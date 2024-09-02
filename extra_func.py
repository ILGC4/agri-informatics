# @solara.component
# def FileUploadMessage():
#     if show_message.get():
#         return solara.Text(message.get(), style={"color": "green", "fontWeight": "bold"})
#     return None

# def handle_upload(change):
#     if change.new:
#         uploaded_file=change.new[0]
#         content=uploaded_file['content']
#         geo_json=json.loads(content.decode('utf-8'))
#         print("File uploaded: ", geo_json)
#         if isinstance(geo_json, list) and all("geometry" in feature for feature in geo_json):
#             geo_json = {"type": "FeatureCollection", "features": geo_json}
#         else:
#             geo_json = geo_json
#         global map_instance
#         map_instance.zoom_to_geojson(geo_json)
#         message.set("File uploaded successfully!")
#         show_message.set(True)
#         asyncio.create_task(hide_message_after_delay(5))


# file_upload=widgets.FileUpload(
#     accept='.geojson',
#     multiple=False
# )
# file_upload.observe(handle_upload, names='value')

# @solara.component
# def FileDrop():
#     return solara.VBox([file_upload, FileUploadMessage()])

# def extract_coords(self, geometry):
    #     coords = []
    #     geom_type = geometry['type']
    #     if geom_type == 'Polygon':
    #         for ring in geometry['coordinates']:
    #             coords.extend(ring)
    #     return coords 

    # def get_bounds_from_geojson(self, geo_json):
    #     coords = []
    #     for feature in geo_json['features']:
    #         geom = feature['geometry']
    #         extracted_coords = self.extract_coords(geom)
    #         coords.extend(extracted_coords)
    #     if not coords:
    #         print("No coordinates extracted, cannot compute bounds.")
    #         return None
    #     min_lat = min(lat for _, lat in coords) 
    #     max_lat = max(lat for _, lat in coords)
    #     min_lon = min(lon for lon, _ in coords)
    #     max_lon = max(lon for lon, _ in coords)
    #     bounds = [(min_lat, min_lon), (max_lat, max_lon)]
    #     print("Computed bounds:", bounds)
    #     return bounds
    
    # def calculate_zoom_level(self, bounds):
    #     min_lat, min_lon = bounds[0]
    #     max_lat, max_lon = bounds[1]
    #     lat_range = max_lat - min_lat
    #     lon_range = max_lon - min_lon
    #     max_range = max(lat_range, lon_range)
    #     if max_range < 0.01:
    #         return 15  
    #     elif max_range < 0.1:
    #         return 13
    #     elif max_range < 1:
    #         return 10
    #     else:
    #         return 8
    
    # def zoom_to_geojson(self, geo_json):
    #     global map_instance
    #     bounds = self.get_bounds_from_geojson(geo_json)
    #     zoom_level = self.calculate_zoom_level(bounds)
    #     if bounds:
    #         try:
    #             min_lat, min_lon = bounds[0]
    #             max_lat, max_lon = bounds[1]
    #             center_lat = (min_lat + max_lat) / 2
    #             center_lon = (min_lon + max_lon) / 2
    #             center_coords=[center_lat, center_lon]
    #             center.set(center_coords) 
    #             zoom.set(zoom_level)
    #             print(f"Manually set center to: {center_coords}, zoom level to 20")
    #         except Exception as e:
    #             print(f"Failed manual zoom: {str(e)}")
    #     else:
    #         print("No valid bounds found to apply zoom.")

# ndvi stuff
# def get_recent_images(directory_path, time_limit_minutes=2):
#     # Path to the directory
#     path = Path(directory_path)
#     print('in get_recent_images')
#     # Current time in seconds since the epoch
#     current_time = time.time()
#     # Time limit in seconds
#     time_limit_seconds = time_limit_minutes * 60
    
#     # Get all image files in the directory with specific extensions
#     image_files = [f for f in path.glob('*') if f.suffix.lower() in ['.jpg', '.png']]
#     # Filter files modified within the last `time_limit_minutes` minutes
#     recent_files = [f for f in image_files if current_time - f.stat().st_mtime < time_limit_seconds]

#     # Sort files by modification time (newest first)
#     recent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
#     print(f"Found {len(recent_files)} recent files.")
    
#     return recent_files