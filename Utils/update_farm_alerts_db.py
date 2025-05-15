import os
import sys
import json
import asyncio
import asyncpg
import logging
import psycopg2
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any, Tuple
import ee
import numpy as np

# Set up logging configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
log_dir = os.path.join(project_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

#creating log files for all calculators
ndvi_log_file = os.path.join(log_dir, 'gee_ndvi_health.log')
harvest_log_file = os.path.join(log_dir, 'gee_harvest_readiness.log')
waterlogging_log_file = os.path.join(log_dir, 'gee_waterlogging.log')

# Custom formatter with IST timezone
class ISTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ist = pytz.timezone('Asia/Kolkata')
        record_time = datetime.fromtimestamp(record.created)
        ist_time = record_time.astimezone(ist)
        
        if datefmt:
            return ist_time.strftime(datefmt)
        else:
            return ist_time.strftime('%Y-%m-%d %H:%M:%S')

class BaseEarthEngineCalculator:
    def __init__(self, service_account_json_path: str, logger=None):
        self.service_account_json_path = service_account_json_path
        self.ee_initialized = False
        self.logger = logger or logging.getLogger("default_ee")
    
    def _init_earth_engine(self):
        # Initialize Google Earth Engine if not already initialized
        if not self.ee_initialized:
            initialize_gee(self.service_account_json_path)
            self.ee_initialized = True
            self.logger.info("Google Earth Engine initialized successfully")

    def get_sentinel2_time_series(self, geometry, period_days=45):
        """Get Sentinel-2 image collection for a given time period"""
        self._init_earth_engine()
        
        # Define date range (45 days to capture 3 observations ~15 days apart)
        now = datetime.now(pytz.UTC)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=period_days)).strftime("%Y-%m-%d")
        
        # Convert geometry to GEE format
        ee_geometry = ee.Geometry.Polygon(geometry['coordinates'])
        
        # Get Sentinel-2 collection
        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(start_date, end_date) \
            .filterBounds(ee_geometry) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .sort('system:time_start', False)
        
        return s2_collection, ee_geometry

    async def get_farm_data(self) -> List[Dict[str, Any]]:
        # Fetch farm data with geometries and planting dates
        try:
            conn = await asyncpg.connect(**DB_PARAMS)
            
            query = """
                SELECT 
                    plot_number, 
                    geometry, 
                    date_of_planting, 
                    village_id, 
                    croptype
                FROM 
                    farm_data 
                WHERE 
                    geometry IS NOT NULL AND date_of_planting IS NOT NULL
                ORDER BY 
                    village_id
            """
            
            rows = await conn.fetch(query)
            await conn.close()
            
            if not rows:
                self.logger.warning("No farms with both geometry and planting date found")
                return []
            
            farms = []
            for row in rows:
                farms.append({
                    "plot_number": row['plot_number'],
                    "geometry": row['geometry'],
                    "planting_date": row['date_of_planting'],
                    "village_id": row['village_id'],
                    "croptype": row['croptype']
                })
            
            self.logger.info(f"Retrieved {len(farms)} farms with geometries and planting dates")
            return farms
            
        except Exception as e:
            self.logger.error(f"Error fetching farm data: {str(e)}")
            raise
        
# Configure logging with IST formatter
formatter = ISTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#setting up handler for ndvi log file
ndvi_file_handler = logging.FileHandler(ndvi_log_file)
ndvi_file_handler.setFormatter(formatter)
ndvi_console_handler = logging.StreamHandler()
ndvi_console_handler.setFormatter(formatter)
ndvi_logger = logging.getLogger("gee_ndvi_health")
ndvi_logger.setLevel(logging.INFO)
ndvi_logger.addHandler(ndvi_file_handler)
ndvi_logger.addHandler(ndvi_console_handler)
ndvi_logger.propagate = False

#setting up handler for harvest log file
harvest_file_handler = logging.FileHandler(harvest_log_file)
harvest_file_handler.setFormatter(formatter)
harvest_console_handler = logging.StreamHandler()
harvest_console_handler.setFormatter(formatter)
harvest_logger = logging.getLogger("gee_harvest_readiness")
harvest_logger.setLevel(logging.INFO)
harvest_logger.addHandler(harvest_file_handler)
harvest_logger.addHandler(harvest_console_handler)
harvest_logger.propagate = False

#setting up handler for waterlogging log file
waterlogging_file_handler = logging.FileHandler(waterlogging_log_file)
waterlogging_file_handler.setFormatter(formatter)
waterlogging_console_handler = logging.StreamHandler()
waterlogging_console_handler.setFormatter(formatter)
waterlogging_logger = logging.getLogger("gee_waterlogging")
waterlogging_logger.setLevel(logging.INFO)
waterlogging_logger.addHandler(waterlogging_file_handler)
waterlogging_logger.addHandler(waterlogging_console_handler)
waterlogging_logger.propagate = False

# Database connection parameters for asyncpg (async operations)
DB_PARAMS = {
    'user': 'smurfs',
    'password': 'smurfs123',
    'database': 'smurf',
    'host': 'localhost',
    'port': '5432'
}

# Database connection parameters for psycopg2 (sync operations)
DB_PARAMS_SYNC = {
    'dbname': 'smurf',
    'user': 'smurfs',
    'password': 'smurfs123',
    'host': 'localhost',
    'port': 5432
}

def initialize_gee(service_account_json_path, logger=None):
    """Initialize Google Earth Engine with service account"""
    if logger is None:
        logger = logging.getLogger("default_ee")
    try:
        with open(service_account_json_path) as f:
            service_account_info = json.load(f)
        
        service_account = service_account_info['client_email']
        credentials = ee.ServiceAccountCredentials(service_account, service_account_json_path)
        ee.Initialize(credentials)
        logger.info("Successfully initialized Earth Engine with service account")
    except Exception as e:
        logger.error(f"Error initializing Earth Engine: {str(e)}")
        raise

class SugarcaneHarvestReadinessCalculator(BaseEarthEngineCalculator):
    
    def convert_harvest_readiness_to_int(self, assessment):
        """Convert harvest readiness assessment to integer for database storage
        
        Args:
            assessment (dict): Harvest readiness assessment from check_harvest_readiness()
            
        Returns:
            int: 3 for 'ready', 2 for 'approaching', 1 for 'not ready'
        """
        if assessment['harvest_ready']:
            return 3  # Ready
        elif assessment['confidence'] >= 50:
            return 2  # Approaching readiness
        else:
            return 1  # Not ready
        
    def calculate_lai(self, image):
        """Calculate Leaf Area Index (LAI) using a simplified model based on NDVI"""
        # Calculate NDVI
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # LAI calculation using formula: LAI = -ln(1 - NDVI)/k where k is extinction coefficient
        # Using simplified version: LAI ≈ 4.5 * NDVI - 0.5  for agricultural crops
        lai = ndvi.multiply(4.5).subtract(0.5).rename('LAI')
        
        # Add LAI band to image
        return image.addBands([ndvi, lai])

    def get_swir_reflectance(self, image):
        """Extract SWIR reflectance (B11 band in Sentinel-2)"""
        # B11 is SWIR at 1610nm which is sensitive to plant moisture/sugar content
        return image.select('B11').rename('SWIR')
    
    def check_harvest_readiness(self, plot_geometry, plot_number):
        """Determine harvest readiness for a sugarcane plot"""
        self._init_earth_engine()
        
        # Get image collection for recent period
        s2_collection, ee_geometry = self.get_sentinel2_time_series(plot_geometry)
        
        # Check if we have enough images
        image_count = s2_collection.size().getInfo()
        self.logger.info(f"Found {image_count} suitable images for plot {plot_number} in the analysis period")
        
        if image_count < 3:
            self.logger.warning(f"Not enough images (minimum 3 needed) for plot {plot_number}, cannot determine harvest readiness")
            return {
                'harvest_ready': False,
                'lai_ready': False,
                'swir_ready': False,
                'confidence': 0,
                'reason': "Insufficient data: Need at least 3 cloud-free observations"
            }
        
        # Process image collection to get LAI and SWIR for each date
        collection_with_indicators = s2_collection.map(lambda img: 
            self.calculate_lai(img).addBands(self.get_swir_reflectance(img)))
        
        # Group images by week to detect stability
        two_weeks_ago = (datetime.now(pytz.UTC) - timedelta(days=14)).strftime("%Y-%m-%d")
        four_weeks_ago = (datetime.now(pytz.UTC) - timedelta(days=28)).strftime("%Y-%m-%d")
        
        # Recent images (last 2 weeks)
        recent_images = collection_with_indicators.filterDate(two_weeks_ago, datetime.now(pytz.UTC).strftime("%Y-%m-%d"))
        # Previous 2 weeks
        previous_images = collection_with_indicators.filterDate(four_weeks_ago, two_weeks_ago)
        # All images for SWIR trend analysis
        all_images_list = collection_with_indicators.toList(collection_with_indicators.size())
        
        # Check LAI criterion: LAI > 3.5 and stable for 2 weeks
        recent_lai = self._calculate_mean_indicator_ready(recent_images, ee_geometry, 'LAI')
        previous_lai = self._calculate_mean_indicator_ready(previous_images, ee_geometry, 'LAI')
        
        lai_ready = False
        if recent_lai is not None and previous_lai is not None:
            lai_ready = (recent_lai > 3.5 and abs(recent_lai - previous_lai) < 0.3)
        
        # Check SWIR trend (increasing by 5-10% over 3 observations)
        swir_ready = False
        swir_values = []
        
        # Get latest 3 observations for SWIR analysis
        latest_count = min(3, image_count)
        for i in range(latest_count):
            image = ee.Image(all_images_list.get(i))
            swir_stats = image.select('SWIR').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geometry,
                scale=20,  # SWIR is at 20m resolution
                maxPixels=1e9
            )
            swir_value = swir_stats.get('SWIR').getInfo()
            image_date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            swir_values.append((image_date, swir_value))
        
        # Sort by date (oldest first)
        swir_values.sort(key=lambda x: x[0])
        
        # Calculate SWIR trend if we have enough values
        if len(swir_values) >= 3:
            first_value = swir_values[0][1]
            last_value = swir_values[-1][1]
            
            if first_value > 0:  # Avoid division by zero
                percent_increase = ((last_value - first_value) / first_value) * 100
                swir_ready = (percent_increase >= 5 and percent_increase <= 10)
                self.logger.info(f"SWIR percent increase for plot {plot_number}: {percent_increase:.2f}%")
            else:
                self.logger.warning(f"Invalid SWIR value (0 or negative) for plot {plot_number}")
        
        # Final harvest readiness determination
        harvest_ready = lai_ready and swir_ready
        
        # Calculate confidence level
        confidence = 0
        if lai_ready:
            confidence += 50
        if swir_ready:
            confidence += 50
            
        # Reason for the assessment
        reason = []
        if lai_ready:
            reason.append("LAI > 3.5 and stable")
        else:
            reason.append(f"LAI criteria not met (value: {recent_lai:.2f})")
            
        if swir_ready:
            reason.append("SWIR reflectance indicates optimal sugar accumulation")
        else:
            if len(swir_values) >= 3:
                percent_increase = ((last_value - first_value) / first_value) * 100
                reason.append(f"SWIR increase ({percent_increase:.2f}%) not in optimal range (5-10%)")
            else:
                reason.append("Not enough observations for SWIR analysis")
        
        return {
            'harvest_ready': harvest_ready,
            'lai_ready': lai_ready,
            'swir_ready': swir_ready,
            'confidence': confidence,
            'lai_value': recent_lai,
            'swir_trend': swir_values,
            'reason': "; ".join(reason)
        }
    
    def _calculate_mean_indicator_ready(self, image_collection, geometry, band_name):
        """Calculate mean value of an indicator for a collection"""
        # Check if collection is empty
        if image_collection.size().getInfo() == 0:
            return None
            
        # Calculate mean across the collection
        mean_image = image_collection.select(band_name).mean()
        
        # Get mean value for the geometry
        stats = mean_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10,  # 10m resolution for most bands
            maxPixels=1e9
        )
        
        # Return mean value
        return stats.get(band_name).getInfo()
    
    async def update_harvest_readiness_with_gee(self):
        """Update harvest readiness indicators for all farms"""
        self._init_earth_engine()
        
        # Fetch all farms with geometries and planting dates
        farms = await self.get_farm_data()
        if not farms:
            self.logger.warning("No farms to process, exiting...")
            return
        
        # Group farms by village for batch processing
        villages = {}
        for farm in farms:
            village_id = farm['village_id']
            if village_id not in villages:
                villages[village_id] = []
            villages[village_id].append(farm)
        
        self.logger.info(f"Processing {len(villages)} villages for harvest readiness")
        
        # Connect to database for updates
        conn = psycopg2.connect(**DB_PARAMS_SYNC)
        cur = conn.cursor()
        
        try:
            # Create harvest_readiness column if it doesn't exist
            # cur.execute("""
            #     DO $$
            #     BEGIN
            #         IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
            #                       WHERE table_name='farm_data' AND column_name='harvest_readiness') THEN
            #             ALTER TABLE farm_data ADD COLUMN harvest_readiness INTEGER DEFAULT 1;
            #         END IF;
            #     END $$;
            # """)
            # conn.commit()
            
            # Process each village
            for village_id, village_farms in villages.items():
                self.logger.info(f"\nProcessing village_id: {village_id} for harvest readiness")
                
                # Process each farm in the village
                processed_count = 0
                for farm in village_farms:
                    try:
                        plot_number = farm['plot_number']
                        croptype = farm['croptype']
                        
                        # Skip non-sugarcane crops
                        if croptype.lower() != 'sugarcane':
                            self.logger.info(f"Skipping plot {plot_number} as crop type is {croptype}, not sugarcane")
                            continue
                        
                        # Parse geometry from JSONB
                        geom = json.loads(farm['geometry'])
                        
                        # Check harvest readiness
                        harvest_assessment = self.check_harvest_readiness(geom, plot_number)
                        
                        # Convert to integer value for database
                        readiness_int = self.convert_harvest_readiness_to_int(harvest_assessment)

                        #obtain lai value from harvest assessment
                        lai_value = harvest_assessment.get('lai_value', None)
                        
                        # Update harvest readiness in database
                        cur.execute("""
                            UPDATE farm_data
                            SET harvest_readiness = %s, lai_value = %s
                            WHERE plot_number = %s
                        """, (readiness_int, lai_value, plot_number))
                        
                        # Log result
                        status_map = {3: "Ready", 2: "Approaching", 1: "Not ready"}
                        self.logger.info(f"Updated plot {plot_number} harvest readiness to {status_map[readiness_int]} ({readiness_int})")
                        processed_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing farm plot {farm['plot_number']} for harvest readiness: {e}")
                
                self.logger.info(f"Processed {processed_count} farms in village {village_id} for harvest readiness")
            
            # Commit all changes
            conn.commit()
            self.logger.info("\nHarvest readiness update completed successfully")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error updating harvest readiness: {e}")
        finally:
            # Close connection
            cur.close()
            conn.close()

class GEENDVICalculator(BaseEarthEngineCalculator):
    
    def convert_health_status_to_int(self, health_status):
        """
        Convert health status string to integer for database storage
        
        Args:
            health_status (str): Health status from assess_sugarcane_health ('in danger', 'neutral', or 'healthy')
            
        Returns:
            int: 3 for 'in danger', 2 for 'neutral', 1 for 'healthy'
        """
        status_map = {
            "in danger": 3,
            "neutral": 2,
            "healthy": 1
        }
        return status_map.get(health_status, 2)  # Default to neutral if unknown
    
    def classify_sugarcane_phase(self, days_since_sowing):
        """
        Classify sugarcane growth phase based on days since sowing.
        
        Args:
            days_since_sowing (int): Number of days since sowing date.
            
        Returns:
            tuple: (growth_phase, phase_details) where:
                - growth_phase is one of: "germination", "tillering", "grand_growth", "maturity"
                - phase_details contains additional information about the phase
        """
        # Define phase boundaries
        if days_since_sowing < 35:
            return "germination", {
                "name": "Germination Phase",
                "description": "Initial growth and establishment",
                "expected_duration": "0-35 days",
                "critical_care": "Adequate moisture and weed control"
            }
        elif days_since_sowing < 120:
            return "tillering", {
                "name": "Tillering Phase",
                "description": "Development of tillers and early stem formation",
                "expected_duration": "35-120 days",
                "critical_care": "Fertilizer application and irrigation"
            }
        elif days_since_sowing < 270:
            return "grand_growth", {
                "name": "Grand Growth Phase",
                "description": "Rapid stem elongation and biomass accumulation",
                "expected_duration": "120-270 days",
                "critical_care": "Regular irrigation and pest management"
            }
        else:
            return "maturity", {
                "name": "Maturity Phase",
                "description": "Sugar accumulation and ripening",
                "expected_duration": "270+ days",
                "critical_care": "Water stress for ripening, harvest planning"
            }
        
    def get_ndvi_thresholds(self, growth_phase):
        """
        Get NDVI thresholds for sugarcane health assessment based on growth phase.
        
        Args:
            growth_phase (str): The current growth phase of sugarcane
            
        Returns:
            dict: NDVI thresholds for the growth phase
        """
        # NDVI thresholds for each growth phase
        if growth_phase == "germination":
            # During germination, NDVI is naturally low but should start increasing
            return {
                "danger_threshold": 0.15,      # Below this is concerning in germination phase
                "neutral_threshold": 0.25,     # Between danger and this value is neutral
                "healthy_threshold": 0.35      # Above this is considered healthy for this early stage
            }
        elif growth_phase == "tillering":
            # Tillering phase should show significant increase in NDVI
            return {
                "danger_threshold": 0.35,      # Below this is concerning in tillering phase
                "neutral_threshold": 0.45,     # Between danger and this value is neutral
                "healthy_threshold": 0.55      # Above this is considered healthy for tillering
            }
        elif growth_phase == "grand_growth":
            # During grand growth, NDVI should be at or near maximum values
            return {
                "danger_threshold": 0.55,      # Below this is concerning in grand growth phase
                "neutral_threshold": 0.65,     # Between danger and this value is neutral
                "healthy_threshold": 0.75      # Above this is considered healthy for grand growth
            }
        else:  # maturity
            # During ripening/maturity, NDVI naturally decreases as the crop matures
            return {
                "danger_threshold": 0.40,      # Below this is concerning in ripening phase
                "neutral_threshold": 0.50,     # Between danger and this value is neutral
                "healthy_threshold": 0.60      # Above this is considered healthy for ripening
            }


    def calculate_days_since_sowing(self, sowing_date_str, current_date_str):
        """
        Calculate days since sowing and other time-related metrics.
        
        Args:
            sowing_date_str (str): Sowing date in 'YYYY-MM-DD HH:MM:SS' format
            current_date_str (str): Current date in 'YYYY-MM-DD HH:MM:SS' format
            
        Returns:
            tuple: (days_since_sowing, days_to_harvest, percent_cycle_complete)
        """
        # Parse dates
        sowing_date = datetime.strptime(str(sowing_date_str).split('+')[0].strip(), '%Y-%m-%d %H:%M:%S')
        current_date = datetime.strptime(str(current_date_str).split('+')[0].strip(), '%Y-%m-%d %H:%M:%S')
        
        # Calculate days since sowing
        days_since_sowing = (current_date - sowing_date).days
        
        # Estimate total cycle length (assume 365 days for full cycle)
        total_cycle_days = 365
        
        # Calculate days remaining until estimated harvest
        days_to_harvest = max(0, total_cycle_days - days_since_sowing)
        
        # Calculate percentage of growth cycle completed
        percent_cycle_complete = min(100, (days_since_sowing / total_cycle_days) * 100)
        
        return days_since_sowing, days_to_harvest, percent_cycle_complete

    def assess_sugarcane_health(self, ndvi_value, growth_phase):
        """
        Assess the health of sugarcane based on NDVI value and growth phase.
        
        Args:
            ndvi_value (float): NDVI value (typically between -1 and 1)
            growth_phase (str): Current growth phase of the sugarcane
            
        Returns:
            dict: Assessment results including health status and recommendations
        """
        # Define NDVI thresholds for different growth phases
        thresholds = self.get_ndvi_thresholds(growth_phase)
        
        # Determine health status
        if ndvi_value < thresholds["danger_threshold"]:
            health_status = "in danger"
            recommendations = [
                "Check for water stress or waterlogging",
                "Inspect for pest or disease outbreaks",
                "Consider additional nutrient application",
                "Evaluate soil conditions and drainage"
            ]
        elif ndvi_value >= thresholds["healthy_threshold"]:
            health_status = "healthy"
            recommendations = [
                "Continue current management practices",
                "Monitor for any changes in crop appearance",
                "Maintain irrigation schedule appropriate for the phase"
            ]
        else:
            health_status = "neutral"
            recommendations = [
                "Monitor crop more frequently",
                "Check irrigation efficiency",
                "Consider light fertilizer application",
                "Inspect for early signs of stress"
            ]
        
        return {
            "health_status": health_status,
            "ndvi_value": ndvi_value,
            "growth_phase": growth_phase,
            "recommendations": recommendations
        }
     
    
    def calculate_ndvi(self, image):
        """Add NDVI band to image"""
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)  
    
    def get_latest_sentinel2_image(self, geometry, days_back=30):
        """Get the latest Sentinel-2 image for a given geometry"""
        self._init_earth_engine()
        
        # Define date range
        now = datetime.now(pytz.UTC)
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # Convert geometry to GEE format
        ee_geometry = ee.Geometry.Polygon(geometry['coordinates'])
        
        # Get Sentinel-2 collection
        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(start_date, end_date) \
            .filterBounds(ee_geometry) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .sort('system:time_start', False)
        
        # Check if we have any images
        image_count = s2_collection.size().getInfo()
        if image_count == 0:
            self.logger.warning(f"No Sentinel-2 images found for the period {start_date} to {end_date}")
            return None
        
        # Get the most recent image
        latest_image = ee.Image(s2_collection.first())
        
        # Add NDVI band
        latest_image_with_ndvi = self.calculate_ndvi(latest_image)
        
        return latest_image_with_ndvi
    
    def calculate_ndvi_for_geometry(self, image, geometry):
        """Calculate NDVI statistics for a specific geometry"""
        self._init_earth_engine()
        
        if image is None:
            self.logger.warning("No image provided for NDVI calculation")
            return None
        
        # Convert geometry to GEE format
        ee_geometry = ee.Geometry.Polygon(geometry['coordinates'])
        
        # Calculate mean NDVI for the geometry
        ndvi_stats = image.select('NDVI').reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ee_geometry,
            scale=10,  # 10m resolution for Sentinel-2
            maxPixels=1e9
        )
        
        # Get the mean NDVI value
        ndvi_value = ndvi_stats.get('NDVI').getInfo()
        
        # Get image date
        image_date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        
        return {
            'ndvi': ndvi_value,
            'date': image_date
        }
     
    async def update_farm_health_with_gee(self):
        """Update farm health using NDVI calculated directly from Google Earth Engine"""
        self._init_earth_engine()
        
        # Fetch all farms with geometries and planting dates
        farms = await self.get_farm_data()
        if not farms:
            self.logger.warning("No farms to process, exiting...")
            return
        
        # Group farms by village for batch processing
        villages = {}
        for farm in farms:
            village_id = farm['village_id']
            if village_id not in villages:
                villages[village_id] = []
            villages[village_id].append(farm)
        
        self.logger.info(f"Processing {len(villages)} villages")
        
        # Connect to database for updates (using psycopg2 for simplicity in the loop)
        conn = psycopg2.connect(**DB_PARAMS_SYNC)
        cur = conn.cursor()
        
        try:
            # Process each village
            for village_id, village_farms in villages.items():
                self.logger.info(f"\nProcessing village_id: {village_id}")
                
                # Get a common image for the entire village to minimize API calls
                # Use the first farm's geometry as representative
                try:
                    first_farm = village_farms[0]
                    first_geom = json.loads(first_farm['geometry'])
                    
                    # Get the latest Sentinel-2 image for this village area
                    village_image = self.get_latest_sentinel2_image(first_geom)
                    
                    if village_image is None:
                        self.logger.warning(f"No recent Sentinel-2 image found for village {village_id}, skipping...")
                        continue
                    
                    image_date = ee.Date(village_image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                    self.logger.info(f"Using Sentinel-2 image from {image_date} for village {village_id}")
                
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.error(f"Error with geometry or image retrieval for village {village_id}: {e}")
                    continue
                
                # Process each farm in the village
                processed_count = 0
                for farm in village_farms:
                    try:
                        plot_number = farm['plot_number']
                        planting_date = farm['planting_date']
                        croptype = farm['croptype']
                        
                        # Parse geometry from JSONB
                        geom = json.loads(farm['geometry'])
                        
                        # Calculate NDVI for this farm geometry using the common village image
                        ndvi_result = self.calculate_ndvi_for_geometry(village_image, geom)
                        
                        if ndvi_result is None or ndvi_result['ndvi'] is None:
                            self.logger.warning(f"Could not calculate NDVI for plot {plot_number}, skipping...")
                            continue
                        
                        ndvi_value = ndvi_result['ndvi']
                        
                        # Current date for health assessment
                        current_date = datetime.now()
                        
                        # Calculate days since planting
                        planting_date_str = f"{planting_date} 00:00:00"
                        days_since_sowing, _, _ = self.calculate_days_since_sowing(
                            planting_date_str, 
                            current_date.strftime("%Y-%m-%d %H:%M:%S")
                        )
                        
                        # Get growth phase
                        growth_phase, _ = self.classify_sugarcane_phase(days_since_sowing)
                        
                        # Assess health based on NDVI and growth phase
                        health_assessment = self.assess_sugarcane_health(ndvi_value, growth_phase)
                        health_status = health_assessment["health_status"]
                        
                        # Convert to integer value for database
                        health_int = self.convert_health_status_to_int(health_status)
                        
                        # Update health in database
                        cur.execute("""
                            UPDATE farm_data
                            SET health = %s, ndvi_value = %s
                            WHERE plot_number = %s
                        """, (health_int, ndvi_value, plot_number))
                        
                        self.logger.info(f"Updated plot {plot_number} health to {health_status} ({health_int}) and NDVI to {ndvi_value:.4f}")
                        processed_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing farm plot {farm['plot_number']}: {e}")
                
                self.logger.info(f"Processed {processed_count} farms in village {village_id}")
            
            # Commit all changes
            conn.commit()
            self.logger.info("\nHealth and NDVI value columns update completed successfully")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error updating health or NDVI: {e}")
        finally:
            # Close connection
            cur.close()
            conn.close()

class WaterLoggingCalculator(BaseEarthEngineCalculator):

    def calculate_ndwi(self, image):
        """Add NDWI band to image using Sentinel-2 bands
        NDWI = (Green - NIR) / (Green + NIR)
        Using B3 (Green) and B8 (NIR) for Sentinel-2"""
        ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
        return image.addBands(ndwi)

    def convert_waterlogging_status_to_int(self, waterlogging_status):
        """
        Convert waterlogging status to integer for database storage
        
        Args:
            waterlogging_status (str): Waterlogging status ('waterlogged', 'at risk', or 'normal')
            
        Returns:
            int: 3 for 'waterlogged', 2 for 'at risk', 1 for 'normal'
        """
        status_map = {
            "waterlogged": 3,
            "at risk": 2,
            "normal": 1
        }
        return status_map.get(waterlogging_status, 1)  # Default to normal if unknown

    def assess_waterlogging_condition(self, ndwi_values):
        """
        Assess waterlogging condition based on NDWI values from consecutive satellite passes
        
        Args:
            ndwi_values (list): List of (date, ndwi_value) tuples from recent satellite passes
            
        Returns:
            dict: Assessment results including waterlogging status and recommendations
        """
        # Check if we have enough measurements
        if len(ndwi_values) < 2:
            return {
                "waterlogging_status": "normal",
                "confidence": "low",
                "recommendations": [
                    "Insufficient data for accurate waterlogging assessment",
                    "Monitor field conditions visually"
                ]
            }
        
        # Sort by date (newest first)
        sorted_values = sorted(ndwi_values, key=lambda x: x[0], reverse=True)
        
        # Get the two most recent measurements
        recent_ndwi = sorted_values[0][1]
        previous_ndwi = sorted_values[1][1]
        
        # Check for waterlogging conditions
        if recent_ndwi > 0.3 and previous_ndwi > 0.3:
            waterlogging_status = "waterlogged"
            recommendations = [
                "Urgent: Implement drainage measures",
                "Check drainage channels for blockages",
                "Consider pumping out excess water if possible",
                "Monitor for signs of crop stress due to waterlogging"
            ]
            confidence = "high"
        elif recent_ndwi > 0.3 or previous_ndwi > 0.3:
            waterlogging_status = "at risk"
            recommendations = [
                "Monitor field conditions closely",
                "Ensure drainage channels are clear",
                "Prepare for possible intervention if rainfall continues",
                "Check low-lying areas of the field specifically"
            ]
            confidence = "medium"
        elif recent_ndwi > 0.2:
            waterlogging_status = "at risk"
            recommendations = [
                "Field conditions approaching waterlogging threshold",
                "Monitor weather forecast for upcoming rain events",
                "Inspect field drainage systems"
            ]
            confidence = "medium"
        else:
            waterlogging_status = "normal"
            recommendations = [
                "Maintain normal monitoring schedule",
                "No waterlogging issues detected"
            ]
            confidence = "high"
        
        return {
            "waterlogging_status": waterlogging_status,
            "ndwi_values": sorted_values[:2],  # Include the two most recent values
            "confidence": confidence,
            "recommendations": recommendations
        }
    
    async def update_waterlogging_with_gee(self):
        """Update waterlogging indicators for all farms using NDWI from Google Earth Engine"""
        self._init_earth_engine()
        
        # Fetch all farms with geometries and planting dates
        farms = await self.get_farm_data()
        if not farms:
            self.logger.warning("No farms to process for waterlogging assessment, exiting...")
            return
        
        # Group farms by village for batch processing
        villages = {}
        for farm in farms:
            village_id = farm['village_id']
            if village_id not in villages:
                villages[village_id] = []
            villages[village_id].append(farm)
        
        self.logger.info(f"Processing {len(villages)} villages for waterlogging assessment")
        
        # Connect to database for updates
        conn = psycopg2.connect(**DB_PARAMS_SYNC)
        cur = conn.cursor()
        
        try:
            # Create waterlogging column if it doesn't exist
            # cur.execute("""
            #     DO $$
            #     BEGIN
            #         IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
            #                     WHERE table_name='farm_data' AND column_name='waterlogging') THEN
            #             ALTER TABLE farm_data ADD COLUMN waterlogging INTEGER DEFAULT 1;
            #         END IF;
            #         IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
            #                     WHERE table_name='farm_data' AND column_name='ndwi_value') THEN
            #             ALTER TABLE farm_data ADD COLUMN ndwi_value FLOAT;
            #         END IF;
            #     END $$;
            # """)
            # conn.commit()
            
            # Process each village
            for village_id, village_farms in villages.items():
                self.logger.info(f"\nProcessing village_id: {village_id} for waterlogging assessment")
                
                # Process each farm in the village
                processed_count = 0
                for farm in village_farms:
                    try:
                        plot_number = farm['plot_number']
                        
                        # Parse geometry from JSONB
                        geom = json.loads(farm['geometry'])
                        
                        # Get Sentinel-2 image collection for the past 30 days (to capture 2-3 passes)
                        s2_collection, ee_geometry = self.get_sentinel2_time_series(geom, period_days=30)
                        
                        # Check if we have images
                        image_count = s2_collection.size().getInfo()
                        
                        if image_count < 1:
                            self.logger.warning(f"No recent images found for plot {plot_number}, skipping waterlogging assessment")
                            continue
                        
                        # Add NDWI band to all images
                        s2_collection_with_ndwi = s2_collection.map(self.calculate_ndwi)
                        
                        # Get images as a list
                        image_list = s2_collection_with_ndwi.toList(s2_collection_with_ndwi.size())
                        
                        # Extract NDWI for each image
                        ndwi_values = []
                        for i in range(image_count):
                            image = ee.Image(image_list.get(i))
                            ndwi_stats = image.select('NDWI').reduceRegion(
                                reducer=ee.Reducer.mean(),
                                geometry=ee_geometry,
                                scale=10,  # 10m resolution
                                maxPixels=1e9
                            )
                            ndwi_value = ndwi_stats.get('NDWI').getInfo()
                            image_date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                            ndwi_values.append((image_date, ndwi_value))
                        
                        # Get the most recent NDWI value for the database
                        latest_ndwi = sorted(ndwi_values, key=lambda x: x[0], reverse=True)[0][1]
                        
                        # Assess waterlogging condition
                        waterlogging_assessment = self.assess_waterlogging_condition(ndwi_values)
                        waterlogging_status = waterlogging_assessment["waterlogging_status"]
                        
                        # Convert to integer value for database
                        waterlogging_int = self.convert_waterlogging_status_to_int(waterlogging_status)
                        
                        # Update waterlogging status in database
                        cur.execute("""
                            UPDATE farm_data
                            SET waterlogging = %s, ndwi_value = %s
                            WHERE plot_number = %s
                        """, (waterlogging_int, latest_ndwi, plot_number))
                        
                        self.logger.info(f"Updated plot {plot_number} waterlogging status to {waterlogging_status} ({waterlogging_int}) and NDWI to {latest_ndwi:.4f}")
                        processed_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing farm plot {farm['plot_number']} for waterlogging assessment: {e}")
                
                self.logger.info(f"Processed {processed_count} farms in village {village_id} for waterlogging assessment")
            
            # Commit all changes
            conn.commit()
            self.logger.info("\nWaterlogging assessment update completed successfully")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error updating waterlogging assessment: {e}")
        finally:
            # Close connection
            cur.close()
            conn.close()    

async def main():
    try:
        # Set paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        
        # Use absolute paths everywhere
        service_account_json_path = os.path.join(project_dir, 'api_key/ee-chaitanyamodi-6874ede8f64c.json')
        
        # Log path information for debugging in each logger
        ndvi_logger.info(f"Script directory: {script_dir}")
        ndvi_logger.info(f"Project directory: {project_dir}")
        ndvi_logger.info(f"Service account path: {service_account_json_path}")
        
        harvest_logger.info(f"Script directory: {script_dir}")
        harvest_logger.info(f"Project directory: {project_dir}")
        harvest_logger.info(f"Service account path: {service_account_json_path}")
        
        waterlogging_logger.info(f"Script directory: {script_dir}")
        waterlogging_logger.info(f"Project directory: {project_dir}")
        waterlogging_logger.info(f"Service account path: {service_account_json_path}")
        
        # Create NDVI calculator instance
        ndvi_calculator = GEENDVICalculator(service_account_json_path, logger=ndvi_logger)
        await ndvi_calculator.update_farm_health_with_gee()
        ndvi_logger.info("Farm health update process completed successfully")

        # Create harvest readiness calculator instance
        harvest_calculator = SugarcaneHarvestReadinessCalculator(service_account_json_path, logger=harvest_logger)
        await harvest_calculator.update_harvest_readiness_with_gee()
        harvest_logger.info("Harvest readiness update process completed successfully")

        # Create waterlogging calculator instance
        waterlogging_calculator = WaterLoggingCalculator(service_account_json_path, logger=waterlogging_logger)
        await waterlogging_calculator.update_waterlogging_with_gee()
        waterlogging_logger.info("Waterlogging update process completed successfully")

    except Exception as e:
        ndvi_logger.error(f"Error in main function: {str(e)}")
        harvest_logger.error(f"Error in main function: {str(e)}")
        waterlogging_logger.error(f"Error in main function: {str(e)}")
        # Print to stderr as well in case logging failed
        print(f"Error in main function: {str(e)}", file=sys.stderr)
        
if __name__ == "__main__":
    asyncio.run(main())