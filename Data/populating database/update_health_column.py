import json
import os
import psycopg2
import sys
from datetime import datetime
import numpy as np

# Add the parent directory to sys.path to import local modules
sys.path.append('/home/smurfs/agri_info2')
from ndvi_utils import ndvi_time_series_farm
from Utils.farm_level_alerts import assess_sugarcane_health, classify_sugarcane_phase, calculate_days_since_sowing

# Database connection details
conn = psycopg2.connect(
    dbname="smurf",
    user="clumsysmurf",
    password="clumsysmurf",
    host="localhost",
    port=5432
)
cur = conn.cursor()

def convert_health_status_to_int(health_status):
    """
    Convert health status string to integer for database storage
    
    Args:
        health_status (str): Health status from assess_sugarcane_health ('in danger', 'neutral', or 'healthy')
        
    Returns:
        int: 0 for 'in danger', 1 for 'neutral', 2 for 'healthy'
    """
    status_map = {
        "in danger": 3,
        "neutral": 2,
        "healthy": 1
    }
    return status_map.get(health_status, 1)  # Default to neutral if unknown

def update_farm_health():
    try:
        # Get all farms with geometries and planting dates
        cur.execute("""
            SELECT plot_number, geometry, date_of_planting, village_id, croptype
            FROM farm_data 
            WHERE geometry IS NOT NULL AND date_of_planting IS NOT NULL
            ORDER BY village_id
        """)
        farms = cur.fetchall()
        print(f"Found {len(farms)} farms with geometries and planting dates")
        
        if not farms:
            print("No farms with both geometry and planting date found, exiting...")
            return
        
        # Directory where TIF files are stored
        tif_directory = "Images/sentinel2"
        
        # Group farms by village for batch processing
        villages = {}
        for plot_number, geom_str, planting_date, village_id, croptype in farms:
            if village_id not in villages:
                villages[village_id] = []
            villages[village_id].append((plot_number, geom_str, planting_date, croptype))
        
        print(f"Processing {len(villages)} villages")
        
        # Process each village
        for village_id, village_farms in villages.items():
            print(f"\nProcessing village_id: {village_id}")
            
            # Get the TIF files for this village
            tif_files = [f for f in os.listdir(tif_directory) if f.endswith('.tif')]
            if not tif_files:
                print(f"No TIF files found in {tif_directory}, skipping village {village_id}...")
                continue
            
            # Use the most recent TIF file for NDVI calculation
            tif_files.sort(reverse=True)  # Sort in descending order to get most recent first
            tif_path = os.path.join(tif_directory, tif_files[0])
            print(f"Using TIF file: {tif_path}")
            
            # Prepare list of geometries and corresponding plot numbers
            geoms = []
            farm_data = []
            
            for plot_number, geom_str, planting_date, croptype in village_farms:
                try:
                    # Parse geometry from JSONB
                    geom = json.loads(geom_str)
                    geoms.append(geom)
                    farm_data.append((plot_number, planting_date, croptype))
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Error parsing geometry for plot {plot_number}: {e}")
            
            if not geoms:
                print(f"No valid geometries found for village {village_id}, skipping...")
                continue
            
            # Calculate NDVI for each farm
            try:
                print(f"Calculating NDVI values for {len(geoms)} farms...")
                ndvi_results = ndvi_time_series_farm(tif_path, geoms)
                
                # Current date for health assessment
                current_date = datetime.now()
                
                # Update health for each farm based on NDVI and growth phase
                for i, (plot_number, planting_date, croptype) in enumerate(farm_data):
                    if i >= len(geoms):
                        continue
                        
                    # Get NDVI value for this farm
                    geom_key = geoms[i]
                    if geom_key in ndvi_results:
                        ndvi_value, _ = ndvi_results[geom_key]
                        if np.isnan(ndvi_value):
                            print(f"Plot {plot_number}: NDVI is NaN, skipping health update")
                            continue
                            
                        # Calculate days since planting
                        planting_date_str = f"{planting_date} 00:00:00"
                        days_since_sowing, _, _ = calculate_days_since_sowing(
                            planting_date_str, 
                            current_date.strftime("%Y-%m-%d %H:%M:%S")
                        )
                        
                        # Get growth phase
                        growth_phase, _ = classify_sugarcane_phase(days_since_sowing)
                        
                        # Assess health based on NDVI and growth phase
                        health_assessment = assess_sugarcane_health(ndvi_value, growth_phase)
                        health_status = health_assessment["health_status"]
                        
                        # Convert to integer value for database
                        health_int = convert_health_status_to_int(health_status)
                        
                        # Update health in database
                        cur.execute("""
                            UPDATE farm_data
                            SET health = %s, ndvi_value = %s
                            WHERE plot_number = %s
                        """, (health_int, ndvi_value, plot_number))
                        
                        print(f"Updated plot {plot_number} health to {health_status} ({health_int})and NDVI to {ndvi_value:.4f}")
            except Exception as e:
                print(f"Error processing village {village_id}: {e}")
                
        # Commit all changes
        conn.commit()
        print("\nHealth and NDVI value columns update completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating health or NDVI: {e}")
    finally:
        # Close connection
        cur.close()
        conn.close()

if __name__ == "__main__":
    update_farm_health()