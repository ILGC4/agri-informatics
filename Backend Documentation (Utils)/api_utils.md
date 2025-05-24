# Local Satellite Imagery Downloading & Preliminary Processing System (api_utils.py)

## Overview
This backend system provides satellite imagery processing capabilities for agricultural monitoring, specifically designed for sugarcane crop analysis. The system integrates with Planet Labs API for satellite data acquisition, PostgreSQL for data persistence, and OpenWeatherMap API for weather forecasting. This code is specifically for downloading satellite images locally for analysis purposes. 

## Architecture Components
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

## System Architecture
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

## API Workflow
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

## Naming Conventions
   - **Image Files:** Named by Planet item ID
   - **CSV Files:** {polygon_identifier}_filter_df.csv
   - **Polygon Identifiers:** Generated from coordinate precision

## Error Handling & Resilience
**Retry Mechanisms:**
   - Download failures: 3 attempts with exponential backoff
   - Asset activation: Built-in Planet API retry logic
   - Database connections: Handled by utility functions

**Exception Management:**
   - Graceful degradation for missing data
   - Comprehensive logging for debugging purposes
   - Exit codes for critical failures


## Configuration Management
**Environment Variables:**
   - PL_API_KEY: Planet Labs API authentication
   - Database connection parameters
   - OpenWeather API key

**Filter Configuration:**
   - Customizable quality thresholds
   - Flexible date range specifications
   - Adjustable search limits and intervals

**External Services:**
   - Planet Labs: Satellite imagery provider
   - OpenWeather: Weather data service
   - PostgreSQL: Persistent data storage

## Troubleshooting
**Common Issues:**
   - Authentication Failures: Verify Planet API key configuration
   - Database Connection: Check PostgreSQL service status and credentials 
   - Download Timeouts: Review network connectivity and retry configurations 
   - Geometric Errors: Validate GeoJSON format and coordinate systems

**Debugging Tools:**
   - Enable verbose logging in Planet SDK
   - Database query logging
   - Network request tracing
   - File system permission checks

## Dependencies Installation
```bash
pip install planet
pip install rasterio
pip install geopandas
pip install pandas
pip install requests
pip install psycopg2-binary  # PostgreSQL adapter
```