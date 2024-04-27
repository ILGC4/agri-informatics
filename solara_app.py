import leafmap
import solara
from ipyleaflet import Map, DrawControl
import json
from leafmap.toolbar import change_basemap
import os
import ipywidgets as widgets
import tempfile
import asyncio
from pathlib import Path
import time
from api_main import main
from solara.lab import task
import io
from PIL import Image as PILImage
import matplotlib.pyplot as plt

global_geojson = [] #cause literally nothing else was working i wanna kms so bad

zoom = solara.reactive(5)
center = solara.reactive((22.0, 78.0))
message = solara.reactive("")
show_message = solara.reactive(False)

locations = {
        "Default": [22.0, 78.0],
        "Chennai": [13.0827, 80.2707],
        "Kolkata": [22.5726, 88.3639],
        "Hyderabad": [17.3850, 78.4867],
        "Pune": [18.5204, 73.8567],
        "New Delhi": [28.6139, 77.2090],
        "Mumbai": [19.0760, 72.8777],
        "Bengaluru": [12.9716, 77.5946],
        "Lakhimpur": [27.9506, 80.7821]
}
selected_location = solara.reactive("Select a location")

async def hide_message_after_delay(delay):
    await asyncio.sleep(delay)
    show_message.set(False)
    message.set("")

@solara.component
def FileUploadMessage():
    if show_message.get():
        return solara.Text(message.get(), style={"color": "green", "fontWeight": "bold"})
    return None

def delete_geojson_on_startup(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted {file_path} successfully.")
    except Exception as e:
        print(f"Failed to delete {file_path}: {e}")

def handle_upload(change):
    if change.new:
        uploaded_file=change.new[0]
        content=uploaded_file['content']
        geo_json=json.loads(content.decode('utf-8'))
        print("File uploaded: ", geo_json)
        map_instance.draw_geojson(geo_json)
        message.set("File uploaded successfully!")
        show_message.set(True)
        asyncio.create_task(hide_message_after_delay(5))


file_upload=widgets.FileUpload(
    accept='.geojson',
    multiple=False
)
file_upload.observe(handle_upload, names='value')

@solara.component
def FileDrop():
    return solara.VBox([file_upload, FileUploadMessage()])

class Map(leafmap.Map):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add what you want below
        self.add_basemap("OpenTopoMap")
        change_basemap(self)
        self.center = center.value
        self.zoom = zoom.value
        # Initialize the draw control
        existing_draw_control = next((control for control in self.controls if isinstance(control, DrawControl)), None)
        if existing_draw_control is not None:
            self.remove_control(existing_draw_control)
        # Add the draw control to the map
        self.draw_control = DrawControl()
        self.add_control(self.draw_control)

        # Set up event handling for drawing on the map
        self.draw_control.on_draw(self.handle_draw)

    def zoom_to_bounds(self, bounds):
        try:
            print("Attempting to zoom to bounds:", bounds)
            super().zoom_to_bounds(bounds) 
        except Exception as e:
            print(f"Error during zoom: {str(e)}")

    def extract_coords(self, geometry):
        coords = []
        geom_type = geometry['type']
        if geom_type == 'Polygon':
            for ring in geometry['coordinates']:
                coords.extend(ring)
        return coords
    
    def zoom_to_geojson(self, geo_json):
        bounds = self.get_bounds_from_geojson(geo_json)
        if bounds:
            try:
                min_lat, min_lon = bounds[0]
                max_lat, max_lon = bounds[1]
                center_lat = (min_lat + max_lat) / 2
                center_lon = (min_lon + max_lon) / 2
                center_coords=[center_lat, center_lon]
                center.set(center_coords)
                zoom.set(20)
                map_instance.center=center_coords
                map_instance.zoom=10
                print(f"Manually set center to: {center_coords}, zoom level to 20")
            except Exception as e:
                print(f"Failed manual zoom: {str(e)}")
        else:
            print("No valid bounds found to apply zoom.")

    def get_bounds_from_geojson(self, geo_json):
        coords = []
        for feature in geo_json['features']:
            geom = feature['geometry']
            extracted_coords = self.extract_coords(geom)
            coords.extend(extracted_coords)
        if not coords:
            print("No coordinates extracted, cannot compute bounds.")
            return None
        min_lat = min(lat for _, lat in coords) 
        max_lat = max(lat for _, lat in coords)
        min_lon = min(lon for lon, _ in coords)
        max_lon = max(lon for lon, _ in coords)
        bounds = [(min_lat, min_lon), (max_lat, max_lon)]
        print("Computed bounds:", bounds)
        return bounds


    
    def draw_geojson(self, geo_json_list):
        # print("Type of geo_json:", type(geo_json_list))
        # print("Content of geo_json:", geo_json_list)
        if isinstance(geo_json_list, list):
        # Construct a proper GeoJSON FeatureCollection
            geo_json = {
                "type": "FeatureCollection",
                "features": geo_json_list
            }
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson", mode="w") as tmp:
                    json.dump(geo_json, tmp)
                    tmp.flush()
                    tmp_path=tmp.name
                self.add_geojson(tmp_path, layer_name="Uploaded Layer")
                os.unlink(tmp_path)
                print("GeoJSON added to map.")
                self.zoom_to_geojson(geo_json)
            except Exception as e:
                print(f"Failed to load GeoJSON: {e}")
        print("Current layers on map:", [layer.name for layer in self.layers])




    def handle_draw(self, target, action, geo_json):
        # Store the drawn GeoJSON data
        global global_geojson
        if action == "created":
            # Assign a unique identifier to the geo_json
            global_geojson.append(geo_json)
            print("Shape drawn and stored: ", geo_json)
        elif action == "deleted": 
            # Remove the feature with the matching ID
            delete = geo_json['geometry']['coordinates']
            global_geojson=[x for x in global_geojson if x['geometry']['coordinates'] != delete]
            print("Shape deleted: ", geo_json)   

    def export(self, file_path):
        global global_geojson
        print("this is the data:", global_geojson) 
        if global_geojson is not None:
            with open(file_path, "w") as f:
                json.dump(global_geojson, f)
            print("GeoJSON data exported to: ", file_path)
            fetch_api()
        else:
            print("No data to export")

@task
async def fetch_api():
    await main()

# ndvi stuff
def get_recent_images(directory_path, time_limit_minutes=2):
    # Path to the directory
    path = Path(directory_path)
    print('in get_recent_images')
    # Current time in seconds since the epoch
    current_time = time.time()
    # Time limit in seconds
    time_limit_seconds = time_limit_minutes * 60
    
    # Get all image files in the directory with specific extensions
    image_files = [f for f in path.glob('*') if f.suffix.lower() in ['.jpg', '.png']]
    # Filter files modified within the last `time_limit_minutes` minutes
    recent_files = [f for f in image_files if current_time - f.stat().st_mtime < time_limit_seconds]

    # Sort files by modification time (newest first)
    recent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return recent_files

@solara.component
def Page():
    global map_instance
    map_instance = Map()
    images_data = solara.reactive([])

    with solara.AppBarTitle():
        solara.Text("Sugarmill Farm Management Tool", style={"fontSize": "24px", "fontWeight": "bold", "textAlign": "center", "alignItems": "center"})
    
        

    def on_location_change(value):
        # Update the map center when the location changes
        print(f"Selected location: {value}")  # Debugging statement
        new_center = locations.get(value)
        if new_center:
            print(f"Setting new center: {new_center}")
            center.set(new_center)
            if value=="Default":
                new_zoom=5
            else:
                new_zoom=13
            zoom.set(new_zoom)
            map_instance.center=new_center
            map_instance.zoom=new_zoom
            print(f"Center and zoom updated to: {new_center}, {new_zoom}")
        else:
            print("Invalid location selected")

    def reset_map():
        global global_geojson
        global_geojson = []
        print("Resetting map to default location and zoom")
        default_center = locations["Default"]
        center.set(default_center)
        zoom.set(5)
        map_instance.center = default_center
        map_instance.zoom = 5
        selected_location.set("Select a location")  # Optionally reset the dropdown
        delete_geojson_on_startup(r'./Data/output.geojson')
        print(f"Map reset to center: {default_center} and zoom: 5")


    def export_geojson():
        file_path=r'./Data/output.geojson'
        map_instance.export(file_path)

    def get_and_display_recent_images():
        directory_path = './plots/'  # Specify the directory path
        print('in get_and_display_recent_images')
        recent_images = get_recent_images(directory_path)
        # plot images using plt
        for img_path in recent_images:
            try:
                with PILImage.open(img_path) as img:
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    buf.seek(0)
                    image_bytes = buf.read()
                    # Create an image widget for each image
                    image_widget = solara.Image(value=image_bytes, format='png', width='100%')
                    images_data.append(image_widget)
            except Exception as e:
                print(f"Failed to process image {img_path}: {str(e)}")
                continue
       
    with solara.Column(style={"min-width": "500px", "display": "flex", "justifyContent": "center", "alignItems": "center", "flexDirection": "column"}):
        solara.Title("Sugarmill Farm Management Tool")
        FileDrop()
        # Select component for location selection
        solara.Select(
            label="Choose a location:",
            value=selected_location,
            values=list(locations.keys()),
            on_value=on_location_change,
            dense=True,
            style={"width": "100%", "maxWidth": "400px", "fontSize": "16px", "marginTop":"5px", "textAlign": "center", "display":"block",
                   "zIndex": "1000","maxHeight": "200px"}
        )
        with solara.Row(justify="center", style={"marginTop": "10px"}):
            solara.Button(
                label="Reset Map",
                on_click=reset_map,
                style={"width": "200px", "marginTop": "2px", "fontSize": "16px", "backgroundColor": "#007BFF", "color": "white", "border": "none", "borderRadius": "5px", "padding": "10px 0"}
            )
            solara.Button(
                label="Export GeoJSON",
                on_click=export_geojson,
                style={"width": "200px", "marginTop": "5px", "fontSize": "16px", "backgroundColor": "#28a745", "color": "white", "border": "none", "borderRadius": "5px", "padding": "10px 0"}
            )
            solara.Button(
                label="Display Plots",
                on_click=get_and_display_recent_images,
                style={"width": "200px", "marginTop": "5px", "fontSize": "16px", "backgroundColor": "#28a745", "color": "white", "border": "none", "borderRadius": "5px", "padding": "10px 0"}
            )
    map_instance.element(
        zoom=zoom.value,
        on_zoom=zoom.set,
        center=center.value,
        on_center=center.set,
        scroll_wheel_zoom=True,
        toolbar_ctrl=False,
        data_ctrl=False,
    )
    solara.Text(f"Zoom: {zoom.value}")
    solara.Text(f"Center: {center.value}")