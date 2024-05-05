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
from ipyleaflet import GeoJSON, Map, WidgetControl
from ipywidgets import HTML, Layout
from shapely.geometry import shape, Point, mapping



global_geojson = [] #cause literally nothing else was working i wanna kms so bad
display_images = solara.reactive(False)
display_grid = solara.reactive(False) 
images_figures = solara.reactive([])

zoom = solara.reactive(5)
center = solara.reactive((22.0, 78.0))
message = solara.reactive("")
show_message = solara.reactive(False)
selected_polygon_id = solara.reactive(None)
selection_message = solara.reactive("") 
click_message = solara.reactive("")

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

async def display_message_for_seconds(msg, seconds):
    click_message.set(msg)  
    await asyncio.sleep(seconds)  
    click_message.set("")  

# @solara.component
# def FileUploadMessage():
#     if show_message.get():
#         return solara.Text(message.get(), style={"color": "green", "fontWeight": "bold"})
#     return None

@solara.component
def SelectionConfirmationMessage():
    if selected_polygon_id.get() is not None:
        return solara.Text(selection_message.get(), style={"color": "green", "fontWeight": "bold"})
    return None

@solara.component
def PolygonClickMessage():
    if click_message.get():
        return solara.Text(click_message.get(), style={"color": "red", "fontWeight": "bold"})
    return None  

def delete_geojson_on_startup(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted {file_path} successfully.")
    except Exception as e:
        print(f"Failed to delete {file_path}: {e}")

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

class Map(leafmap.Map):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add what you want below
        self.add_basemap("OpenTopoMap")
        change_basemap(self)
        self.center = center.value
        self.zoom = zoom.value
        self.geojson_layers = {}
        self.setup_draw_control()
        self.on_interaction(self.general_interaction_handler)

    def general_interaction_handler(self, **kwargs):
        if 'type' in kwargs and kwargs['type'] == 'click':
            self.handle_map_click(**kwargs)

    def handle_map_click(self, **kwargs):
        global global_geojson
        coordinates = kwargs.get('coordinates')
        if coordinates:
            # Create a point with longitude and latitude (ensure the correct order based on your map's configuration)
            clicked_point = Point(coordinates[1], coordinates[0])
            print(f"Clicked point: {clicked_point}")  # Debug output
            found = False
            for feature in global_geojson:
                polygon=shape(feature['geometry'])
                if polygon.contains(clicked_point):
                    asyncio.create_task(display_message_for_seconds("Selected a polygon, please wait for results", 5))
                    found=True
                    break
            if not found:
                asyncio.create_task(display_message_for_seconds("Please click within a polygon", 5)) 


    
    def setup_draw_control(self):
        existing_draw_control=next((control for control in self.controls if isinstance(control, DrawControl)), None)
        if existing_draw_control:
            self.remove_control(existing_draw_control)
            self.draw_control=DrawControl()
            self.add_control(self.draw_control)
            self.draw_control.on_draw(self.handle_draw)  

    def draw_geojson(self, geo_json):
        # Clear existing GeoJSON layers
        for layer in self.geojson_layers.values():
            self.remove_layer(layer)
        self.geojson_layers = {}  
        # Create and add new GeoJSON layers
        for feature in geo_json['features']:
            feature_id = feature.get('id', len(self.geojson_layers) + 1)
            geo_json_layer = GeoJSON(data=feature)
            geo_json_layer.on_click(lambda feature, **kwargs: self.handle_polygon_click(feature, **kwargs))
            self.add_layer(geo_json_layer) 
            self.geojson_layers[feature_id] = geo_json_layer



    def handle_draw(self, target, action, geo_json):
        # Store the drawn GeoJSON data
        global global_geojson
        if action == "created":
            # Assign a unique identifier to the geo_json
            geo_json['id'] = len(global_geojson) + 1
            global_geojson.append(geo_json) 
            print("Shape drawn and stored: ", geo_json)
        elif action == "deleted": 
            # Remove the feature with the matching ID
            delete = geo_json['geometry']['coordinates']
            global_geojson=[x for x in global_geojson if x['geometry']['coordinates'] != delete]
            print("Shape deleted: ", geo_json)

    def extract_coords(self, geometry):
        coords = []
        geom_type = geometry['type']
        if geom_type == 'Polygon':
            for ring in geometry['coordinates']:
                coords.extend(ring)
        return coords 

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
    
    def calculate_zoom_level(self, bounds):
        min_lat, min_lon = bounds[0]
        max_lat, max_lon = bounds[1]
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        max_range = max(lat_range, lon_range)
        if max_range < 0.01:
            return 15  
        elif max_range < 0.1:
            return 13
        elif max_range < 1:
            return 10
        else:
            return 8
    
    def zoom_to_geojson(self, geo_json):
        global map_instance
        bounds = self.get_bounds_from_geojson(geo_json)
        zoom_level = self.calculate_zoom_level(bounds)
        if bounds:
            try:
                min_lat, min_lon = bounds[0]
                max_lat, max_lon = bounds[1]
                center_lat = (min_lat + max_lat) / 2
                center_lon = (min_lon + max_lon) / 2
                center_coords=[center_lat, center_lon]
                center.set(center_coords) 
                zoom.set(zoom_level)
                print(f"Manually set center to: {center_coords}, zoom level to 20")
            except Exception as e:
                print(f"Failed manual zoom: {str(e)}")
        else:
            print("No valid bounds found to apply zoom.")

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

def test_get_recent_images(directory_path):
    path = Path(directory_path)
    all_files = list(path.glob('*'))  # List all files without filtering
    print(f"All files in directory: {all_files}")
    return all_files  # Ensure to return the list of files
 
 
def get_and_display_recent_images():
        directory_path = './plots/'  # Specify the directory path
        print('Fetching recent images...')
        recent_images = test_get_recent_images(directory_path)
        # plot images using plt
        figs=[]
        if recent_images:
            for img_path in recent_images:
                try:
                    img = plt.imread(img_path)  
                    fig, ax = plt.subplots(figsize=(10, 8), dpi=100) 
                    ax.imshow(img, interpolation='bicubic')
                    ax.axis('off')  # Hide the axes
                    figs.append(fig)
                    print(f"Loaded image {img_path}")
                except Exception as e:
                    print(f"Failed to process image {img_path}: {str(e)}")
            if figs:
                images_figures.set(figs)
                display_images.set(True)
                display_grid.set(True)
                print("Images are ready to be displayed.")
            else:
                print("No images were loaded.")
        else:
            print("No files in directory.")

def remove_images():
    display_images.set(False)
    display_grid.set(False) 
    images_figures.set([])
    print("Images removed.")



@solara.component
def DisplayImages():
    if display_images.get():
        print("Displaying images...")
        return solara.VBox([solara.FigureMatplotlib(fig) for fig in images_figures.get()])
    print("No images to display")
    return None

@solara.component 
def TextCard(color, text, title=None):
    if display_grid.get():
        style = {
            "backgroundColor": color,
            "color": "white",
            "padding": "10px",
            "height": "100%",
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
            "fontSize": "16px",
            "borderRadius": "5px",
        }
        return solara.Div([
            # solara.Text(title, style={"fontWeight": "bold"}),
            solara.Text(text, style={"marginTop": "10px"}),
        ], style=style)

@solara.component
def DraggableGrid():
    if display_grid.get():
        grid_layout_initial = [
            {"h": 10, "i": "0", "moved": False, "w": 10, "x": 0, "y": 0},
            {"h": 3, "i": "1", "moved": False, "w": 3, "x": 3, "y": 0},
            {"h": 3, "i": "2", "moved": False, "w": 3, "x": 6, "y": 0},
            {"h": 3, "i": "3", "moved": False, "w": 3, "x": 0, "y": 3},
            {"h": 3, "i": "4", "moved": False, "w": 3, "x": 3, "y": 3},
            {"h": 3, "i": "5", "moved": False, "w": 3, "x": 6, "y": 3},
        ]
        colors = "blue blue blue blue blue blue".split()
        dummy_texts = [
            "Lorem ipsum dolor sit.",
            "Consectetur adipiscing.",
            "Sed do eiusmod tempor.",
            "Ut labore et dolore.",
            "Ut enim ad minim veniam.",
            "Quis nostrud exercitation."
        ]

        grid_layout, set_grid_layout = solara.use_state(grid_layout_initial)

        items = [TextCard(title=f"Item {i}", color=colors[i], text=dummy_texts[i]) for i in range(len(grid_layout))]
        
        return solara.GridDraggable(
            items=items,
            grid_layout=grid_layout,
            resizable=True,
            draggable=True,
            on_grid_layout=set_grid_layout
        )

@solara.component
def Page():
    global map_instance
    map_instance = Map()

    with solara.AppBarTitle():
        solara.Text("Sugarmill Farm Management Tool", style={"fontSize": "24px", "fontWeight": "bold", "textAlign": "center", "alignItems": "center"})
         
    with solara.Column(style={"min-width": "500px", "display": "flex", "justifyContent": "center", "alignItems": "center", "flexDirection": "column"}):
        solara.Title("Sugarmill Farm Management Tool")
        PolygonClickMessage()
        FileDrop() # type: ignore
        SelectionConfirmationMessage()  
        # Rest of your existing UI components

    return solara.VBox([
        map_instance.element(
            zoom=zoom.value,
            on_zoom=zoom.set,
            center=center.value,
            on_center=center.set,
            scroll_wheel_zoom=True,
            toolbar_ctrl=False,
            data_ctrl=False,
        ),
        solara.Text(f"Zoom: {zoom.value}"),
        solara.Text(f"Center: {center.value}")
    ])


@solara.component
def Page():
    global map_instance
    map_instance = Map()

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

       
    with solara.Column(style={"min-width": "500px", "display": "flex", "justifyContent": "center", "alignItems": "center", "flexDirection": "column"}):
        solara.Title("Sugarmill Farm Management Tool")
        PolygonClickMessage()
        # FileDrop()
        SelectionConfirmationMessage()  
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
                style={"width": "200px", "marginTop": "5px", "fontSize": "16px", "backgroundColor": "#007BFF", "color": "white", "border": "none", "borderRadius": "5px", "padding": "10px 0"}
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
            solara.Button(
                label="Remove Plots",
                on_click=remove_images,
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
    if display_images.get():
        DisplayImages()
    if display_grid.get():
        DraggableGrid()
    solara.Text(f"Zoom: {zoom.value}")
    solara.Text(f"Center: {center.value}")  