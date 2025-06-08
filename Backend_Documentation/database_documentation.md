# Database Documentation - Sugarcane Farming Tool

## Database Setup

The database was created using PostgreSQL with PostGIS extension for geospatial data handling. Tables were designed with proper foreign key relationships to maintain data integrity. Primary keys use auto-incrementing sequences, and geometry columns are indexed for spatial query performance.

setup documentation: https://postgis.net/documentation/getting_started/

## Connection Parameters (on the server)

dbname="smurf"
user="clumsysmurf"
password="clumsysmurf"
host="localhost"
port=5432

## Overview
This database supports a geospatial web application designed for sugarcane farming operations in India, serving mill workers and farm management personnel.

## Table Structure

### `farm_data`
**Primary table containing individual farm plot information**

| Column | Type | Description |
|--------|------|-------------|
| `plot_number` | bigint | Unique plot identifier (Primary Key) |
| `farmer_name` | text | Name of the farmer |
| `father_name` | text | Father's name (as per Indian documentation) |
| `area` | double precision | Plot area in acres/hectares |
| `croptype` | text | Type of crop planted |
| `variety_group` | text | Sugarcane variety classification |
| `date_of_planting` | date | Planting date |
| `village_id` | integer | Reference to village (Foreign Key) |
| `geometry` | jsonb | Geospatial plot boundaries |
| `phone_number` | text | Farmer's contact number |
| `health` | integer | Crop health status code |
| `village_code_og` | integer | Original village code |
| `village_name` | text | Village name |
| `farmer_code` | bigint | Unique farmer identifier |
| `croptype_code` | integer | Crop type classification code |
| `variety_code` | integer | Variety classification code |
| `ndvi_value` | double precision | Normalized Difference Vegetation Index |
| `harvest_readiness` | integer | Harvest readiness indicator (Default: 1) |
| `lai_value` | double precision | Leaf Area Index |
| `waterlogging` | integer | Waterlogging status (Default: 1) |
| `ndwi_value` | double precision | Normalized Difference Water Index |

**Relationships:**
- Links to `village_data` via `village_id`

---

### `village_data`
**Village administrative and geographic information**

| Column | Type | Description |
|--------|------|-------------|
| `village_id` | integer | Unique village identifier (Primary Key) |
| `village_name` | text | Official village name |
| `field_officer_id` | integer | Assigned field officer (Foreign Key) |
| `village_size` | integer | Village population/size |
| `geometry` | MultiPolygon | Village boundary geometry |
| `centroid` | Point | Geographic center point |

**Relationships:**
- Links to `field_officer_credentials` via `field_officer_id`
- Referenced by `farm_data`

---

### `field_officer_credentials`
**Authentication and officer information**

| Column | Type | Description |
|--------|------|-------------|
| `field_officer_id` | integer | Unique officer identifier (Primary Key) |
| `name` | varchar(50) | Officer's full name |
| `username` | varchar(50) | Login username (Unique) |
| `password` | varchar(100) | Encrypted password |

**Relationships:**
- Referenced by `village_data`

---

### `satellite_images`
**Satellite imagery metadata for analysis**

| Column | Type | Description |
|--------|------|-------------|
| `tile_id` | integer | Unique tile identifier (Primary Key) |
| `image_path` | text | File path to satellite image |
| `geometry` | Point | Image capture location |
| `acquisition_date` | date | Date when image was captured |

## Usage Notes
- All geometry data uses SRID 4326 (WGS84 coordinate system)
- NDVI values range from -1 to 1 (higher values indicate healthier vegetation)
- **Phone numbers and agricultural indices (NDVI, LAI, NDWI) are currently randomly assigned for testing purposes**

## Key Features - to help understand the larger picture

### Geospatial Capabilities
- **Plot Mapping**: Farm boundaries stored as GeoJSON in `farm_data.geometry`
- **Village Boundaries**: Administrative boundaries in `village_data.geometry`
- **Satellite Integration**: Location-based imagery for crop monitoring

### Agricultural Monitoring
- **NDVI Analysis**: Vegetation health monitoring
- **Water Management**: NDWI values for irrigation planning
- **Harvest Planning**: Readiness indicators and LAI measurements

### Administrative Structure
- **Officer Assignment**: Field officers mapped to specific villages
- **Farmer Records**: Complete farmer information with contact details
- **Crop Classification**: Standardized crop and variety coding

---

## Python Utility Scripts

### weather_stuff.py
**Purpose:**
Fetches the nearest weather station and weather forecast for a given latitude/longitude using the OpenWeatherMap API.

**Key Functions:**
- `haversine_distance(lat1, lon1, lat2, lon2)`: Calculates the great-circle distance between two points on the Earth using the Haversine formula.
- `get_nearest_station_and_forecast(lat, lon, api_key)`: 
    1. Finds the nearest weather station to the provided coordinates using OpenWeatherMap's station API.
    2. Fetches the weather forecast for the provided coordinates.
    3. Returns a dictionary with the requested location, nearest station info, distance, and forecast data.

**Usage Example:**
```python
weather_info = get_nearest_station_and_forecast(27.692, 79.902, "<API_KEY>")
print(weather_info["nearest_station_name"])
print(weather_info["distance_to_station_km"])
print(weather_info["forecast"])
```

---

### database_utils.py
**Purpose:**
Provides utility functions for interacting with a PostgreSQL/PostGIS database for geospatial queries and satellite image metadata management.

**Key Functions:**
- `check_area_coverage(polygon, date, connection_params)`: 
    - Checks if any satellite image in the database covers the given polygon area on the specified date.
    - Returns the image path if found, otherwise `None`.
- `add_new_image(tile_id, acquisition_date, coordinates, image_path, filter_df_name, connection_params)`: 
    - Inserts a new satellite image record into the database with geospatial geometry and metadata.
    - Handles conversion of coordinates to WKT (Well-Known Text) for PostGIS compatibility.

**Usage Notes:**
- Requires a valid PostgreSQL connection and PostGIS-enabled database.
- Geometry is handled as WKT for SQL queries.
- Designed for use in geospatial/agricultural applications (e.g., satellite monitoring of farm plots).
