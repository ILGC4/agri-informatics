import json
import psycopg2
from psycopg2 import sql
import datetime
import random
from shapely.geometry import shape, MultiPolygon
from shapely.wkt import dumps as wkt_dumps

# --- Database Connection Details (Update these) ---
DB_NAME = "smurf"
DB_USER = "clumsysmurf"
DB_PASSWORD = "clumsysmurf"
DB_HOST = "localhost"
DB_PORT = "5432"

# --- File Paths ---
VILLAGES_GEOJSON_PATH = r"../new_data/villages_with_farms.geojson"
FARMS_GEOJSON_PATH = r"../new_data/farms.geojson" # Assuming this is the correct name

def convert_days_to_date(days_since_1900):
    """
    Converts a number of days since Jan 1, 1900 to a YYYY-MM-DD date string.
    Assumes day 0 is Jan 1, 1900.
    """
    if days_since_1900 is None:
        return None
    try:
        # Ensure it's an integer
        days_since_1900 = int(days_since_1900)
        base_date = datetime.datetime(1900, 1, 1)
        target_date = base_date + datetime.timedelta(days=days_since_1900)
        return target_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError) as e:
        print(f"Warning: Could not convert days {days_since_1900} to date: {e}")
        return None

def generate_random_phone_number():
    """Generates a random 10-digit phone number as a string."""
    return ''.join([str(random.randint(0, 9)) for _ in range(10)])

def main():
    conn = None
    cur = None
    village_geometries = [] # To store {'id': village_id, 'shape': shapely_geom, 'name': village_name}

    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # --- Create tables if they don't exist ---
        create_village_data_table_sql = """
        CREATE TABLE IF NOT EXISTS public.village_data (
            village_id SERIAL PRIMARY KEY,
            village_name TEXT NOT NULL,
            field_officer_id INTEGER NOT NULL,
            village_size INTEGER,
            geometry GEOMETRY(MultiPolygon, 4326),
            centroid GEOMETRY(Point, 4326)
        );
        """
        cur.execute(create_village_data_table_sql)
        print("Ensured public.village_data table exists.")

        create_farm_data_table_sql = """
        CREATE TABLE IF NOT EXISTS public.farm_data (
            plot_number BIGINT PRIMARY KEY,
            farmer_name TEXT,
            father_name TEXT,
            area DOUBLE PRECISION,
            croptype TEXT,
            variety_group TEXT,
            date_of_planting DATE,
            village_id INTEGER,
            geometry JSONB,
            phone_number TEXT,
            health INTEGER,
            village_code_og INTEGER,
            village_name TEXT, -- Note: This duplicates village_data.village_name, consider if needed
            farmer_code BIGINT,
            croptype_code INTEGER,
            variety_code INTEGER,
            ndvi_value DOUBLE PRECISION,
            harvest_readiness INTEGER DEFAULT 1,
            lai_value DOUBLE PRECISION,
            waterlogging INTEGER DEFAULT 1,
            ndwi_value DOUBLE PRECISION,
            FOREIGN KEY (village_id) REFERENCES public.village_data(village_id)
        );
        """
        cur.execute(create_farm_data_table_sql)
        print("Ensured public.farm_data table exists.")
        conn.commit()

        # --- Modifications: Tables will not be cleared. Data will be appended. ---
        print("Processing and Appending villages...")
        with open(VILLAGES_GEOJSON_PATH, 'r') as f:
            villages_geojson = json.load(f)

        for feature in villages_geojson.get('features', []):
            props = feature.get('properties', {})
            geom_geojson = feature.get('geometry')

            if not geom_geojson:
                print(f"Skipping village feature due to missing geometry: {props.get('name')}")
                continue

            village_name = props.get('name') or props.get('lgd_villagename') or props.get('censusname')
            if not village_name:
                print(f"Skipping village feature due to missing name. Properties: {props}")
                continue
                
            field_officer_id = random.randint(1, 25)
            
            no_hh = props.get('no_hh')
            village_size = int(no_hh) if no_hh is not None else None

            try:
                shapely_geom = shape(geom_geojson)
                if shapely_geom.geom_type == 'Polygon':
                    shapely_geom = MultiPolygon([shapely_geom])
                elif shapely_geom.geom_type != 'MultiPolygon':
                    print(f"Skipping village {village_name} due to incompatible geometry type: {shapely_geom.geom_type}")
                    continue
                
                geom_wkt = wkt_dumps(shapely_geom)
                centroid_wkt = wkt_dumps(shapely_geom.centroid)

                insert_village_query = sql.SQL("""
                    INSERT INTO public.village_data 
                    (village_name, field_officer_id, village_size, geometry, centroid)
                    VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326), ST_GeomFromText(%s, 4326))
                    RETURNING village_id;
                """)
                cur.execute(insert_village_query, (village_name, field_officer_id, village_size, geom_wkt, centroid_wkt))
                returned_village_id = cur.fetchone()[0]
                village_geometries.append({'id': returned_village_id, 'shape': shapely_geom, 'name': village_name})
            except Exception as e:
                print(f"Error processing/inserting village {village_name}: {e}")
                conn.rollback() # Rollback this specific insertion
                cur = conn.cursor() # Reopen cursor

        print(f"Processed and Appended {len(village_geometries)} villages.")
        conn.commit()

        # Appending to farm_data table
        print("\nProcessing and Appending farms...")

        with open(FARMS_GEOJSON_PATH, 'r') as f:
            farms_geojson = json.load(f)

        farm_insert_count = 0
        for feature in farms_geojson.get('features', []):
            props = feature.get('properties', {})
            geom_geojson = feature.get('geometry')

            if not geom_geojson:
                print(f"Skipping farm feature due to missing geometry: {props.get('Plot Number')}")
                continue

            plot_number_str = props.get('Plot Number')
            if plot_number_str is None: # plot_number is primary key, cannot be null if table was empty
                print(f"Skipping farm feature due to missing Plot Number. Properties: {props}")
                continue
            try:
                plot_number = int(plot_number_str) # farm_data.plot_number is bigint
            except ValueError:
                print(f"Skipping farm feature due to invalid Plot Number: {plot_number_str}. Properties: {props}")
                continue

            farmer_name = props.get('Farmer Name')
            father_name = props.get("Father\\'s Name") # Escaped apostrophe
            area_str = props.get('Area (in Ha.)')
            area = None
            if area_str:
                try:
                    area = float(area_str)
                except ValueError:
                    print(f"Warning: Could not convert area '{area_str}' to float for plot {plot_number}. Setting to NULL.")

            croptype = props.get('Croptype Description')
            variety_group = props.get('Variety Group')
            dop_days = props.get('Date of Planting')
            date_of_planting_str = convert_days_to_date(dop_days)
            
            phone_number = generate_random_phone_number() # Generate random phone number

            farmer_code_str = props.get('Farmer Code')
            farmer_code = None
            if farmer_code_str:
                try:
                    farmer_code = int(farmer_code_str)
                except ValueError:
                    print(f"Warning: Could not convert Farmer Code '{farmer_code_str}' to int for plot {plot_number}. Setting to NULL.")
            
            croptype_code_str = props.get('Croptype Code')
            croptype_code = None
            if croptype_code_str:
                try:
                    croptype_code = int(croptype_code_str)
                except ValueError:
                    print(f"Warning: Could not convert Croptype Code '{croptype_code_str}' to int for plot {plot_number}. Setting to NULL.")

            variety_code_str = props.get('Variety Code')
            variety_code = None
            if variety_code_str:
                try:
                    variety_code = int(variety_code_str)
                except ValueError:
                    print(f"Warning: Could not convert Variety Code '{variety_code_str}' to int for plot {plot_number}. Setting to NULL.")
            
            # Geometry for farm_data is JSONB
            farm_geometry_jsonb = json.dumps(geom_geojson)

            assigned_village_id = None
            try:
                farm_shapely_geom = shape(geom_geojson)
                overlapping_villages = []
                for v_info in village_geometries:
                    if farm_shapely_geom.intersects(v_info['shape']):
                        overlapping_villages.append(v_info['id'])
                
                if overlapping_villages:
                    assigned_village_id = random.choice(overlapping_villages)
                else:
                    print(f"Warning: Farm plot {plot_number} does not overlap with any village. village_id will be NULL.")

                insert_farm_query = sql.SQL("""
                    INSERT INTO public.farm_data
                    (plot_number, farmer_name, father_name, area, croptype, variety_group,
                     date_of_planting, village_id, geometry, phone_number,
                     farmer_code, croptype_code, variety_code)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                    ON CONFLICT (plot_number) DO NOTHING; 
                """) # Added ON CONFLICT DO NOTHING in case plot_number already exists
                cur.execute(insert_farm_query, (
                    plot_number, farmer_name, father_name, area, croptype, variety_group,
                    date_of_planting_str, assigned_village_id, farm_geometry_jsonb, phone_number,
                    farmer_code, croptype_code, variety_code
                ))
                farm_insert_count += 1
            except Exception as e:
                print(f"Error processing/inserting farm {plot_number}: {e}")
                conn.rollback() # Rollback this specific insertion
                cur = conn.cursor() # Reopen cursor

        print(f"Inserted {farm_insert_count} farms.")
        conn.commit()
        print("\nData population completed successfully.")

    except (Exception, psycopg2.Error) as error:
        print(f"Error connecting to or working with PostgreSQL: {error}")
        if conn:
            conn.rollback()
    finally:
        # Close the database connection
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("PostgreSQL connection is closed.")

if __name__ == "__main__":
    main()