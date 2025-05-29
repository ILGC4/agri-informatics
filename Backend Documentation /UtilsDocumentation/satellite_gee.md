# Satellite Data Scheduler and Local Downloader Using GEE (satellite_gee.py)
This is a Python script for automated collection of satellite imagery from Google Earth Engine for multiple villages, with support for Sentinel-1, Sentinel-2, and Landsat 9 satellites.

## Features 
1. Multi-Satellite Support: Collects data from Sentinel-1 (SAR), Sentinel-2 (optical), and Landsat 9 (optical + thermal)
2. Automated Scheduling: Tracks previously downloaded images to avoid duplicates
3. Village-Based Collection: Fetches satellite data for all villages stored in PostgreSQL database
4. Smart Filtering: Applies cloud cover and quality filters to ensure high-quality imagery
5. IST Timezone Logging: All logs are in Indian Standard Time
6. Configurable: Can run for specific satellite types or all satellites
Google Earth Engine (GEE) setup is the same as for the Fram Monitoring System (update_farm_alerts_db.py)

## Basic Usage
**Run For All Satellites**
```bash
python satellite_gee.py
```

**Run For Individual Satellites**
```bash
python satellite_gee.py S1    # Sentinel-1 only
python satellite_gee.py S2    # Sentinel-2 only
python satellite_gee.py L9    # Landsat 9 only
```

## Output Structure
Images are saved in the following directory structure:
Images/
├── sentinel1/
│   └── v{village_id}/
├── sentinel2/
│   └── v{village_id}/
└── landsat/
    └── v{village_id}/

## File Naming Convention
Files are named as: {SATELLITE}_v{VILLAGE_ID}_{COORDINATES}_{IMAGE_DATE}_{DOWNLOAD_TIMESTAMP}.tif
Example: S2_v123_25.12345N_75.67890E_20241201_20241201_143022.tif

## Satellite Specifications
**Sentinel-2 (S2)**
   - Bands: B2, B3, B4, B5, B6, B7, B8, B11, B12 + SCL (Scene Classification)
   - Resolution: 10m (optical), 20m (SCL)
   - Revisit Period: 5 days
   - Cloud Filter: <20%

**Sentinel-1 (S1)**
   - Bands: VV, VH, angle
   - Resolution: 10m
   - Revisit Period: 6 days
   - Mode: IW (Interferometric Wide)

**Landsat 9 (L9)**
   - Optical Bands: SR_B2-SR_B7, QA_PIXEL
   - Thermal Band: ST_B10
   - Resolution: 30m (optical), 100m (thermal)
   - Revisit Period: 16 days
   - Cloud Filter: <20%

## Region of Interest
1. Buffer Size: 6.75km radius around each village centroid
2. Geometry: Circular buffer converted to rectangular bounds for download

## Logging
Separate log files are created based on satellite type:
   - logs/sentinel1_cron.log
   - logs/sentinel2_cron.log
   - logs/landsat_cron.log
   - logs/satellite_scheduler.log (default)

## Tracking System
The script maintains a JSON tracking database (download_tracking.json) to:
   - Record the latest image date for each village-satellite combination
   - Prevent duplicate downloads
   - Enable incremental updates

## Error Handling
1. Comprehensive logging with IST timestamps
2. Database connection error handling
3. Earth Engine API error handling
4. File system error handling
5. Graceful failure recovery per village/satellite

## Scheduling
The script looks back 30 days from the current date to catch any missed images during processing delays, while only downloading images newer than the last recorded download for each village-satellite combination.