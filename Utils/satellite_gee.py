import os
import sys
import json
import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any, Tuple
import ee
import geemap

# Get the satellite type from command line args
satellite_type = None
if len(sys.argv) > 1:
    satellite_type = sys.argv[1].upper()

# Define log file paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
log_dir = os.path.join(project_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

# Set up logging configuration based on satellite type
if satellite_type in ['S1', 'S2', 'L9']:
    log_file_map = {
        'S1': os.path.join(log_dir, 'sentinel1_cron.log'),
        'S2': os.path.join(log_dir, 'sentinel2_cron.log'),
        'L9': os.path.join(log_dir, 'landsat_cron.log')
    }
    log_file = log_file_map[satellite_type]
else:
    # Default log file if no satellite type or invalid type
    log_file = os.path.join(project_dir, 'satellite_scheduler.log')

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

# Configure logging with IST formatter
formatter = ISTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set up handlers
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Configure the logger
logger = logging.getLogger("satellite_scheduler")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Remove default handlers if any exist
logger.propagate = False

# Database connection parameters
DB_PARAMS = {
    'user': 'smurfs',
    'password': 'smurfs123',
    'database': 'smurf',
    'host': 'localhost',
    'port': '5432'
}

def initialize_gee(service_account_json_path):
# Initialize Google Earth Engine 
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

def download_image(image, roi, output_dir, scale, bands, satellite_type, lat, lon, village_id):
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the image acquisition date
    image_date = ee.Date(image.get('system:time_start')).format('yyyyMMdd').getInfo()
    
    # Generate IST timestamp for the download time
    ist = pytz.timezone('Asia/Kolkata')
    utc_now = datetime.now(pytz.UTC)
    ist_time = utc_now.astimezone(ist)  # Convert from UTC to IST
    download_timestamp = ist_time.strftime('%Y%m%d_%H%M%S')
    
    # Create the new filename with village_id, coordinates, image date, and download timestamp
    coords_str = f"{abs(lat):.5f}{'N' if lat >= 0 else 'S'}_{abs(lon):.5f}{'E' if lon >= 0 else 'W'}"
    filename = f"{satellite_type}_v{village_id}_{coords_str}_{image_date}_{download_timestamp}.tif"
    output_path = os.path.join(output_dir, filename)
    
    # Select the specified bands and download
    image = image.select(bands)
    region = roi.bounds().getInfo()['coordinates'][0]  # Get the region bounds
    
    # Get the download URL
    url = image.getDownloadURL({
        'scale': scale,
        'region': region,
        'format': 'GEO_TIFF'
    })
    
    # Download img
    geemap.download_file(url, output_path)
    logger.info(f"Image downloaded to: {output_path}")
    
    return output_path

# Class to manage satellite data collection
class SatelliteDataCollector:
    def __init__(self, service_account_json_path: str, base_dir: str):
        self.service_account_json_path = service_account_json_path
        self.base_dir = base_dir
        self.ee_initialized = False
        
        # Create the base directory if it doesn't exist
        os.makedirs(base_dir, exist_ok=True)
        
        # Create tracking database if it doesn't exist
        self.tracking_db_path = os.path.join(base_dir, 'download_tracking.json')
        if not os.path.exists(self.tracking_db_path):
            with open(self.tracking_db_path, 'w') as f:
                json.dump({}, f)

    async def get_village_centroids(self) -> List[Dict[str, Any]]:
        # Fetch all village centroids from the database
        try:
            conn = await asyncpg.connect(**DB_PARAMS)
            
            query = """
                SELECT 
                    village_id,
                    village_name,
                    ST_X(centroid) as lon,
                    ST_Y(centroid) as lat
                FROM 
                    village_data
                WHERE 
                    centroid IS NOT NULL
            """
            
            rows = await conn.fetch(query)
            await conn.close()
            
            if not rows:
                logger.warning("No village centroids found in the database")
                return []
            
            villages = []
            for row in rows:
                villages.append({
                    "village_id": row['village_id'],
                    "village_name": row['village_name'],
                    "lon": row['lon'],
                    "lat": row['lat']
                })
            
            logger.info(f"Retrieved {len(villages)} village centroids from database")
            return villages
            
        except Exception as e:
            logger.error(f"Error fetching village centroids: {str(e)}")
            raise
    
    def _init_earth_engine(self):
        # Initialize Google Earth Engine
        if not self.ee_initialized:
            initialize_gee(self.service_account_json_path)
            self.ee_initialized = True
            logger.info("Google Earth Engine initialized successfully")
    
    def _get_tracking_data(self) -> Dict:
        try:
            with open(self.tracking_db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tracking data: {str(e)}")
            return {}
    
    def _save_tracking_data(self, tracking_data: Dict):
        try:
            with open(self.tracking_db_path, 'w') as f:
                json.dump(tracking_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tracking data: {str(e)}")
    
    def _update_last_image_date(self, village_id: int, satellite_type: str, image_date: str):
        # Update the date of the latest image acquired for a specific village and satellite
        tracking_data = self._get_tracking_data()
        
        village_key = str(village_id)
        if village_key not in tracking_data:
            tracking_data[village_key] = {}
        
        # Update the last image date for this satellite type
        tracking_data[village_key][satellite_type] = image_date
        
        self._save_tracking_data(tracking_data)
        logger.info(f"Updated last image date for village {village_id}, satellite {satellite_type}: {image_date}")
    
    def _get_last_image_date(self, village_id: int, satellite_type: str) -> str:
        # Get the last image date for a specific village and satellite
        tracking_data = self._get_tracking_data()
        
        village_key = str(village_id)
        if village_key not in tracking_data or satellite_type not in tracking_data[village_key]:
            return None
        
        return tracking_data[village_key][satellite_type]
    
    def _should_download_new_image(self, village_id: int, satellite_type: str, image_date: str) -> bool:
        # Check if this image is newer than what we already have
        last_image_date = self._get_last_image_date(village_id, satellite_type)
        
        # If we've never downloaded an image for this village/satellite, download it
        if last_image_date is None:
            return True
        
        # Compare image dates (format is YYYYMMDD)
        return image_date > last_image_date
    
    async def collect_satellite_data(self, satellite_type: str = None):
        # Collect satellite data for all villages
        self._init_earth_engine()
        
        # Get all village centroids
        villages = await self.get_village_centroids()
        
        if not villages:
            logger.warning("No villages found, skipping satellite data collection")
            return
        
        # Define satellite types with their revisit periods
        satellite_configs = {
            "S2": {"revisit_days": 5, "name": "Sentinel-2", "dir": "sentinel2"},
            "S1": {"revisit_days": 6, "name": "Sentinel-1", "dir": "sentinel1"},
            "L9": {"revisit_days": 16, "name": "Landsat 9", "dir": "landsat"}
        }
        
        # Filter to only the requested satellite type if specified
        if satellite_type:
            if satellite_type not in satellite_configs:
                logger.error(f"Invalid satellite type: {satellite_type}")
                return
            satellite_configs = {satellite_type: satellite_configs[satellite_type]}
        
        # Get current date in UTC
        now = datetime.now(pytz.UTC)
        
        # Create base directories for each satellite type
        for sat_type, config in satellite_configs.items():
            sat_dir = os.path.join(self.base_dir, config["dir"])
            os.makedirs(sat_dir, exist_ok=True)
        
        # Process each village
        for village in villages:
            village_id = village["village_id"]
            village_name = village["village_name"]
            lon = village["lon"]
            lat = village["lat"]
            
            logger.info(f"Processing village: {village_name} (ID: {village_id}, Coords: {lat}, {lon})")
            
            # Create a point geometry for this village's centroid
            center_point = ee.Geometry.Point([lon, lat])
            roi = center_point.buffer(6750)  # 6.75km buffer (radius)
            
            # Process each satellite type
            for sat_type, config in satellite_configs.items():
                revisit_days = config["revisit_days"]
                sat_name = config["name"]
                sat_dir = config["dir"]
                
                logger.info(f"Checking for new {sat_name} images for village {village_name} (ID: {village_id})")
                
                # Calculate date range - look back much further than just the revisit period
                # to ensure we catch any images that might have been delayed in processing
                end_date = now.strftime("%Y-%m-%d")
                # Look back 30 days to catch any images we might have missed
                start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
                
                # Get last image date to filter for newer images after collection
                last_image_date = self._get_last_image_date(village_id, sat_type)
                if last_image_date:
                    logger.info(f"Last {sat_name} image for village {village_id} was from {last_image_date}")
                
                try:
                    # Collect satellite data based on type
                    if sat_type == "S2":
                        self._collect_sentinel2(roi, start_date, end_date, self.base_dir, lat, lon, village_id)
                    elif sat_type == "S1":
                        self._collect_sentinel1(roi, start_date, end_date, self.base_dir, lat, lon, village_id)
                    elif sat_type == "L9":
                        self._collect_landsat9(roi, start_date, end_date, self.base_dir, lat, lon, village_id)
                    
                except Exception as e:
                    logger.error(f"Error collecting {sat_name} data for village {village_name}: {str(e)}")

    def _collect_sentinel2(self, roi, start_date, end_date, base_dir, lat, lon, village_id):
        """Collect Sentinel-2 data"""
        # Create specific directory for Sentinel-2 with village subdirectory
        sentinel2_base_dir = os.path.join(base_dir, 'sentinel2')
        village_dir = os.path.join(sentinel2_base_dir, f'v{village_id}')
        os.makedirs(village_dir, exist_ok=True)
        
        # Get Sentinel-2 Surface Reflectance (Level-2A) image collection
        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                        .filterDate(start_date, end_date) \
                        .filterBounds(roi) \
                        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        s2_count = s2_collection.size().getInfo()
        logger.info(f"Found {s2_count} Sentinel-2 images for village {village_id}")
        
        if s2_count > 0:
            # Sort by acquisition date (most recent first) and then by cloud cover
            s2_images = s2_collection.sort('system:time_start', False).sort('CLOUDY_PIXEL_PERCENTAGE').toList(s2_count)
            
            # Check each image from newest to oldest
            for i in range(s2_count):
                s2_image = ee.Image(s2_images.get(i))
                
                # Get the image acquisition date
                image_date = ee.Date(s2_image.get('system:time_start')).format('yyyyMMdd').getInfo()
                
                # Check if we already have this image or a newer one
                if self._should_download_new_image(village_id, "S2", image_date):
                    # Define bands to download
                    sentinel2_bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B11', 'B12']
                    
                    # Download the image
                    download_image(
                        s2_image,
                        roi,
                        village_dir,
                        scale=10,  # 10m resolution for key bands
                        bands=sentinel2_bands,
                        satellite_type="S2",
                        lat=lat,
                        lon=lon,
                        village_id=village_id
                    )
                    
                    # Also download SCL (Scene Classification Layer) for cloud and shadow masking
                    download_image(
                        s2_image,
                        roi,
                        village_dir,
                        scale=20,  # SCL is at 20m resolution
                        bands=['SCL'],
                        satellite_type="S2_SCL",
                        lat=lat,
                        lon=lon,
                        village_id=village_id
                    )
                    
                    # Update tracking information with the image date
                    self._update_last_image_date(village_id, "S2", image_date)
                    
                    logger.info(f"Downloaded Sentinel-2 image from {image_date} for village {village_id}")
                    return True
                else:
                    logger.info(f"Skipping Sentinel-2 image from {image_date} - not newer than our last download")
            
            logger.info(f"No new Sentinel-2 images found for village {village_id}")
            return False
        else:
            logger.warning(f"No Sentinel-2 images found for village {village_id} in date range")
            return False

    def _collect_sentinel1(self, roi, start_date, end_date, base_dir, lat, lon, village_id):
        """Collect Sentinel-1 data"""
        # Create specific directory for Sentinel-1 with village subdirectory
        sentinel1_base_dir = os.path.join(base_dir, 'sentinel1')
        village_dir = os.path.join(sentinel1_base_dir, f'v{village_id}')
        os.makedirs(village_dir, exist_ok=True)
        
        # Get Sentinel-1 SAR GRD image collection
        s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
                        .filterDate(start_date, end_date) \
                        .filterBounds(roi) \
                        .filter(ee.Filter.eq('instrumentMode', 'IW')) \
                        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
                        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
        
        s1_count = s1_collection.size().getInfo()
        logger.info(f"Found {s1_count} Sentinel-1 images for village {village_id}")
        
        if s1_count > 0:
            # Sort by acquisition date (most recent first)
            s1_images = s1_collection.sort('system:time_start', False).toList(s1_count)
            
            # Check each image from newest to oldest
            for i in range(s1_count):
                s1_image = ee.Image(s1_images.get(i))
                
                # Get the image acquisition date
                image_date = ee.Date(s1_image.get('system:time_start')).format('yyyyMMdd').getInfo()
                
                # Check if we already have this image or a newer one
                if self._should_download_new_image(village_id, "S1", image_date):
                    # Define bands to download
                    sentinel1_bands = ['VV', 'VH', 'angle']
                    
                    # Download the image
                    download_image(
                        s1_image,
                        roi,
                        village_dir,
                        scale=10,
                        bands=sentinel1_bands,
                        satellite_type="S1",
                        lat=lat,
                        lon=lon,
                        village_id=village_id
                    )
                    
                    # Update tracking information with the image date
                    self._update_last_image_date(village_id, "S1", image_date)
                    
                    logger.info(f"Downloaded Sentinel-1 image from {image_date} for village {village_id}")
                    return True
                else:
                    logger.info(f"Skipping Sentinel-1 image from {image_date} - not newer than our last download")
            
            logger.info(f"No new Sentinel-1 images found for village {village_id}")
            return False
        else:
            logger.warning(f"No Sentinel-1 images found for village {village_id} in date range")
            return False

    def _collect_landsat9(self, roi, start_date, end_date, base_dir, lat, lon, village_id):
        """Collect Landsat 9 data"""
        # Create specific directory for Landsat with village subdirectory
        landsat_base_dir = os.path.join(base_dir, 'landsat')
        village_dir = os.path.join(landsat_base_dir, f'v{village_id}')
        os.makedirs(village_dir, exist_ok=True)
        
        # Get Landsat 9 Surface Reflectance with Surface Temperature collection
        landsat_collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') \
                            .filterDate(start_date, end_date) \
                            .filterBounds(roi) \
                            .filter(ee.Filter.lt('CLOUD_COVER', 20))
        
        landsat_count = landsat_collection.size().getInfo()
        logger.info(f"Found {landsat_count} Landsat images for village {village_id}")
        
        if landsat_count > 0:
            # Sort by acquisition date (most recent first) and then by cloud cover
            landsat_images = landsat_collection.sort('system:time_start', False).sort('CLOUD_COVER').toList(landsat_count)
            
            # Check each image from newest to oldest
            for i in range(landsat_count):
                landsat_image = ee.Image(landsat_images.get(i))
                
                # Get the image acquisition date
                image_date = ee.Date(landsat_image.get('system:time_start')).format('yyyyMMdd').getInfo()
                
                # Check if we already have this image or a newer one
                if self._should_download_new_image(village_id, "L9", image_date):
                    # Define bands to download
                    optical_bands = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'QA_PIXEL']
                    
                    # Download optical bands
                    download_image(
                        landsat_image,
                        roi,
                        village_dir,
                        scale=30,  # 30m resolution (native for optical bands)
                        bands=optical_bands,
                        satellite_type="L9",
                        lat=lat,
                        lon=lon,
                        village_id=village_id
                    )
                    
                    # Download thermal band
                    thermal_bands = ['ST_B10']
                    download_image(
                        landsat_image,
                        roi,
                        village_dir,
                        scale=100,  # 100m resolution (native for thermal band)
                        bands=thermal_bands,
                        satellite_type="L9_thermal",
                        lat=lat,
                        lon=lon,
                        village_id=village_id
                    )
                    
                    # Update tracking information with the image date
                    self._update_last_image_date(village_id, "L9", image_date)
                    
                    logger.info(f"Downloaded Landsat image from {image_date} for village {village_id}")
                    return True
                else:
                    logger.info(f"Skipping Landsat image from {image_date} - not newer than our last download")
            
            logger.info(f"No new Landsat images found for village {village_id}")
            return False
        else:
            logger.warning(f"No Landsat images found for village {village_id} in date range")
            return False

async def main():
    try:
        # Set paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        
        # Use absolute paths everywhere
        service_account_json_path = os.path.join(project_dir, 'api_key/ee-chaitanyamodi-6874ede8f64c.json')
        base_dir = os.path.join(project_dir, 'Images/')
        
        # Log path information for debugging
        logger.info(f"Script directory: {script_dir}")
        logger.info(f"Project directory: {project_dir}")
        logger.info(f"Service account path: {service_account_json_path}")
        logger.info(f"Base directory: {base_dir}")
        
        # Create collector instance
        collector = SatelliteDataCollector(service_account_json_path, base_dir)
        
        # Get satellite type from command line arguments if provided
        satellite_type = None
        if len(sys.argv) > 1:
            satellite_type = sys.argv[1].upper()
            if satellite_type not in ['S1', 'S2', 'L9']:
                logger.error(f"Invalid satellite type: {satellite_type}. Use S1, S2, or L9.")
                return
        
        # Collect satellite data
        await collector.collect_satellite_data(satellite_type)
        
        logger.info("Satellite data collection completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        # Print to stderr as well in case logging failed
        print(f"Error in main function: {str(e)}", file=sys.stderr)
        
if __name__ == "__main__":
    asyncio.run(main())