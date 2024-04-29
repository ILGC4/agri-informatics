import psycopg2
from geojson import Polygon

def check_area_coverage(geojson_polygon, date, connection_params) :
    # Convert GeoJSON to WKT (Well-Known Text)
    geometry_wkt = str(Polygon(geojson_polygon['coordinates']))
    
    # Connect to the database
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()
    
    # SQL query to check for existence of the data
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM satellite_images WHERE geometry && ST_GeomFromText(%s, 4326) AND acquisition_date = %s)",
        (geometry_wkt, date)
    )
    
    # Fetch the result
    exists = cur.fetchone()[0]
    
    # Close the database connection
    cur.close()
    conn.close()
    
    return exists

def add_new_image(tile_id, acquisition_date, geojson_polygon, image_path, connection_params):
    # Convert GeoJSON to WKT (Well-Known Text)
    geometry_wkt = str(Polygon(geojson_polygon['coordinates']))
    
    # Connect to the database
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()
    
    # SQL command to insert new data
    cur.execute(
        "INSERT INTO satellite_images (tile_id, acquisition_date, geometry, image_path) VALUES (%s, %s, ST_GeomFromText(%s, 4326), %s)",
        (tile_id, acquisition_date, geometry_wkt, image_path)
    )
    
    # Commit changes
    conn.commit()
    
    # Close the database connection
    cur.close()
    conn.close()
