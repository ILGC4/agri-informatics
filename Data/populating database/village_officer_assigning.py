import psycopg2
import json
from psycopg2 import sql

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="smurf",
    user="clumsysmurf",
    password="clumsysmurf",
    host="localhost",
    port=5432
)
conn.autocommit = True
cur = conn.cursor()

# Add centroid column to the village_data table if it doesn't exist yet
add_centroid_column_query = """
ALTER TABLE village_data 
ADD COLUMN IF NOT EXISTS centroid geometry(Point, 4326);
"""
cur.execute(add_centroid_column_query)

# Load the GeoJSON data
with open("/home/smurfs/agri_info2/Data/populating database/village_centroids.geojson", 'r') as f:
    geojson_data = json.load(f)

# Loop through features and update village_data table with centroids
for feature in geojson_data['features']:
    village_id = feature['properties']['fid']
    
    # Convert GeoJSON geometry to WKT format
    point_geometry = json.dumps(feature['geometry'])
    
    # Update the table with centroid for the matching village_id
    update_query = """
    UPDATE village_data 
    SET centroid = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
    WHERE village_id = %s;
    """
    cur.execute(update_query, (point_geometry, village_id))
    print(f"Updated centroid for village ID: {village_id}")

# Create a spatial index on the centroid column for better query performance
cur.execute("""
CREATE INDEX IF NOT EXISTS village_centroid_idx 
ON village_data USING GIST (centroid);
""")

# Check results
cur.execute("SELECT village_id, village_name, ST_AsText(centroid) FROM village_data LIMIT 5;")
results = cur.fetchall()
for row in results:
    if row[2]:
        print(f"Village ID: {row[0]}, Name: {row[1]}, Centroid: {row[2]}")
    else:
        print(f"Village ID: {row[0]}, Name: {row[1]}, Centroid: Not set")

# Close connection
cur.close()
conn.close()

print("Village centroids successfully added from GeoJSON file!")