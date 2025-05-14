from datetime import datetime, timedelta

def calculate_days_since_sowing(sowing_date_str, current_date_str=None):
    """
    Calculate the number of days since the sugarcane was sown.
    
    Args:
        sowing_date_str (str): Sowing date in 'YYYY-MM-DD HH:MM:SS' format
        current_date_str (str, optional): Current date in 'YYYY-MM-DD HH:MM:SS' format.
                                         If None, current date is used.
    
    Returns:
        int: Number of days since sowing
        datetime: The sowing date as a datetime object
        datetime: The current date as a datetime object
    """
    try:
        sowing_date = datetime.strptime(sowing_date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise ValueError("Sowing date must be in 'YYYY-MM-DD HH:MM:SS' format")
    
    if current_date_str:
        try:
            current_date = datetime.strptime(current_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("Current date must be in 'YYYY-MM-DD HH:MM:SS' format")
    else:
        current_date = datetime.now()
    
    days_since_sowing = (current_date - sowing_date).days
    
    return days_since_sowing, sowing_date, current_date

def classify_sugarcane_phase(days_since_sowing):
    """
    Classify the sugarcane growth phase based on days since sowing.
    
    Args:
        days_since_sowing (int): Number of days since the sugarcane was sown
        
    Returns:
        str: Growth phase - "Germination", "Tillering", "Grand Growth", or "Ripening"
        int: Percentage completion of the current phase (0-100)
    """
    # Phase boundaries (days)
    phase_boundaries = {
        "Germination": (0, 35),
        "Tillering": (36, 100),
        "Grand Growth": (101, 270),
        "Ripening": (271, 400)  # Assuming a harvest cycle of around 365 days
    }
    
    # Determine the current growth phase
    current_phase = None
    for phase, (start_day, end_day) in phase_boundaries.items():
        if start_day <= days_since_sowing <= end_day:
            current_phase = phase
            # Calculate percentage completion within this phase
            phase_duration = end_day - start_day
            days_in_phase = days_since_sowing - start_day
            phase_completion_percentage = min(100, int((days_in_phase / phase_duration) * 100))
            break
    
    # If beyond 365 days, it's definitely in ripening (mature/over-mature)
    if current_phase is None:
        current_phase = "Ripening"
        phase_completion_percentage = 100
    
    return current_phase, phase_completion_percentage

def get_ndvi_thresholds(growth_phase):
    """
    Get NDVI thresholds for sugarcane health assessment based on growth phase.
    
    NDVI (Normalized Difference Vegetation Index) typically ranges from -1 to 1:
    - Higher values (approaching 1) indicate dense, healthy vegetation
    - Mid-range values indicate moderate vegetation
    - Lower values (approaching 0 or negative) indicate sparse or unhealthy vegetation
    
    The thresholds are adjusted based on the expected NDVI values for each growth phase.
    
    Args:
        growth_phase (str): The current growth phase of sugarcane
        
    Returns:
        dict: NDVI thresholds for the growth phase
    """
    # NDVI thresholds for each growth phase
    if growth_phase == "Germination":
        # During germination, NDVI is naturally low but should start increasing
        return {
            "danger_threshold": 0.15,  # Below this is concerning in germination phase
            "neutral_threshold": 0.25,  # Between danger and this value is neutral
            "healthy_threshold": 0.35   # Above this is considered healthy for this early stage
        }
    
    elif growth_phase == "Tillering":
        # Tillering phase should show significant increase in NDVI
        return {
            "danger_threshold": 0.35,  # Below this is concerning in tillering phase
            "neutral_threshold": 0.45,  # Between danger and this value is neutral
            "healthy_threshold": 0.55   # Above this is considered healthy for tillering
        }
    
    elif growth_phase == "Grand Growth":
        # During grand growth, NDVI should be at or near maximum values
        return {
            "danger_threshold": 0.55,  # Below this is concerning in grand growth phase
            "neutral_threshold": 0.65,  # Between danger and this value is neutral
            "healthy_threshold": 0.75   # Above this is considered healthy for grand growth
        }
    
    else:  # Ripening
        # During ripening, NDVI naturally decreases as the crop matures
        return {
            "danger_threshold": 0.40,  # Below this is concerning in ripening phase
            "neutral_threshold": 0.50,  # Between danger and this value is neutral
            "healthy_threshold": 0.60   # Above this is considered healthy for ripening
        }

def assess_sugarcane_health(ndvi_value, growth_phase):
    """
    Assess the health of sugarcane based on NDVI value and growth phase.
    
    Args:
        ndvi_value (float): The NDVI value for the sugarcane field
        growth_phase (str): The current growth phase of the sugarcane
        
    Returns:
        dict: Health assessment details
    """
    # Get appropriate thresholds for the growth phase
    thresholds = get_ndvi_thresholds(growth_phase)
    
    # Assess health based on thresholds
    if ndvi_value < thresholds["danger_threshold"]:
        health_status = "in danger"
        message = f"NDVI value ({ndvi_value:.2f}) is below expected range for {growth_phase} phase"
        alert_color = "#ef9a9a"  # Light red
    elif ndvi_value < thresholds["neutral_threshold"]:
        health_status = "neutral"
        message = f"NDVI value ({ndvi_value:.2f}) is in the moderate range for {growth_phase} phase"
        alert_color = "#fff59d"  # Light yellow
    else:
        health_status = "healthy"
        message = f"NDVI value ({ndvi_value:.2f}) is in the healthy range for {growth_phase} phase"
        alert_color = "#a5d6a7"  # Light green
    
    return {
        "health_status": health_status,
        "message": message,
        "alert_color": alert_color,
        "ndvi_value": ndvi_value,
        "growth_phase": growth_phase,
        "thresholds": thresholds
    }

def generate_sugarcane_alerts(sowing_date_str, ndvi_value, current_date_str=None):
    """
    Generate alerts for sugarcane health based on NDVI and growth phase.
    
    Args:
        sowing_date_str (str): Sowing date in 'YYYY-MM-DD HH:MM:SS' format
        ndvi_value (float): NDVI value for the sugarcane field
        current_date_str (str, optional): Current date for assessment
        
    Returns:
        dict: Alert information including health status, messages, and growth phase details
    """
    # Calculate days since sowing and get dates
    days_since_sowing, sowing_date, current_date = calculate_days_since_sowing(
        sowing_date_str, current_date_str
    )
    
    # Classify growth phase
    growth_phase, phase_completion = classify_sugarcane_phase(days_since_sowing)
    
    # Assess health based on NDVI and growth phase
    health_assessment = assess_sugarcane_health(ndvi_value, growth_phase)
    
    # Create complete alert response
    alert_response = {
        "days_since_sowing": days_since_sowing,
        "sowing_date": sowing_date_str,
        "assessment_date": current_date.strftime("%Y-%m-%d %H:%M:%S"),
        "growth_phase": growth_phase,
        "phase_completion_percentage": phase_completion,
        "health_assessment": health_assessment,
        "alert": {
            "title": f"Sugarcane {growth_phase} Phase - {health_assessment['health_status'].capitalize()}",
            "content": health_assessment["message"],
            "color": health_assessment["alert_color"]
        }
    }
    
    return alert_response

# Example usage
if __name__ == "__main__":
    # Example: Sugarcane sown on June 1, 2024, with NDVI assessment on April 19, 2025
    sowing_date = "2024-06-01 06:00:00"
    current_date = "2025-04-19 12:00:00"
    ndvi_value = 0.52  # Example NDVI value
    
    alert_info = generate_sugarcane_alerts(sowing_date, ndvi_value, current_date)
    
    # Print alert information
    print(f"Growth Phase: {alert_info['growth_phase']} ({alert_info['phase_completion_percentage']}% complete)")
    print(f"Health Status: {alert_info['health_assessment']['health_status']}")
    print(f"Alert: {alert_info['alert']['title']}")
    print(f"Message: {alert_info['alert']['content']}")