import requests
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = map(math.radians, [lat1, lat2])
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = (math.sin(dphi / 2)**2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_nearest_station_and_forecast(lat, lon, api_key):
    # 1) Find the nearest station
    url_station = (
        "https://api.openweathermap.org/data/2.5/station/find"
        f"?lat={lat}&lon={lon}&cnt=1&appid={api_key}"
    )
    station_resp = requests.get(url_station)
    station_data = station_resp.json()
    
    # Debug print
    print("Station API response:", station_data)
    
    # Check if the response is an error dictionary
    if isinstance(station_data, dict) and "cod" in station_data:
        # Means an error from OpenWeather: e.g. {"cod":"400", "message":"..."}
        raise ValueError(f"OpenWeather error: {station_data.get('message')}")
    
    # Otherwise, we hope it is a list of stations
    if not isinstance(station_data, list) or len(station_data) == 0:
        raise ValueError("No stations found or station data is invalid.")

    # Now it should be safe to access station_data[0]
    station_info = station_data[0].get("station")
    if not station_info:
        raise ValueError("Could not find 'station' info in the first item.")

    station_lat = station_info["coord"]["lat"]
    station_lon = station_info["coord"]["lon"]
    station_name = station_info["name"]

    # Check distance field
    distance_meters = station_data[0].get("distance")
    if distance_meters is not None:
        distance_km = distance_meters / 1000.0
    else:
        distance_km = haversine_distance(lat, lon, station_lat, station_lon)

    # 2) Fetch weather forecast for your lat/long
    url_forecast = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={api_key}"
    )
    forecast_resp = requests.get(url_forecast)
    forecast_data = forecast_resp.json()

    return {
        "requested_lat": lat,
        "requested_lon": lon,
        "nearest_station_name": station_name,
        "nearest_station_lat": station_lat,
        "nearest_station_lon": station_lon,
        "distance_to_station_km": distance_km,
        "forecast": forecast_data
    }

# Example usage:
if __name__ == "__main__":
    MY_API_KEY = "13d9e58f69c0db07c240206f6b6e2662"
    sample_lat = 27.692
    sample_lon = 79.902
    weather_info = get_nearest_station_and_forecast(sample_lat, sample_lon, MY_API_KEY)
    
    print("Nearest station:", weather_info["nearest_station_name"])
    print("Distance (km):", weather_info["distance_to_station_km"])
    print("Forecast data:", weather_info["forecast"])
