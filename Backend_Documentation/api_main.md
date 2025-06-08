# api_main.py - Detailed Documentation

This document provides a detailed overview of the main FastAPI backend file `api_main.py` in the SMURF project. It describes the structure, key components, and the purpose of each major section and endpoint.

---

## Overview
`api_main.py` is the entry point for the SMURF backend. It implements a FastAPI server that provides RESTful APIs for satellite data collection, weather-based sugarcane analytics, farm health alerts, and database access. It integrates with external APIs (Planet, OpenWeather, Google Earth Engine) and a PostgreSQL/PostGIS database.

---

## Key Components

### Imports and Setup
- Imports standard libraries (os, json, datetime, etc.), FastAPI, asyncpg, pandas, numpy, rasterio, and custom utility modules from `Utils/`.
- Loads API keys for OpenWeather and Planet from JSON files in `api_key/` with error handling.
- Configures CORS middleware for frontend-backend communication.

### Data Models
Defines Pydantic models for request validation:
- `ProcessingRequest`: For NDVI/imagery processing jobs.
- `WeatherRequestFarm`, `WeatherRequestVillage`: For weather/forecast endpoints.
- `AlertRequest`: For farm alert queries.
- `SatelliteImage`: For satellite image metadata.

---

## API Endpoints

### Weather and Sugarcane Analytics
- **POST `/sugarcane-forecast`**
  - Accepts farm location and planting date.
  - Fetches weather forecast from OpenWeather API.
  - Compares forecast to optimal sugarcane growth thresholds and returns advisories.

- **GET `/sugarcane-stage`**
  - Returns the current growth stage of sugarcane given planting and forecast dates.

- **GET `/sugarcane-thresholds`**
  - Returns optimal temperature, humidity, and rainfall thresholds for a given sugarcane growth stage.

### Satellite Data Collection and Status
- **POST `/api/satellite/collect`**
  - Triggers satellite data collection for all villages and all supported satellite types (Sentinel-1, Sentinel-2, Landsat-9).
  - Uses Google Earth Engine via `Utils/satellite_gee.py`.

- **GET `/api/satellite/status`**
  - Returns the latest satellite image acquisition status for all villages.

- **GET `/api/satellite/images`**
  - Returns metadata for the most recent satellite images for all villages, including band types and acquisition dates.

### NDVI and Imagery Processing
- **POST `/view-results`**
  - Triggers NDVI/image processing using parameters stored in a pickle file.
  - Returns processed results, including NDVI values, image paths, and ranked polygons.

- **POST `/start-processing`**
  - Accepts processing parameters (date range, interval, geojson) and stores them in a pickle file.
  - Calls the processing function and returns results.

### Database Access
- **GET `/village-boundaries/{field_officer_id}`**
  - Returns village boundaries and centroids for a given field officer from the PostGIS database.

- **GET `/village/{village_id}/farms`**
  - Returns all farm boundaries and metadata for a given village.

### Farm Health Alerts
- **GET `/api/farm/{farm_id}/alerts`**
  - Returns health alerts for a specific farm based on NDVI value, sowing date, and current date.
  - Uses logic from `Utils/farm_level_alerts.py`.

---

## Supporting Functions
- **fetch_and_process_data**: Loads processing parameters, initializes Planet API, downloads imagery, computes NDVI, and returns results.
- **get_village_boundaries_by_officer**: Async function to fetch village boundaries for a field officer.
- **get_farm_data_by_village**: Async function to fetch all farm data for a village.

---

## Error Handling
- All endpoints use try/except blocks and return informative error messages via FastAPI's `HTTPException` or JSON responses.
- API key loading and file access are wrapped in error handling to prevent server crashes.

---

## Running the Server
- The file can be run directly (`python3 api_main.py`) or with Uvicorn (`uvicorn api_main:app --reload`).
- The main block starts the FastAPI server on `0.0.0.0:8000`.

---

## External Dependencies
- **API Keys:** Loaded from `api_key/` directory for OpenWeather and Planet.
- **Database:** Connects to PostgreSQL/PostGIS using asyncpg.
- **Satellite Data:** Uses Google Earth Engine and Planet APIs for imagery.
- **Utils:** Relies on custom modules in `Utils/` for NDVI, alerts, and satellite data collection.

---

## Summary
`api_main.py` is the central backend file for SMURF, orchestrating API endpoints, data processing, and integration with external services and the database. It is designed for extensibility, robust error handling, and efficient geospatial analytics.
