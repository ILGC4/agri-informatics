# Farm Monitoring System (update_farm_alerts_db.py)

## Overview
This backend system provides comprehensive farm monitoring capabilities using satellite imagery analysis and Google Earth Engine (GEE) integration. The system is designed to monitor sugarcane farms, providing real-time insights on crop health, harvest readiness, and waterlogging conditions through advanced remote sensing techniques.

## Architecture
**Core Components**
1. Google Earth Engine Integration: Processes Sentinel-2 satellite imagery for vegetation analysis
2. Database Layer: PostgreSQL database for storing farm data and analysis results
3. Analysis Calculators: Specialized modules for different farm monitoring aspects
4. Logging System: Comprehensive logging with IST timezone support

**Technology Stack**
   - Python 3.x: Core programming language
   - Google Earth Engine (GEE): Satellite imagery processing and analysis
   - PostgreSQL: Primary database for farm data storage
   - asyncpg: Asynchronous PostgreSQL driver
   - psycopg2: Synchronous PostgreSQL driver for batch operations
   - Sentinel-2: ESA satellite constellation for Earth observation

## System Components
### Base Earth Engine Calculator (BaseEarthEngineCalculator)
The foundation class that basically handles:
   - Google Earth Engine authentication and initialization
   - Sentinel-2 image collection retrieval
   - Common geometry processing operations
   - Database connection management

**Key Features**
   - Service account authentication for GEE
   - Automatic cloud filtering (< 20% cloud coverage)
   - Time-series data retrieval with configurable date ranges
   - Asynchronous farm data fetching

### NDVI Health Calculator (GEENDVICalculator)
Monitors crop health using Normalized Difference Vegetation Index (NDVI) analysis.

**Functionality**
   - Growth Phase Classification: Automatically determines sugarcane growth stage (as defined previously)
      - Germination Phase (0-35 days)
      - Tillering Phase (35-120 days)
      - Grand Growth Phase (120-270 days)
      - Maturity/Ripening Phase (270+ days)
   - Adaptive Health Thresholds: Dynamic NDVI thresholds based on determined growth stage
   - Health Status Assessment: Classifies particular farm as 'healthy', 'neutral', or 'in danger'
   - Automated Database Updates: Updates health status and NDVI values 

**Health Assessment Logic**
  - Germination: danger < 0.15, neutral < 0.25, healthy ≥ 0.35
  - Tillering: danger < 0.35, neutral < 0.45, healthy ≥ 0.55
  - Grand Growth: danger < 0.55, neutral < 0.65, healthy ≥ 0.75
  - Maturity/Ripening: danger < 0.40, neutral < 0.50, healthy ≥ 0.60

### Harvest Readiness Calculator (Sugarcane Harvest Readiness Calculator)
Determines optimal harvest timing using multiple satellite-derived indicators.

**Analysis Parameters:**
   - Leaf Area Index (LAI): Measures crop canopy development
   - SWIR Reflectance: Monitors sugar accumulation in sugarcane
   - Temporal Stability: Analyzes trends over 2-4 week periods

**Harvest Readiness Criteria:**
   - LAI > 3.5 and stable for 2 weeks
   - SWIR reflectance increase of 5-10% over 3 observations
   - Confidence scoring based on multiple indicators

**Output Classifications:**
   - Ready (3): Both LAI and SWIR criteria met
   - Approaching (2): Partial criteria met with ≥50% confidence
   - Not Ready (1): Criteria not met

### Waterlogging Calculator (WaterLoggingCalculator)
Detects waterlogging conditions using Normalized Difference Water Index (NDWI).

**Detection Method:**
   - NDWI Calculation: (Green - NIR) / (Green + NIR) using Sentinel-2 bands B3 and B8
   - Multi-temporal Analysis: Compares recent satellite passes
   - Threshold-based Classification: Determines waterlogging severity

**Classification Thresholds:**
   - Waterlogged: NDWI > 0.3 for consecutive observations
   - At Risk: NDWI > 0.3 for single observation or > 0.2 trending upward
   - Normal: NDWI ≤ 0.2

## Database Schema
**Farm Data Table**
Core table storing farm information and analysis results (only relevant fields listed below):
```sql
- plot_number (PRIMARY KEY): Unique farm identifier
- geometry (JSONB): GeoJSON polygon for farm boundaries
- date_of_planting (TIMESTAMP): Crop planting date
- village_id (INTEGER): Village grouping identifier
- croptype (VARCHAR): Crop type (filtered for 'sugarcane')
- health (INTEGER): Health status (1=healthy, 2=neutral, 3=in danger)
- ndvi_value (FLOAT): Latest NDVI measurement
- harvest_readiness (INTEGER): Harvest status (1=not ready, 2=approaching, 3=ready)
- lai_value (FLOAT): Leaf Area Index value
- waterlogging (INTEGER): Waterlogging status (1=normal, 2=at risk, 3=waterlogged)
- ndwi_value (FLOAT): Latest NDWI measurement
```

## Configuration
**Google Earth Engine Authentication**
Requires service account JSON file for authentication:
   - Service account must have Earth Engine API access
   - Credentials automatically initialized on first use

## Logging System
**Multi-Logger Architecture**
The system implements separate loggers for each analysis module:
   1. NDVI Logger (gee_ndvi_health.log)
   2. Harvest Logger (gee_harvest_readiness.log)
   3. Waterlogging Logger (gee_waterlogging.log)

**Custom IST Formatter**
All logs are timestamped in Indian Standard Time (IST) with the format:

YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message

**Log Levels**
   - INFO: Normal operation status, processing updates
   - WARNING: Non-critical issues (insufficient data, missing images)
   - ERROR: Critical errors requiring attention

## Processing Workflow
1. Farm Data Retrieval 
```python
async def get_farm_data() -> List[Dict[str, Any]]
```
   - Fetches farms with valid geometry and planting dates
   - Groups farms by village for efficient processing
   - Filters by crop type (sugarcane only)

2. Satellite Image Processing
```python
def get_sentinel2_time_series(geometry, period_days=45)
```
   - Retrieves images from Sentinel-2 at specific time periods
   - Applies cloud covering (<20% cloud coverage)
   - Sorts by acquisition date for temporal analysis

3. Analysis Execution
Each calculator processes farms by the village:
   - Minimizes API calls through batch processing
   - Handles errors gracefully and consistently through detailed logging
   - Updates database atomically with transaction support

## Performance Optimizations
1. Village-Based Batching
   - API calls reduced by grouping farms by the village
   - Uses single satellite image per village wherever possible
   - Implements efficient geometric processing

2. Asynchronous Operations
   - Database operations use asyncpg for better performance
   - Parallel processing of farm data retrieval
   - Non-blocking I/O for large datasets

3. Error Handling
   - Comprehensive exception handling at multiple levels
   - Graceful degradation when satellite data is unavailable
   - Automatic retry mechanisms for transient failures

## API Dependencies
**Satellite Data Requirements**
   - Sentinel-2 L2A: Surface reflectance products
   - Minimum Observations: 3 cloud-free images per analysis period
   - Spatial Resolution: 10-20m depending on spectral band
   - Temporal Resolution: 5-day revisit cycle (with twin satellites)

**External Services**
   - Google Earth Engine: Primary satellite data source
   - Copernicus/ESA: Sentinel-2 data provider
   - PostgreSQL: Data persistence layer


## Deployment Considerations
1. Environment Setup
```bash
pip install earthengine-api
pip install asyncpg psycopg2-binary
pip install numpy pytz
```

2. Service Account Setup
   - Create Google Cloud Project with Earth Engine API enabled
   - Generate service account credentials
   - Download JSON key file to api_key/ directory
   - Set appropriate file permissions (600)

## Monitoring and Maintenance
**Health Checks**
   - Monitor log files for error patterns
   - Verify satellite data availability
   - Check database connection status
   - Validate GEE authentication

**Performance Metrics**
   - Processing time per village
   - Success/failure rates for each analysis type
   - Database update frequency
   - Satellite image availability rates

## Troubleshooting Common Issues
1. "No images found": Check date ranges and cloud coverage thresholds
2. Database connection errors: Verify credentials and network connectivity
3. GEE authentication failures: Ensure service account has proper permissions
4. Memory issues: Implement pagination for large farm datasets