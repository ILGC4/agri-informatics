import os
import asyncio
import pathlib
import rasterio
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from ndvi_utils import normalize_bands, ndvi_time_series, plot_rgb_and_ndvi
from Utils.farm_level_alerts import generate_sugarcane_alerts
from Utils.api_utils import PlanetData, read_geojson, get_sugarcane_stage, get_stage_thresholds, fetch_forecast_data
from fastapi.middleware.cors import CORSMiddleware
from Utils.satellite_gee import SatelliteDataCollector
from pydantic import BaseModel
import pickle
import asyncpg
from typing import Dict, List, Optional
import json
import requests
from datetime import datetime, timedelta

app = FastAPI()

OPENWEATHER_API_KEY = "13d9e58f69c0db07c240206f6b6e2662"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "*"],
    allow_headers=["*"],
)

class ProcessingRequest(BaseModel):
    startDate: str
    endDate: str
    interval: int
    geoJsonData: dict

app.mount("/plots", StaticFiles(directory="plots"), name="plots")

class WeatherRequestFarm(BaseModel):
    lat: float
    lon: float
    start_date: str
    date_of_planting: str

class WeatherRequestVillage(BaseModel):
    lat: float
    lon: float
    start_date: str

class AlertRequest(BaseModel):
    farm_id: int
    sowing_date: str
    ndvi_value: float
    current_date: str = None

class SatelliteImage(BaseModel):
    image_id: str
    satellite_type: str
    acquisition_date: str
    download_date: str
    path: str
    village_id: int
    bands: str

@app.post("/sugarcane-forecast")
async def analyze_sugarcane_forecast(request: WeatherRequestFarm):
    try:
        start_datetime = datetime.strptime(request.start_date, "%Y-%m-%d %H:%M:%S")
        date_of_planting = datetime.strptime(request.date_of_planting, "%Y-%m-%d %H:%M:%S")
        end_datetime = start_datetime + timedelta(hours=48)

        data = fetch_forecast_data(request.lat, request.lon, OPENWEATHER_API_KEY)

        if "list" not in data:
            raise HTTPException(status_code=500, detail="Unexpected response format from OpenWeather API.")

        forecasts = data["list"]
        not_ideal_reasons = []

        for forecast in forecasts:
            forecast_time_str = forecast.get("dt_txt")
            if not forecast_time_str:
                continue

            forecast_time = datetime.strptime(forecast_time_str, "%Y-%m-%d %H:%M:%S")

            if start_datetime <= forecast_time <= end_datetime:
                current_stage = get_sugarcane_stage(date_of_planting, forecast_time)
                thresholds = get_stage_thresholds(current_stage)

                main_info = forecast.get("main", {})
                temp_c = main_info.get("temp")
                humidity = main_info.get("humidity")
                rain_3h = forecast.get("rain", {}).get("3h", 0.0)

                if temp_c is not None and not (thresholds["min_temp"] <= temp_c <= thresholds["max_temp"]):
                    not_ideal_reasons.append(
                        f"{forecast_time_str}: Temperature {temp_c}°C out of ideal range "
                        f"({thresholds['min_temp']}-{thresholds['max_temp']}°C)."
                    )

                if humidity is not None and not (thresholds["min_humidity"] <= humidity <= thresholds["max_humidity"]):
                    not_ideal_reasons.append(
                        f"{forecast_time_str}: Humidity {humidity}% out of ideal range "
                        f"({thresholds['min_humidity']}-{thresholds['max_humidity']}%)."
                    )

                if rain_3h > thresholds["max_3h_rainfall"]:
                    not_ideal_reasons.append(
                        f"{forecast_time_str}: Rainfall {rain_3h} mm/3h exceeds "
                        f"{thresholds['max_3h_rainfall']} mm threshold."
                    )

        if not_ideal_reasons:
            return {"status": "warning", "message": "Not ideal for sugarcane in the next 36 hours", "details": not_ideal_reasons}
        return {"status": "success", "message": "Weather conditions are ideal for sugarcane in the next 36 hours"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/sugarcane-stage")
async def get_sugarcane_growth_stage(
    date_of_planting: str = Query(..., description="Date of planting in format YYYY-MM-DD HH:MM:SS"),
    forecast_date: str = Query(..., description="Forecast date in format YYYY-MM-DD HH:MM:SS")
):
    """
    API to determine the current growth stage of sugarcane given a planting date and a forecast date.
    """
    try:
        date_of_planting_dt = datetime.strptime(date_of_planting, "%Y-%m-%d %H:%M:%S")
        forecast_date_dt = datetime.strptime(forecast_date, "%Y-%m-%d %H:%M:%S")

        stage = get_sugarcane_stage(date_of_planting_dt, forecast_date_dt)

        return {"status": "success", "growth_stage": stage}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD HH:MM:SS")
    
@app.get("/sugarcane-thresholds")
async def get_sugarcane_thresholds(stage: str = Query(..., description="Growth stage of sugarcane")):
    """
    API to return optimal temperature, humidity, and rainfall thresholds for a given sugarcane growth stage.
    """
    thresholds = get_stage_thresholds(stage)

    if not thresholds:
        raise HTTPException(status_code=400, detail="Invalid growth stage. Choose from Germination, Tillering, Grand Growth, Ripening.")

    return {"status": "success", "stage": stage, "thresholds": thresholds}

@app.post("/api/satellite/collect")
async def collect_satellite_data():
    # Trigger satellite data collection for all satellite types (S1, S2, L9) for all villages.
    try:
        # Set paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        service_account_json_path = os.path.join(script_dir, 'api_key/ee-chaitanyamodi-6874ede8f64c.json')
        base_dir = os.path.join(script_dir, 'Images/Villages')
        
        # Create collector instance
        collector = SatelliteDataCollector(service_account_json_path, base_dir)
        
        # Process for all three satellite types sequentially
        results = {}
        
        # Collect Sentinel-2 data
        try:
            await collector.collect_satellite_data("S2")
            results["S2"] = "success"
        except Exception as e:
            results["S2"] = f"error: {str(e)}"
        
        # Collect Sentinel-1 data
        try:
            await collector.collect_satellite_data("S1")
            results["S1"] = "success"
        except Exception as e:
            results["S1"] = f"error: {str(e)}"
        
        # Collect Landsat-9 data
        try:
            await collector.collect_satellite_data("L9")
            results["L9"] = "success"
        except Exception as e:
            results["L9"] = f"error: {str(e)}"
        
        return JSONResponse(
            content={
                "status": "completed",
                "message": "Satellite data collection completed",
                "results": results
            }
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Error in satellite data collection: {str(e)}"
            },
            status_code=500
        )

@app.get("/api/satellite/status")
async def get_satellite_status():
    # Get the status of satellite data collection for all villages.
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.join(script_dir, 'Images/Villages')
        tracking_db_path = os.path.join(base_dir, 'download_tracking.json')
        
        if not os.path.exists(tracking_db_path):
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "No satellite data collection has been performed yet",
                    "data": []
                }
            )
        
        with open(tracking_db_path, 'r') as f:
            tracking_data = json.load(f)
        
        # Process tracking data into a more readable format
        village_statuses = []
        for village_id, satellite_data in tracking_data.items():
            village_status = {
                "village_id": int(village_id), 
                "satellites": {}
            }
            
            for sat_type, image_date in satellite_data.items():
                satellite_map = {"S1": "Sentinel-1", "S2": "Sentinel-2", "L9": "Landsat-9"}
                
                # Convert the image date string (YYYYMMDD) to a datetime object
                try:
                    acq_date = datetime.strptime(image_date, '%Y%m%d')
                    formatted_date = acq_date.strftime("%Y-%m-%d")
                    days_since_acquisition = (datetime.now() - acq_date).days
                except ValueError:
                    # Handle any unexpected format issues
                    formatted_date = image_date
                    days_since_acquisition = "unknown"
                
                village_status["satellites"][sat_type] = {
                    "name": satellite_map.get(sat_type, sat_type),
                    "latest_image_date": formatted_date,
                    "days_since_acquisition": days_since_acquisition
                }
            
            village_statuses.append(village_status)
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Retrieved satellite image status",
                "data": village_statuses
            }
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Error retrieving satellite status: {str(e)}"
            },
            status_code=500
        )

@app.get("/api/satellite/images")
async def get_all_village_satellite_images():
    # Get the most recent satellite images for all villages.

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.join(script_dir, 'Images')
        
        # Map satellite type codes to directory names
        sat_dirs = {
            "S1": "sentinel1",
            "S2": "sentinel2", 
            "L9": "landsat"
        }
        
        # Map satellite type codes to full names
        sat_names = {
            "S1": "Sentinel-1",
            "S2": "Sentinel-2", 
            "L9": "Landsat-9"
        }
        
        # Map satellite types to band descriptions
        band_descriptions = {
            "S1": "VV+VH+angle",
            "S2": "RGB+NIR+RedEdge+SWIR",
            "L9": "RGB+NIR+SWIR+QA",
            "L9_thermal": "Thermal"
        }
        
        # Dictionary to store results by village
        village_images: Dict[int, Dict[str, Dict]] = {}
        
        # Process all satellite types
        for sat_type, sat_dir in sat_dirs.items():
            satellite_dir = os.path.join(base_dir, sat_dir)
            
            if not os.path.exists(satellite_dir):
                continue
                
            # List all village directories
            for village_dir_name in os.listdir(satellite_dir):
                if not village_dir_name.startswith('v'):
                    continue
                    
                try:
                    # Extract village ID from directory name (format: v{id})
                    village_id = int(village_dir_name[1:])
                    
                    # Initialize village entry if not exists
                    if village_id not in village_images:
                        village_images[village_id] = {
                            "S1": None,
                            "S2": None,
                            "L9": None,
                            "S2_SCL": None,  # Scene Classification Layer for Sentinel-2
                            "L9_thermal": None  # Thermal band for Landsat-9
                        }
                    
                    village_dir = os.path.join(satellite_dir, village_dir_name)
                    
                    # Find the latest image for this satellite type
                    latest_image = None
                    latest_date = None
                    
                    # List all .tif files in the village directory
                    for filename in os.listdir(village_dir):
                        if not filename.endswith('.tif'):
                            continue
                            
                        # Parse information from filename
                        # Format is like: S2_v2_29.3080N_78.5033E_20240415_20240419_123456.tif
                        parts = filename.split('_')
                        if len(parts) < 6:
                            continue
                            
                        file_sat_type = parts[0]
                        acquisition_date = parts[4]  # YYYYMMDD format
                        
                        # Update latest image if this one is newer
                        if latest_date is None or acquisition_date > latest_date:
                            latest_date = acquisition_date
                            
                            # Format the date
                            try:
                                acq_date = datetime.strptime(acquisition_date, '%Y%m%d')
                                acq_date_formatted = acq_date.strftime('%Y-%m-%d')
                            except:
                                acq_date_formatted = acquisition_date
                                
                            download_date = '_'.join(parts[5:]).replace('.tif', '')
                            
                            latest_image = {
                                "image_id": filename.replace('.tif', ''),
                                "satellite_type": sat_names.get(file_sat_type.split('_')[0], file_sat_type),
                                "acquisition_date": acq_date_formatted,
                                "download_date": download_date,
                                "path": os.path.join(village_dir, filename),
                                "village_id": village_id,
                                "bands": band_descriptions.get(file_sat_type, "Unknown")
                            }
                    
                            # Include band type information in the image data
                            if "thermal" in filename.lower():
                                latest_image["band_type"] = "thermal"
                            elif "SCL" in filename:
                                latest_image["band_type"] = "scene_classification"
                            else:
                                latest_image["band_type"] = "standard"
                    
                    # Save the latest image for this satellite type
                    if latest_image:
                        # For thermal and SCL, add them as additional satellite types
                        if "thermal" in filename.lower():
                            # Create L9_thermal entry if needed
                            if "L9_thermal" not in village_images[village_id]:
                                village_images[village_id]["L9_thermal"] = None
                            village_images[village_id]["L9_thermal"] = latest_image
                        elif "SCL" in filename:
                            # Create S2_SCL entry if needed
                            if "S2_SCL" not in village_images[village_id]:
                                village_images[village_id]["S2_SCL"] = None
                            village_images[village_id]["S2_SCL"] = latest_image
                        else:
                            # Standard bands
                            village_images[village_id][sat_type] = latest_image
                
                except ValueError:
                    # Skip directories that don't have a proper village ID format
                    continue
        
        # Create the final response
        results = []
        for village_id, satellites in village_images.items():
            # Get latest images of each type (if available)
            latest_images = []
            for sat_type in ["S1", "S2", "L9", "S2_SCL", "L9_thermal"]:
                if sat_type in satellites and satellites[sat_type]:
                    latest_images.append(satellites[sat_type])
            
            results.append({
                "village_id": village_id,
                "image_count": len(latest_images),
                "latest_images": latest_images
            })
        
        # Sort results by village ID
        results = sorted(results, key=lambda x: x["village_id"])
        
        return JSONResponse(
            content={
                "status": "success",
                "village_count": len(results),
                "villages": results
            }
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Error retrieving satellite images: {str(e)}"
            },
            status_code=500
        )

# Route to handle fetching results after user clicks "View Results"
@app.post("/view-results")
async def view_results():
    try:
        # Start processing after fetching results from Planet
        result = await fetch_and_process_data()

        # Prepare the results
        return JSONResponse(
            content={
                "status": "success",
                "dates": result["dates"],
                "images": result["images"],
                "ranked_polygons": result["ranked_polygons"],
                "geojson_data": result["geojson_data"],
                "message": "Results processed successfully!"
            }
        )

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

async def fetch_and_process_data():
    try:
        # Load the processing data from the pickle file
        processing_data_path = "Data/processing_data.pkl"
        
        # Check if the pickle file exists
        if not os.path.exists(processing_data_path):
            raise Exception("Processing data not found. Please start the process first.")
        
        # Load the stored data (start_date, end_date, interval, geojson_data)
        with open(processing_data_path, 'rb') as f:
            processing_data = pickle.load(f)

        # Extract variables from the loaded data
        start_date = str(processing_data['start_date'])
        end_date = str(processing_data['end_date'])
        interval = processing_data['interval']
        geojson_data = processing_data['geojson_data']

        # Initialize the PlanetData with the extracted variables
        credentials = {'API_KEY': 'PLAK6d9e3e666f9b461c92468569a4b270c7'}

        planet_data = PlanetData(
            credentials=credentials,
            clear_percent_filter_value=(0, 100),
            date_range={'gte': start_date, 'lte': end_date},
            cloud_cover_filter_value=(0, 100),
            item_types=['PSScene'],
            limit=10,
            directory="./Images/",
            interval=int(interval)
        )

        # Initialize lists to store image and plot results
        csv_data = []  # To store data for the CSV file
        image_data = []  # Store image paths and corresponding plot numbers
        plot_results = []  # To store results for each plot
        ndvi_results = [] # Storing the clipped mean values

        # Loop over geometries (GeoJSON data)
        for geom_idx, geom in enumerate(geojson_data['features']):
            plot_number = geom['properties'].get('Plot Number')
            print(f"Processing geometry for Plot Number: {plot_number}...")

            # Extract the geometry data
            geometry = geom.get('geometry')
            if not geometry:
                print(f"No geometry found for plot: {plot_number}")
                continue

            # Pass the geometry to download_multiple_assets
            results, item_list, search_df = await planet_data.download_multiple_assets(geom=geometry, asset_type_id='ortho_analytic_8b_sr')
            if results:
                tif_files = [result for result in results if pathlib.Path(result).suffix == '.tif']
            else:
                print(f"No results found for plot: {plot_number}")
                continue

            # Loop over TIFF files and process them
            for idx, tif_file in enumerate(tif_files):
                filename = str(tif_file)
                date_str = filename[7:15]  # Extract date from filename

                # Save the date for later use
                state.dates.append(date_str)

                # Open and process the TIFF file
                with rasterio.open(tif_file) as src:
                    ndvi_full_mean, ndvi_full, ndvi_clipped_mean, ndvi_clipped = ndvi_time_series(tif_file, geom)

                    ndvi_results.append({
                        'plot_number': plot_number,
                        'ndvi_clipped_mean': ndvi_clipped_mean
                    })

                    # Normalize and plot RGB and NDVI for the full image
                    full_img = src.read()
                    normalized_full_img = normalize_bands(full_img)
                    blue = normalized_full_img[1, :, :]
                    green = normalized_full_img[3, :, :]
                    red = normalized_full_img[5, :, :]
                    rgb_img_full = np.dstack((red, green, blue))

                    # Save the full image NDVI plot
                    full_image_path = f'plots/{plot_number}_{date_str}_full_image_{idx + 1}.png'
                    plot_rgb_and_ndvi(rgb_img_full, ndvi_full, "Full Image", save_path=full_image_path)

                    # Add the full image path and plot number to the image data
                    image_data.append({
                        'plot_number': plot_number,
                        'image_path': full_image_path,
                        'date': date_str
                    })

                    # Add data to CSV list
                    csv_data.append({
                        'plot_number': plot_number,
                        'date': date_str,
                        'ndvi_image_path': full_image_path,
                        'polygon_coordinates': json.dumps(geometry)  # Save polygon as JSON string
                    })

        # Sorting polygons based on NDVI values
        ranked_polygons = sorted(ndvi_results, key=lambda x: x['ndvi_clipped_mean'], reverse=True)

        # Save data to CSV file
        csv_file_path = "/ndvi_image_metadata.csv"
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_file_path, index=False)
        print(f"CSV file saved at: {csv_file_path}")

        # Return the processed results
        return {"dates": state.dates, "images": image_data, "csv_file": csv_file_path, "ranked_polygons": ranked_polygons,
        "geojson_data": geojson_data}

    except Exception as e:
        print(f"Error during fetch and process: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/start-processing")
async def start_processing(request: ProcessingRequest):
    try:
        # Extract the data from the request body
        start_date = request.startDate
        end_date = request.endDate
        interval = request.interval
        geojson_data = request.geoJsonData
        
        # Store the data in a pickle file
        processing_data = {
            "start_date": start_date,
            "end_date": end_date,
            "interval": interval,
            "geojson_data": geojson_data
        }
        
        # Store the data in a temporary file (or any location you prefer)
        processing_data_path = "Data/processing_data.pkl"
        with open(processing_data_path, 'wb') as f:
            pickle.dump(processing_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        # print(f"Processing data saved: {processing_data}")

        # Call fetch_and_process_data to fetch and process the data
        processing_results = await fetch_and_process_data()

        # Return the results from fetch_and_process_data
        return JSONResponse(content={
            "status": "success",
            "message": "Processing started and completed!",
            "data": processing_results
        })

    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

async def get_village_boundaries_by_officer(field_officer_id: int) -> dict:
    # Retrieve village boundaries for a specific field officer.

    try:
        conn = await asyncpg.connect(
            user='smurfs',
            password='smurfs123',
            database='smurf',
            host='localhost',
            port='5432'
        )
        
        # First, check if the field officer exists
        check_query = """
            SELECT EXISTS(
                SELECT 1 FROM field_officer_credentials 
                WHERE field_officer_id = $1
            )
        """
        officer_exists = await conn.fetchval(check_query, field_officer_id)
        
        if not officer_exists:
            await conn.close()
            raise Exception(f"Field officer with ID {field_officer_id} not found in the database.")
        
        # Query to get village boundaries - now including centroid
        query = """
            SELECT 
                v.village_id,
                v.village_name,
                v.field_officer_id,
                v.village_size,
                ST_AsGeoJSON(v.geometry) as geometry,
                ST_AsGeoJSON(v.centroid) as centroid
            FROM 
                village_data v
            WHERE 
                v.field_officer_id = $1
            ORDER BY 
                v.village_id
        """
        
        rows = await conn.fetch(query, field_officer_id)
        await conn.close()
        
        # If no villages are found for a valid field officer, return an appropriate message
        if not rows:
            raise Exception(f"No villages found for field officer with ID {field_officer_id}.")
        
        features = []
        for row in rows:
            geometry = json.loads(row['geometry'])
            centroid = json.loads(row['centroid']) if row['centroid'] else None
            
            features.append({
                "type": "Feature",
                "properties": {
                    "village_id": row['village_id'],
                    "village_name": row['village_name'],
                    "field_officer_id": row['field_officer_id'],
                    "village_size": row['village_size'],
                    "centroid": centroid
                },
                "geometry": geometry
            })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
        
    except Exception as e:
        print(f"Error in get_village_boundaries_by_officer: {e}")
        raise Exception(f"Database error: {str(e)}")

@app.get("/village-boundaries/{field_officer_id}")
async def village_boundaries_endpoint(field_officer_id: int):
    # API endpoint to retrieve village boundaries for a specific field officer.
    try:
        result = await get_village_boundaries_by_officer(field_officer_id)
        return JSONResponse(
            content={
                "status": "success",
                "data": result,
                "message": f"Village boundaries for field officer {field_officer_id} retrieved successfully!"
            }
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e)
            },
            status_code=404 if "not found" in str(e) or "No villages found" in str(e) else 500
        )

async def get_farm_data_by_village(village_id: int) -> Dict:
    # Retrieve farm data for a specific village.
    try:
        conn = await asyncpg.connect(
            user='smurfs',
            password='smurfs123',
            database='smurf',
            host='localhost',
            port='5432'
        )
        
        # First check if the village exists and get basic info
        village_query = """
            SELECT 
                village_id,
                village_name,
                village_size
            FROM 
                village_data
            WHERE 
                village_id = $1
        """
        
        village_row = await conn.fetchrow(village_query, village_id)
        
        if not village_row:
            await conn.close()
            raise Exception(f"Village with ID {village_id} not found.")
        
        # Get all farms for this village
        farms_query = """
            SELECT 
                plot_number,
                farmer_name,
                father_name,
                area,
                croptype,
                variety_group,
                date_of_planting,
                phone_number,
                health,
                farmer_code,
                geometry as farm_boundaries
            FROM 
                farm_data
            WHERE 
                village_id = $1
            ORDER BY 
                plot_number
        """
        
        farm_rows = await conn.fetch(farms_query, village_id)
        await conn.close()
        
        # If no farms found, return an appropriate message
        if not farm_rows:
            raise Exception(f"No farms found for village with ID {village_id}.")
        
        # Format the results
        farms = []
        for row in farm_rows:
            # Process the farm geometry (stored as JSONB)
            farm_geometry = row['farm_boundaries']
            
            # If farm_geometry is a string, parse it
            if isinstance(farm_geometry, str):
                farm_geometry = json.loads(farm_geometry)
            
            farm_data = {
                "farm_id": row['plot_number'],
                "farmer_name": row['farmer_name'],
                "father_name": row['father_name'],
                "area": row['area'],
                "croptype": row['croptype'],
                "variety_group": row['variety_group'],
                "date_of_planting": row['date_of_planting'].isoformat() if row['date_of_planting'] else None,
                "phone_number": row['phone_number'],
                "health": row['health'],
                "farmer_code": row['farmer_code'],
                "geometry": farm_geometry
            }
            
            farms.append(farm_data)
        
        # Return only the village ID, name and farms
        return {
            "village_id": village_row['village_id'],
            "village_name": village_row['village_name'],
            "no_of_farms": village_row['village_size'],
            "farms": farms
        }
        
    except Exception as e:
        print(f"Error in get_farm_data_by_village: {e}")
        raise Exception(f"Database error: {str(e)}")

@app.get("/village/{village_id}/farms")
async def farm_boundaries_by_village_endpoint(village_id: int):
    # API endpoint to retrieve farm boundaries for a specific village.
    try:
        result = await get_farm_data_by_village(village_id)
        return JSONResponse(
            content={
                "status": "success",
                "data": result,
                "message": f"Farm boundaries for village ID {village_id} retrieved successfully!"
            }
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e)
            },
            status_code=404 if "not found" in str(e) or "No farms found" in str(e) else 500
        )
    
@app.get("/api/farm/{farm_id}/alerts")
async def get_farm_alerts(farm_id: int, ndvi_value: float, sowing_date: str, current_date: str = None):
    """
    API endpoint to retrieve health alerts for a specific farm.
    
    Args:
        farm_id: The ID of the farm
        ndvi_value: The NDVI value for the farm
        sowing_date: Sowing date in YYYY-MM-DD HH:MM:SS format
        current_date: Optional current date for assessment
    """
    try:
        # Generate alerts using the imported function
        alert_info = generate_sugarcane_alerts(sowing_date, ndvi_value, current_date)
        
        # Add farm_id to the response
        alert_info["farm_id"] = farm_id
        
        return JSONResponse(
            content={
                "status": "success",
                "data": alert_info,
                "message": f"Health alerts for farm ID {farm_id} generated successfully!"
            }
        )
    except ValueError as ve:
        # Handle validation errors (like date format issues)
        return JSONResponse(
            content={
                "status": "error",
                "message": str(ve)
            },
            status_code=400
        )
    except Exception as e:
        # Handle other errors
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e)
            },
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
