# Local & Additional Advanced Satellite Imagery Processing System (ndvi_utils.py)

## Overview
This backend module provides comprehensive satellite imagery processing capabilities, specifically designed for NDVI (Normalized Difference Vegetation Index) analysis and vegetation monitoring. The system processes multispectral satellite imagery, particularly from Planet Labs satellites, to calculate vegetation health metrics across different geographical areas.

## Architecture
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

## Key Features
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

## Data Processing Pipeline
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

## API Integration
The system integrates with external APIs through the Utils.api_utils module:
   - **PlanetData:** Handles Planet Labs satellite imagery access
   - **GeoJSON Processing:** Reads and processes geographic boundary files
   - **Coordinate Extraction:** Extracts corner coordinates for image georeferencing

## Output Formats
**Numerical Data**
   - NDVI Values: Float values ranging from -1 to 1
   - Statistical Metrics: Mean, min, max values for regions
   - Time Series Data: Temporal NDVI progression

**Visualizations**
   - RGB Composites: True-color satellite imagery
   - NDVI Maps: Color-coded vegetation index visualizations
   - Comparison Plots: Side-by-side RGB and NDVI analysis

## Dependencies 
```python
rasterio>=1.3.0
geopandas>=0.12.0
numpy>=1.21.0
matplotlib>=3.5.0
shapely>=1.8.0
```

## Configuration
The system uses several configurable parameters:
   - Band Indices: NIR (band 8), Red (band 6) - adjustable for different sensors
   - Coordinate Systems: Default EPSG:4326 with automatic transformation
   - Visualization Settings: Customizable colormaps and plot dimensions
   - Error Thresholds: Configurable NaN handling and data validation