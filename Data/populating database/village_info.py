import json
import psycopg2

# Database connection parameters (update if needed)
DB_PARAMS = {
    "dbname": "smurf",
    "user": "clumsysmurf",
    "password": "clumsysmurf",
    "host": "localhost",
    "port": "5432",
}

# Load GeoJSON file
with open("/home/smurfs/agri_info2/Data/loni_boundaries.geojson", "r", encoding="utf-8") as file:
    geojson_data = json.load(file)

# Connect to PostgreSQL
conn = psycopg2.connect(**DB_PARAMS)
cur = conn.cursor()

# Iterate over GeoJSON features
for feature in geojson_data["features"]:
    properties = feature["properties"]
    
    # Extract relevant data
    plot_number = properties.get("Plot Number")
    village_code_og = properties.get("Village Code")
    village_name = properties.get("Village Name").strip() if properties.get("Village Name") else None
    farmer_code = properties.get("Farmer Code")
    croptype_code = properties.get("Croptype Code")
    variety_code = properties.get("Variety Code")
    
    # Update the database
    update_query = """
        UPDATE farm_data
        SET village_code_og = %s,
            village_name = %s,
            farmer_code = %s,
            croptype_code = %s,
            variety_code = %s
        WHERE plot_number = %s;
    """
    
    cur.execute(update_query, (village_code_og, village_name, farmer_code, croptype_code, variety_code, plot_number))

# Commit changes and close connection
conn.commit()
cur.close()
conn.close()

print("Database updated successfully!")
