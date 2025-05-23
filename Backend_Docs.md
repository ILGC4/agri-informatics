# Sugarcane Monitoring and Utility Resource Framework (SMURF) Backend Documentation

## Sugarcane Growth Monitoring & Basic Village-Based Alert Framework (analyse_sugarcane_forecast.py)

A backend system that provides intelligent weather-based alerts for sugarcane cultivation by analysing growth stages and environmental conditions.

### Overview
This system monitors sugarcane growth stages nd provides real-time weather-based alerts for a particular region (a group of farms together or more simply, an entire village) to optimize agricultural practices. It integrates with the OpenWeather API to fetch weather forecasts and analyzes them against stage-specific agricultural requirements for sugarcane cultivation.

### Architecture 
1. Growth Stage Detection Engine 
   - Determines current sugarcane growth stage based on planting date
   - Maps weather requirements to specific growth stages for the crop
   - Supports four distinct growth phases

2. Weather Forecast Integration
   - Fetches 5-day weather forecasts from the OpenWeather API
   - Processes 3-hourly interval data
   - Analyzes temperature, humidity, and rainfall patterns specifically

3. Village Alert Generation System
   - Compares obtained forecasted conditions against stage-specific thresholds
   - Generates actionable and easily understandable alerts for non-ideal sugarcane conditions
   - Outputs JSON format compatible with the frontend

### Supported Growth Stages & Thresholds 
1. Germination Stage (1-35 days)
   - Temperature Range: 20-32°C
   - Humidity Range: 50-80%
   - Max Rainfall: 10mm/3h
   - Critical Period: Initial sprouting and root establishment

2. Tillering/Tilling Stage (36-100 days)
   - Temperature Range: 18-35°C
   - Humidity Range: 50-80%
   - Max Rainfall: 10mm/3h
   - Critical Period: Shoot multiplication and early growth

3. Grand Growth/Germination Stage (101-270 days)
   - Temperature Range: 14-30°C
   - Humidity Range: 80-85%
   - Max Rainfall: 10mm/3h
   - Critical Period: Rapid stem elongation and biomass accumulation

4. Ripening Stage (more than 270 days)
   - Temperature Range: 20-30°C
   - Humidity Range: 50-55%
   - Max Rainfall: 10mm/3h
   - Critical Period: Sugar accumulation and maturation

### API Integration
**OpenWeather API**
   - Endpoint: https://api.openweathermap.org/data/2.5/forecast
   - Data Format: 3-hourly forecasts for 5 days
   - Parameters: Latitude, longitude, metric units
   - Required Data: Temperature, humidity, precipitation

### Key Functions
**get_sugarcane_stage(date_of_planting, forecast_time)**
Determines the current growth stage based on:
   - Planting date
   - Current/forecast time
   - Days since planting calculation

**get_stage_thresholds(stage)**
Returns stage-specific environmental thresholds:
   - Temperature ranges (min/max)
   - Humidity ranges (min/max)
   - Maximum rainfall limits

**fetch_forecast_data(lat, lon, api_key)**
Retrieves weather forecast data:
   - Makes API requests to OpenWeather
   - Handles authentication and error responses
   - Returns structured JSON data

**analyze_sugarcane_forecast(lat, lon, start_date_str, date_of_planting_str, api_key)**
Main analysis function that:
   - Processes 36-hour forecast windows
   - Compares conditions against stage thresholds
   - Generates detailed alert messages
   - Returns JSON-formatted results

### Input Parameters
| Parameter     | Type | Format       | Description       |
|---------------|------|--------------|-------------------|
| lat    | float  | Decimal degrees   | Location latitude   |
| lon    | float  | Decimal degrees | Location longitude   |
| start_date_str  | string  | YYYY-MM-DD HH:MM:SS    | Forecast start time   |
| date_of_planting_str  | string  | YYYY-MM-DD HH:MM:SS    | Crop planting date   |
| api_key  | string  | API key    | OpenWeather API key   | 

### Output Format
The system generates an output which is compatible with our frontend.
```json
{
  "alerts": [
    {
      "title": "Sugarcane Alert",
      "content": "Not ideal for sugarcane in the next 36 hours:\n2024-05-23 12:00:00: Temperature 38°C out of ideal range (20-32°C).",
      "color": "#ef9a9a"
    }
  ]
}
```
The alerts in the frontend are segregated based on Daytime and Nighttime (given the location and time). 

**Alert Structure**
- Empty Array: No weather concerns detected
- Alert Object: Contains title, detailed content, and color coding
- Content Format: Timestamp-specific condition violations

### Error Handling
1. API Connectivity Issues
   - Network timeouts
   - Authentication failures
   - Rate limiting

2. Data Validation
   - Date format validation
   - Missing forecast data
   - Unexpected API responses

3. Input Validation
   - Coordinate range checking
   - Date string format verification

### Dependencies 
```python
import json
import requests
from datetime import datetime, timedelta
```
**Required Packages**
requests: HTTP library for API calls
datetime: Date/time manipulation
json: JSON data processing

### Configuration
1. Default Settings
   - Forecast Window: 36 hours
   - API Endpoint: OpenWeather 5-day forecast
   - Units: Metric system
   - Update Frequency: Real-time on request

2. Environment Variables
OPENWEATHER_API_KEY: API key for weather data access

### Usage Example
```python
lat = 30.7333  # Chandigarh, India
lon = 76.7794
start_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
date_of_planting_str = "2024-06-01 06:00:00"
api_key = 'your_openweather_api_key'

alert_message = analyze_sugarcane_forecast(
    lat, lon, start_date_str, date_of_planting_str, api_key
)

if alert_message:
    alerts = [{"title": "Sugarcane Alert", "content": alert_message, "color": "#ef9a9a"}]
else:
    alerts = []

print(json.dumps({"alerts": alerts}))
```

### Agricultural References
The growth stage thresholds are based on established agricultural research and best practices for sugarcane cultivation, with specific reference to optimal growing conditions documented in agricultural literature (BN_Sugarcane.pdf).

## Local Satellite Imagery Downloading & Preliminary Processing System (api_utils.py)

### Overview
This backend system provides satellite imagery processing capabilities for agricultural monitoring, specifically designed for sugarcane crop analysis. The system integrates with Planet Labs API for satellite data acquisition, PostgreSQL for data persistence, and OpenWeatherMap API for weather forecasting. This code is specifically for downloading satellite images locally for analysis purposes. 

### Architecture Components
1. Core Technologies
   - Python 3.x: Primary backend language
   - PostgreSQL: Database for storing image metadata and coverage information
   - Planet Labs API: Satellite imagery data source
   - OpenWeatherMap API: Weather data integration
   - Next.js Frontend: Web application interface (separate component)

2. Key Libraries and Dependencies
   - planet: Planet Labs API client
   - rasterio: Geospatial raster data processing
   - geopandas: Geospatial data manipulation
   - pandas: Data analysis and manipulation
   - asyncio: Asynchronous programming support
   - requests: HTTP client for external API calls

### System Architecture
1. Data Acquisition Layer (PlanetData Class)
The PlanetData class serves as the primary interface for satellite imagery acquisition:
**Key Features:**
   - Multi-temporal Search: Configurable date ranges with interval-based filtering
   - Quality Filters: Cloud cover and clear percentage thresholds
   - Geometric Filtering: Area-of-interest based image selection
   - Retry Logic: Robust download mechanisms with exponential backoff

**Configuration Parameters**
```python
{
    'clear_percent_filter_value': [min, max],  # Image clarity thresholds
    'cloud_cover_filter_value': float,         # Maximum cloud coverage
    'date_range': {'gte': 'YYYY-MM-DD', 'lte': 'YYYY-MM-DD'},
    'item_types': ['PSScene'],                 # Planet imagery types
    'limit': int,                              # Max results per search
    'interval': int                            # Day intervals for searches
}
```

2. Database Acquisition Layer
**Database Operations:**
   - Coverage Checking: check_area_coverage() - Verifies existing imagery for given polygon and date
   - Image Registration: add_new_image() - Stores new imagery metadata and file paths
   - Coordinate Extraction: Automatic extraction of corner coordinates from raster files

3. Geospatial Processing
**Coordinate System Handling:**
   - Automatic CRS detection from raster files
   - Transformation to WGS84 (EPSG:4326) for standardization
   - Corner coordinate extraction for spatial indexing

**Geometry Processing:**
   - GeoJSON parsing for area-of-interest definition
   - Multi-geometry support (FeatureCollections, single features, polygon arrays)
   - Coordinate-based naming convention for file organization

4. Agricultural Intelligence Layer
To reiterate, this layer includes growth stage specific thresholding for a weather-based alerting system.

**Sugarcane Growth Stage Detection**
Growth Stages:
   - Germination: 0-35 days after planting
   - Tillering: 36-100 days after planting  
   - Grand Growth: 101-270 days after planting
   - Ripening: 271+ days after planting

**Environmental Thresholds**
Each growth stage has specific environmental requirements:
   - Temperature ranges (min/max)
   - Humidity levels
   - Rainfall thresholds

**Weather Integration**
Integration with OpenWeatherMap API for forecast data:
   - 5-day weather forecasts
   - Temperature, humidity, and precipitation data
   - Location-based queries using latitude/longitude coordinates

### API Workflow
**Image Search Process**
1. Generate date ranges based on interval configuration
2. Apply geometric, quality, and temporal filters
3. Execute parallel searches across date ranges
4. Filter results to one image per day (lowest cloud cover)
5. Return consolidated item list and metadata DataFrame

**Image Download Process**
1. Check database for existing coverage
2. If not found, initiate Planet API download:
   - Activate asset
   - Wait for processing completion
   - Download to specified directory
   - Extract corner coordinates  
   - Register in database
3. Return local file path

**Batch Processing**
- Concurrent downloads using asyncio.gather()
- Configurable retry logic with exponential backoff
- Exception handling for individual download failures
- Progress tracking and logging

### Naming Conventions
**Image Files:** Named by Planet item ID
**CSV Files:** {polygon_identifier}_filter_df.csv
**Polygon Identifiers:** Generated from coordinate precision

### Error Handling & Resilience
**Retry Mechanisms:**
   - Download failures: 3 attempts with exponential backoff
   - Asset activation: Built-in Planet API retry logic
   - Database connections: Handled by utility functions

**Exception Management:**
   - Graceful degradation for missing data
   - Comprehensive logging for debugging purposes
   - Exit codes for critical failures


### Configuration Management
**Environment Variables:**
PL_API_KEY: Planet Labs API authentication
Database connection parameters
OpenWeather API key

**Filter Configuration:**
Customizable quality thresholds
Flexible date range specifications
Adjustable search limits and intervals

**External Services:**
Planet Labs: Satellite imagery provider
OpenWeather: Weather data service
PostgreSQL: Persistent data storage

### Troubleshooting
**Common Issues:**
   - Authentication Failures: Verify Planet API key configuration
   - Database Connection: Check PostgreSQL service status and credentials 
   - Download Timeouts: Review network connectivity and retry configurations 
   - Geometric Errors: Validate GeoJSON format and coordinate systems

**Debugging Tools:**
Enable verbose logging in Planet SDK
Database query logging
Network request tracing
File system permission checks

### Dependencies Installation
```bash
pip install planet
pip install rasterio
pip install geopandas
pip install pandas
pip install requests
pip install psycopg2-binary  # PostgreSQL adapter
```

## Local & Additional Advanced Satellite Imagery Processing System (ndvi_utils.py)

### Overview
This backend module provides comprehensive satellite imagery processing capabilities, specifically designed for NDVI (Normalized Difference Vegetation Index) analysis and vegetation monitoring. The system processes multispectral satellite imagery, particularly from Planet Labs satellites, to calculate vegetation health metrics across different geographical areas.

### Architecture
**Core Components**
The backend is built around several key processing modules:
   - Image Processing Pipeline - Handles raster data normalization and band manipulation
   - NDVI Calculation Engine - Computes vegetation indices from NIR and Red bands
   - Geospatial Analysis - Processes geographic boundaries and regions of interest
   - Time Series Analysis - Tracks vegetation changes over time
   - Visualization System - Generates RGB and NDVI comparison plots

**Technology Stack**
   - Python 3.x - Core runtime environment
   - Rasterio - Geospatial raster data I/O and processing
   - GeoPandas - Geospatial data manipulation and analysis
   - NumPy - Numerical computing and array operations
   - Matplotlib - Visualization and plotting
   - Shapely - Geometric operations and spatial analysis
   - Planet Labs API - Satellite imagery data source

### Key Features
1. Image Normalization
   - Function: normalize_bands(img)
   - Purpose: Normalizes satellite magery bands to 0-1 range for consistent processing
   - Process:
      - Calculates min/max values for each spectral band
      - Applies linear normalization: (value - min)/(max - min)
      - Handles edge cases wherever min equals to max

2. NDVI Time Series Analysis
   - Function: ndvi_time_series(tif_file, geom=None)
   - Purpose: Calculates NDVI values for entire images or specific geometric areas
   - Capabilities:
      - Full image NDVI calculation
      - Region specific NDVI analysis using provided geometries
      - Coordinate system transformation (EPSG:4326 to raster CRS)
      - Handles data clipping and masking operations

3. Multi-Geometry Farm Analysis
   - Function: ndvi_time_series_farm(tif_file, geoms=None)
   - Purpose: Batch processing of multiple farm boundaries or regions
   - Features:
      - Processes multiple geometries in a single operation
      - Returns dictionary mapping geometries to NDVI results
      - Optimized for agricultural monitoring applications

4. Visualization System
   - Function: plot_rgb_and_ndvi(rgb_img, ndvi, title, save_path=None)
   - Purpose: Creates side-by-side RGB and NDVI visualizations
   - Output:
      - RGB composite images
      - Color-mapped NDVI visualizations (RdYlGn colormap)
      - Optional file saving capabilities

### Data Processing Pipeline
**Input Data**
   - Format: GeoTIFF files containing multispectral satellite imagery
   - Bands: Expects at least 8 bands with NIR (band 8) and Red (band 6) channels
   - Geometry: GeoJSON geometries for area-of-interest analysis
   - Coordinate System: Supports automatic CRS transformation

**Processing Workflow (Step By Step)**
1. Data Ingestion: Load GeoTIFF files using Rasterio
2. Band Extraction: Extract relevant spectral bands (NIR, Red)
3. Normalization: Apply band-wise normalization for consistent processing
4. Geometry Processing: Transform and clip data to areas of interest
5. NDVI Calculation: Apply vegetation index formula: (NIR - Red) / (NIR + Red)
6. Statistical Analysis: Calculate mean values and handle NaN values
7. Output Generation: Return processed data and optional visualizations

**Error & Edge-Case Handling**
   - Division by Zero: Protected NDVI calculations with zero-sum detection
   - Invalid Data: NaN handling for corrupted or missing pixel values
   - Geometry Validation: Checks for valid geometry objects before processing
   - Warning Suppression: Filters common geospatial processing warnings

### API Integration
The system integrates with external APIs through the Utils.api_utils module:
**PlanetData:** Handles Planet Labs satellite imagery access
**GeoJSON Processing:** Reads and processes geographic boundary files
**Coordinate Extraction:** Extracts corner coordinates for image georeferencing

### Output Formats
**Numerical Data**
NDVI Values: Float values ranging from -1 to 1
Statistical Metrics: Mean, min, max values for regions
Time Series Data: Temporal NDVI progression

**Visualizations**
RGB Composites: True-color satellite imagery
NDVI Maps: Color-coded vegetation index visualizations
Comparison Plots: Side-by-side RGB and NDVI analysis

### Dependencies 
```python
rasterio>=1.3.0
geopandas>=0.12.0
numpy>=1.21.0
matplotlib>=3.5.0
shapely>=1.8.0
```

### Configuration
The system uses several configurable parameters:
   - Band Indices: NIR (band 8), Red (band 6) - adjustable for different sensors
   - Coordinate Systems: Default EPSG:4326 with automatic transformation
   - Visualization Settings: Customizable colormaps and plot dimensions
   - Error Thresholds: Configurable NaN handling and data validation

