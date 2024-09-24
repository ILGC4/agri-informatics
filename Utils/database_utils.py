import psycopg2
from geojson import Polygon

def check_area_coverage(polygon, date, connection_params):
    date = '-'.join([date[:4], date[4:6], date[6:]])

    # Convert GeoJSON to WKT (Well-Known Text)
    wkt = f"POLYGON(({', '.join([' '.join(map(str, coord)) for coord in polygon['coordinates'][0]])}))"

    # Connect to the database
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()
    
    # SQL query to check for existence of the data and get the image path
    try:
        cur.execute("SELECT image_path FROM satellite_images WHERE ST_Intersects(geometry, ST_GeomFromText(%s, 4326)) AND acquisition_date = %s",(wkt, date))
        result = cur.fetchone()
    except Exception as e:
        print("Error:", e)
        result = [None]

    print("\nresult from query:", result)
    cur.close()
    conn.close()
    return result[0] if result else None

def add_new_image(tile_id, acquisition_date, coordinates, image_path, filter_df_name, connection_params):
    # Convert date string from 'YYYYMMDD' to a date object
    acquisition_date = '-'.join([acquisition_date[:4], acquisition_date[4:6], acquisition_date[6:]])

    # Convert GeoJSON to WKT (Well-Known Text)
    wkt_geometry = f"POLYGON((\
        {coordinates['top_left'].x} {coordinates['top_left'].y}, \
        {coordinates['top_right'].x} {coordinates['top_right'].y}, \
        {coordinates['bottom_right'].x} {coordinates['bottom_right'].y}, \
        {coordinates['bottom_left'].x} {coordinates['bottom_left'].y}, \
        {coordinates['top_left'].x} {coordinates['top_left'].y}\
    ))"

    image_path = str(image_path)
    print("Image Path:", image_path)
    print("Image Path Type", type(image_path))
    print("Polygon",wkt_geometry)

    # Connect to the database
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()
    
    # SQL command to insert new data
    cur.execute(
        "INSERT INTO satellite_images (tile_id, acquisition_date, geometry, image_path, filter_df_name) VALUES (%s, %s, ST_GeomFromText(%s, 4326), %s, %s)",
        (tile_id, acquisition_date, wkt_geometry, image_path, filter_df_name))
    
    # Commit changes
    conn.commit()
    
    # Close the database connection
    cur.close()
    conn.close()