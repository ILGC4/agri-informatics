# Sugarcane Growth Monitoring & Basic Village-Based Alert Framework (analyse_sugarcane_forecast.py)

A backend system that provides intelligent weather-based alerts for sugarcane cultivation by analysing growth stages and environmental conditions.

## Overview
This system monitors sugarcane growth stages nd provides real-time weather-based alerts for a particular region (a group of farms together or more simply, an entire village) to optimize agricultural practices. It integrates with the OpenWeather API to fetch weather forecasts and analyzes them against stage-specific agricultural requirements for sugarcane cultivation.

## Architecture 
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

## Supported Growth Stages & Thresholds 
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

## API Integration
**OpenWeather API**
   - Endpoint: https://api.openweathermap.org/data/2.5/forecast
   - Data Format: 3-hourly forecasts for 5 days
   - Parameters: Latitude, longitude, metric units
   - Required Data: Temperature, humidity, precipitation

## Key Functions
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

## Input Parameters
| Parameter     | Type | Format       | Description       |
|---------------|------|--------------|-------------------|
| lat    | float  | Decimal degrees   | Location latitude   |
| lon    | float  | Decimal degrees | Location longitude   |
| start_date_str  | string  | YYYY-MM-DD HH:MM:SS    | Forecast start time   |
| date_of_planting_str  | string  | YYYY-MM-DD HH:MM:SS    | Crop planting date   |
| api_key  | string  | API key    | OpenWeather API key   | 

## Output Format
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

## Error Handling
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

## Configuration
1. Default Settings
   - Forecast Window: 36 hours
   - API Endpoint: OpenWeather 5-day forecast
   - Units: Metric system
   - Update Frequency: Real-time on request

2. Environment Variables
OPENWEATHER_API_KEY: API key for weather data access

## Usage Example
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

## Agricultural References
The growth stage thresholds are based on established agricultural research and best practices for sugarcane cultivation, with specific reference to optimal growing conditions documented in agricultural literature (BN_Sugarcane.pdf).