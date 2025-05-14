import json
import psycopg2
import os
from ndvi_utils import ndvi_time_series_farm

# Database connection details
conn = psycopg2.connect(
    dbname="smurf",
    user="clumsysmurf",
    password="clumsysmurf",
    host="localhost",
    port=5432
)
cur = conn.cursor()

def process_villages():
    # Get all unique village_ids
    cur.execute("SELECT DISTINCT village_id FROM farm_data WHERE village_id IS NOT NULL ORDER BY village_id")
    village_ids = [row[0] for row in cur.fetchall()]
    print(f"Found {len(village_ids)} unique villages to process")
    
    # Directory where TIF files are stored
    tif_directory = "/Images/sentinel2"
    
    # Dictionary to store results for all villages
    all_results = {}
    # Process each village
    for village_id in village_ids:
        print(f"\nProcessing village_id: {village_id}")
        # Get farm geometries for this village
        cur.execute("""
            SELECT plot_number, geometry 
            FROM farm_data 
            WHERE village_id = %s AND geometry IS NOT NULL
        """, (village_id,))
        farms = cur.fetchall()
        print(f"Found {len(farms)} farms with geometries in village {village_id}")
        if not farms:
            print(f"No farms with geometries found for village {village_id}, skipping...")
            continue
        # Get the TIF file for this village
        tif_filename = f"village_{village_id}.tif"
        tif_path = os.path.join(tif_directory, tif_filename)
        if not os.path.exists(tif_path):
            print(f"Warning: TIF file {tif_path} not found for village {village_id}, skipping...")
            continue
        
        # Prepare list of geometries
        geoms = []
        plot_numbers = []
        for plot_number, geom_str in farms:
            try:
                # Parse geometry from JSONB
                geom = json.loads(geom_str)
                geoms.append(geom)
                plot_numbers.append(plot_number)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing geometry for plot {plot_number}: {e}")
        if not geoms:
            print(f"No valid geometries found for village {village_id}, skipping...")
            continue
        
        # Calculate NDVI for each farm
        try:
            print(f"Calculating NDVI values for {len(geoms)} farms...")
            ndvi_results = ndvi_time_series_farm(tif_path, geoms)
            # Map results back to plot numbers
            village_results = {}
            for i, plot_number in enumerate(plot_numbers):
                if json.dumps(geoms[i]) in ndvi_results:
                    village_results[plot_number] = ndvi_results[json.dumps(geoms[i])]
            # Add to overall results
            all_results[village_id] = village_results
        except Exception as e:
            print(f"  Error processing village {village_id}: {e}")

# Close connection
cur.close()
conn.close()