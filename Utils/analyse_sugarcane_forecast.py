import json
import requests
from datetime import datetime, timedelta

import requests
from datetime import datetime, timedelta

def get_sugarcane_stage(date_of_planting, forecast_time):
    """
    Determines which stage (phase) of sugarcane growth is current,
    given the planting date and the forecast time.
    Returns one of: "Germination", "Tillering", "Grand Growth", or "Ripening".
    """
    # Calculate the number of days between planting and this specific forecast time
    days_since_planting = (forecast_time - date_of_planting).days
    
    # Simple stage boundaries (based on typical sugarcane growth intervals)
    # Germination: ~1-35 days
    # Tillering: ~36-100 days
    # Grand growth: ~101-270 days
    # Ripening: >270 days
    if days_since_planting <= 35:
        return "Germination"
    elif days_since_planting <= 100:
        return "Tillering"
    elif days_since_planting <= 270:
        return "Grand Growth"
    else:
        return "Ripening"


def get_stage_thresholds(stage):
    """
    Returns the min/max temperature and min/max humidity thresholds for the
    given stage of sugarcane growth. Also returns a maximum 3-hour rainfall threshold.
    These values derive from typical sugarcane requirements, but have been adapted
    to align with the original code’s checks (10 mm rainfall threshold, etc.).
    
    For reference to temperature/humidity ranges:
    See BN_Sugarcane.pdf (Tables on critical stages and recommended conditions).
    """
    # The original code used fixed ranges: temp 20–35 °C, humidity 50–80%.
    # Below, we adapt these ranges for each stage based on general guidelines:
    # Germination: 20–32 °C, humidity check can remain ~50–80% for alerts
    # Tillering:   18–35 °C, humidity ~50–80%
    # Grand Growth:14–30 °C, humidity ~80–85%
    # Ripening:    20–30 °C, humidity ~50–55%
    # Max rainfall threshold remains 10 mm/3h from the original code.
    
    if stage == "Germination":
        return {
            "min_temp": 20.0,
            "max_temp": 32.0,
            "min_humidity": 50,
            "max_humidity": 80,
            "max_3h_rainfall": 10.0
        }
    elif stage == "Tillering":
        return {
            "min_temp": 18.0,
            "max_temp": 35.0,
            "min_humidity": 50,
            "max_humidity": 80,
            "max_3h_rainfall": 10.0
        }
    elif stage == "Grand Growth":
        return {
            "min_temp": 14.0,
            "max_temp": 30.0,
            "min_humidity": 80,
            "max_humidity": 85,
            "max_3h_rainfall": 10.0
        }
    else:  # "Ripening"
        return {
            "min_temp": 20.0,
            "max_temp": 30.0,
            "min_humidity": 50,
            "max_humidity": 55,
            "max_3h_rainfall": 10.0
        }


def fetch_forecast_data(lat, lon, api_key):
    """
    Fetches 5-day forecast data from the OpenWeather API (3-hourly intervals).
    Returns the raw JSON data or raises an exception on error.
    """
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    )
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def analyze_sugarcane_forecast(
    lat,
    lon,
    start_date_str,
    date_of_planting_str,
    api_key='13d9e58f69c0db07c240206f6b6e2662'
):
    """
    Analyzes the weather forecast for the next 36 hours starting from start_date_str
    at the location specified by (lat, lon).
    
    If the weather conditions (temperature, humidity, and rainfall) are not within
    the defined thresholds for the *current growth phase* of sugarcane, returns an error
    message in the format:
        "Not ideal for sugarcane in the next 36 hours:\n<reason>\n<reason>..."
    If everything is fine, returns None.
    
    Added 'date_of_planting_str' argument to determine the crop's growth phase
    dynamically. The overall *structure* and *output text* remain the same.
    """
    # Parse the user-supplied start_date
    try:
        start_datetime = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "Error: Start date/time must be in 'YYYY-MM-DD HH:MM:SS' format."
    
    # Parse the date_of_planting
    try:
        date_of_planting = datetime.strptime(date_of_planting_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "Error: Planting date/time must be in 'YYYY-MM-DD HH:MM:SS' format."

    # Determine the cutoff time: 36 hours from start
    end_datetime = start_datetime + timedelta(hours=36)

    # Fetch forecast data
    try:
        data = fetch_forecast_data(lat, lon, api_key)
    except requests.exceptions.RequestException as e:
        return f"Error fetching data from OpenWeather API: {e}"
    except ValueError:
        return "Error: Unexpected response format from OpenWeather API."

    if "list" not in data:
        return "Error: Unexpected response format from OpenWeather API."

    forecasts = data["list"]
    not_ideal_reasons = []

    for forecast in forecasts:
        forecast_time_str = forecast.get("dt_txt")
        if not forecast_time_str:
            continue

        try:
            forecast_time = datetime.strptime(forecast_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        # Check only forecasts within the 36-hour window
        if start_datetime <= forecast_time <= end_datetime:
            # Determine which stage of growth applies at this forecast_time
            current_stage = get_sugarcane_stage(date_of_planting, forecast_time)
            thresholds = get_stage_thresholds(current_stage)

            main_info = forecast.get("main", {})
            temp_c = main_info.get("temp")
            humidity = main_info.get("humidity")
            rain_3h = forecast.get("rain", {}).get("3h", 0.0)

            # Compare forecasted values to the stage-specific thresholds
            if (
                temp_c is not None
                and not (thresholds["min_temp"] <= temp_c <= thresholds["max_temp"])
            ):
                not_ideal_reasons.append(
                    f"{forecast_time_str}: Temperature {temp_c}°C out of ideal range "
                    f"({thresholds['min_temp']}-{thresholds['max_temp']}°C)."
                )

            if (
                humidity is not None
                and not (thresholds["min_humidity"] <= humidity <= thresholds["max_humidity"])
            ):
                not_ideal_reasons.append(
                    f"{forecast_time_str}: Humidity {humidity}% out of ideal range "
                    f"({thresholds['min_humidity']}-{thresholds['max_humidity']}%)."
                )

            if rain_3h > thresholds["max_3h_rainfall"]:
                not_ideal_reasons.append(
                    f"{forecast_time_str}: Rainfall {rain_3h} mm/3h exceeds "
                    f"{thresholds['max_3h_rainfall']} mm threshold."
                )

    # Preserve the exact same return structure as before
    if not_ideal_reasons:
        return "Not ideal for sugarcane in the next 36 hours:\n" + "\n".join(not_ideal_reasons)
    return None

# ✅ MAIN EXECUTION: Generates JSON Output for Next.js API
if __name__ == "__main__":
    lat = 30.7333
    lon = 76.7794
    start_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    api_key = '13d9e58f69c0db07c240206f6b6e2662'
    date_of_planting_str = "2024-06-01 06:00:00"

    alert_message = analyze_sugarcane_forecast(lat, lon, start_date_str, date_of_planting_str, api_key)


    if alert_message:
        alerts = [{"title": "Sugarcane Alert", "content": alert_message, "color": "#ef9a9a"}]
    else:
        alerts = []

    print(json.dumps({"alerts": alerts}))  
