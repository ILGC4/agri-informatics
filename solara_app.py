import leafmap
import solara
from ipyleaflet import Map, DrawControl
import json
from leafmap.toolbar import change_basemap
import os
import asyncio
from pathlib import Path
import csv
from api_main import main
from solara.lab import task
import matplotlib.pyplot as plt
from ipyleaflet import GeoJSON, Map, WidgetControl
from ipywidgets import HTML, Layout
from shapely.geometry import shape, Point, mapping
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
import glob
import datetime
import solara.lab
import state




global_geojson = [] #cause literally nothing else was working i wanna kms so bad
polygon_coords = None
display_info = solara.reactive(False) 
show_info=solara.reactive(False)
images_figures = solara.reactive([])


zoom = solara.reactive(5)
center = solara.reactive((22.0, 78.0))
message = solara.reactive("")
show_message = solara.reactive(False)
selected_polygon_id = solara.reactive(None)
selection_message = solara.reactive("") 
click_message = solara.reactive("")
selected_date = solara.reactive("Select a date")
info_collected = solara.reactive(False)

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

async def hide_message_after_delay(delay): #top message after clicking on shape
    await asyncio.sleep(delay)
    show_message.set(False)
    message.set("")

async def display_message_for_seconds(msg, seconds): #determines how long to display message for
    click_message.set(msg)  
    await asyncio.sleep(seconds)  
    click_message.set("")  
    
@solara.component
def DateDropdown(): #dropdown list for dates from database (should only be displayed after collect info is clicked)
    input_range = solara.use_reactive(tuple([datetime.date.today(), datetime.date.today() + datetime.timedelta(days=1)]))
    interval = solara.use_reactive("1")  # Initialize interval as a string to capture user input

    def set_interval(value):
        # Update interval when the user inputs a new value
        interval.set(value)
        state.interval = interval.value

    with solara.Column(style="width: 400px; padding-top: 150px"):
        # Text input for the interval
        solara.InputText(
            label="Interval (in days)",
            value=interval,
            on_value=set_interval,
            # placeholder="Enter the interval",
        )
        
        # InputDateRange to select start and end date from the calendar
        with solara.lab.InputDateRange(
            input_range,
            sort=True
        ):
            pass
        if input_range.value and len(input_range.value) == 2:
            state.date_range = {'gte': input_range.value[0].isoformat(), 'lte': input_range.value[1].isoformat()}

@solara.component
def SelectionConfirmationMessage(): #display message at top of screen once shape is clicked and selection of shape confirmed
    if selected_polygon_id is not None:
        return solara.Text(selection_message.get(), style={"color": "green", "fontWeight": "bold"})
    return None

@solara.component
def PolygonClickMessage(): #clicked on polygon message
    if click_message.get():
        return solara.Text(click_message.get(), style={"color": "red", "fontWeight": "bold"})
    return None  

def delete_geojson_on_startup(file_path): #remove geojson file on startup
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted {file_path} successfully.")
    except Exception as e:
        print(f"Failed to delete {file_path}: {e}")

def get_data_from_csv(directory_path): #get info from database and display in grid (dummy for now)
    fields = ['cloud_cover', 'pixel_resolution', 'clear_percent', 'satellite_id', 'gsd', 'heavy_haze_percent']
    data_by_date = {}
    dates_list = []
    csv_files = glob.glob(f"{directory_path}/*.csv")
    if not os.path.exists(directory_path):
        return None, None
    for directory_path in csv_files:
        with open(directory_path, newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                date_str = row['date']
                if date_str not in data_by_date:
                    data_by_date[date_str] = []
                    dates_list.append(date_str)
                data_by_date[date_str].append({field: row[field] for field in fields})
    dates_list = sorted(list(set(dates_list)))  
    return data_by_date, dates_list


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

    def handle_map_click(self, **kwargs): #clicking point on map and checking whether it is in a polygon or not
        global global_geojson, selected_polygon_id
        global polygon_coords
        coordinates = kwargs.get('coordinates')
        if coordinates:
            clicked_point = Point(coordinates[1], coordinates[0])
            print(f"Clicked point: {clicked_point}")  # Debug output
            found = False
            for feature in global_geojson:
                polygon=shape(feature['geometry'])
                if polygon.contains(clicked_point):
                    asyncio.create_task(display_message_for_seconds("Selected a polygon, please wait for results", 5))
                    selected_polygon_id=feature['id']
                    print(selected_polygon_id) 
                    polygon_coords = list(polygon.exterior.coords)
                    print(f"Polygon Coordinates: {polygon_coords}")
                    found=True
                    break
            if not found:  
                asyncio.create_task(display_message_for_seconds("Please click within a polygon", 5)) 
                selected_polygon_id=None

 
    
    def setup_draw_control(self): #not sure?
        existing_draw_control=next((control for control in self.controls if isinstance(control, DrawControl)), None)
        if existing_draw_control:
            self.remove_control(existing_draw_control)
            self.draw_control=DrawControl()
            self.add_control(self.draw_control)
            self.draw_control.on_draw(self.handle_draw)  

    def draw_geojson(self, geo_json): #get id of polygon from app and others
        for layer in self.geojson_layers.values():
            self.remove_layer(layer)
        self.geojson_layers = {}  
        for feature in geo_json['features']:
            feature_id = feature.get('id', len(self.geojson_layers) + 1)
            geo_json_layer = GeoJSON(data=feature)
            geo_json_layer.on_click(lambda feature, **kwargs: self.handle_polygon_click(feature, **kwargs))
            self.add_layer(geo_json_layer) 
            self.geojson_layers[feature_id] = geo_json_layer



    def handle_draw(self, target, action, geo_json): #handle drawn and deleted shapes
        global global_geojson
        if action == "created":
            geo_json['id'] = len(global_geojson) + 1
            global_geojson.append(geo_json) 
            display_info.set(True)
            print("Shape drawn and stored: ", geo_json)
        elif action == "deleted": 
            delete = geo_json['geometry']['coordinates']
            global_geojson=[x for x in global_geojson if x['geometry']['coordinates'] != delete]
            print("Shape deleted: ", geo_json)

    
    def export(self, file_path): #export geojson data to a file
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



def get_recent_images(directory_path, selected_date): 
    path = Path(directory_path)
    all_files = list(path.glob('*.png'))  
    print(f"All files in directory: {all_files}")

    date_image_pairs = []
    for file_path in all_files:
        try:
            date_str = file_path.stem.split('_')[0]
            date_obj = datetime.datetime.strptime(date_str, '%Y%m%d')  
            
            if date_str == selected_date.replace("-", ""):
                date_image_pairs.append((date_obj, file_path))
        except Exception as e:
            print(f"Error parsing file {file_path}: {str(e)}")

    sorted_image_paths = [file_path for date_obj, file_path in sorted(date_image_pairs)]
    print(f"Sorted image paths for {selected_date}: {sorted_image_paths}")
    return sorted_image_paths

  

def load_ndvi_data():
    with open('ndvi_data.json', 'r') as f:
        data = json.load(f)
    return data['dates'], data['ndvi_values']
 
 
def get_and_display_recent_images(): #plot images on website
        if display_info.get() and selected_date.get() != "Select a date":
            directory_path = './plots/'  
            print('Fetching recent images for the date: {selected_date.get()}...')
            recent_images = get_recent_images(directory_path, selected_date.get())
            dates, ndvi_values = load_ndvi_data()

            
            # plot images using plt
            figs=[]
            # dummy_dates = ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'] #currently being used as we have no tiff files
            # dummy_ndvi_values = [0.2, 0.3, 0.5, 0.6, 0.7]
            fig, ax = plt.subplots(figsize=(10, 8), dpi=100)
            ax.plot(dates, ndvi_values, marker='o', linestyle='-', color='green')
            ax.set_title("NDVI Time Series")
            ax.set_xlabel("Date")
            ax.set_ylabel("NDVI Value")
            ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
            fig.autofmt_xdate() 
            figs.append(fig)  
            if recent_images:
                for img_path in recent_images:
                    try:
                        img = plt.imread(img_path)  
                        fig, ax = plt.subplots(figsize=(10, 8), dpi=100) 
                        ax.imshow(img, interpolation='bicubic')
                        ax.axis('off')  
                        figs.append(fig)
                        print(f"Loaded image {img_path}")
                    except Exception as e:
                        print(f"Failed to process image {img_path}: {str(e)}")
                
                if figs:
                    images_figures.set(figs) 
                    display_info.set(True)
                    print("Images are ready to be displayed.") 
                else:
                    print("No images were loaded.")
            else:
                print("No files in directory.")
        else:
            print("Nothing to process.")

def remove_images(): #remove images on pressing button
    display_info.set(False) 
    images_figures.set([])
    print("Images removed.")



@solara.component
def DisplayImages(): #component to display images
    if display_info.get():
        print("Displaying images...")
        return solara.VBox([solara.FigureMatplotlib(fig) for fig in images_figures.get()])
    print("No images to display")
    return None

def get_weather_metrics(polygon_coords, date):
    return {
        "Temperature": "28°C",
        "Humidity": "60%",
        "Wind Speed": "15 km/h",
        "Precipitation": "5 mm"
    }

@solara.component 
def TextCard(color, text, title=None): #each text card in grid
    if display_info.get() is True:
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
def DraggableGrid(): #grid to display info
    weather_data = get_weather_metrics(polygon_coords, selected_date.get())
    if display_info.get():
        if not weather_data:
            return solara.Text("No data available", style={"color": "red", "fontSize": "16px", "marginTop": "10px"})
            
        grid_layout_initial = [
            {"h": 3, "i": str(i), "moved": False, "w": 3, "x": i % 2 * 3, "y": i // 2 * 3} for i in range(4)
        ]
        colors = ["blue"]*4
        dummy_texts = [
            f"Temperature: {weather_data['Temperature']}",
            f"Humidity: {weather_data['Humidity']}",
            f"Wind Speed: {weather_data['Wind Speed']}",
            f"Precipitation: {weather_data['Precipitation']}",
        ]

        grid_layout, set_grid_layout = solara.use_state(grid_layout_initial) 

        items = [TextCard(title=f"Item {i}", color=colors[i], text=dummy_texts[i]) for i in range(len(dummy_texts))]
        
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
        PolygonClickMessage() #click polygon message
        SelectionConfirmationMessage()  #confirmed polygon click message

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
         

    def on_location_change(value): #when places are changed
        print(f"Selected location: {value}")  
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

    def reset_map(): #reset map to default location and zoom
        global global_geojson
        global_geojson = []
        print("Resetting map to default location and zoom")
        default_center = locations["Default"]
        center.set(default_center)
        zoom.set(5)
        map_instance.center = default_center
        map_instance.zoom = 5
        selected_location.set("Select a location") 
        delete_geojson_on_startup(r'./Data/output.geojson')
        print(f"Map reset to center: {default_center} and zoom: 5") 


    def export_geojson(): #export geojson coordinates file
        file_path=r'./Data/output.geojson'
        map_instance.export(file_path)
        info_collected.set(True)

       
    with solara.Column(style={"min-width": "500px", "display": "flex", "justifyContent": "center", "alignItems": "center", "flexDirection": "column"}):
        solara.Title("Sugarmill Farm Management Tool")
        PolygonClickMessage()
        # FileDrop()
        SelectionConfirmationMessage()  
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
                label="Collect Info",
                on_click=export_geojson,
                style={"width": "200px", "marginTop": "5px", "fontSize": "16px", "backgroundColor": "#28a745", "color": "white", "border": "none", "borderRadius": "5px", "padding": "10px 0"}
            )
            if info_collected.get():
                solara.Button( 
                    label="Display Info",
                    on_click=get_and_display_recent_images,
                    style={"width": "200px", "marginTop": "5px", "fontSize": "16px", "backgroundColor": "#28a745", "color": "white", "border": "none", "borderRadius": "5px", "padding": "10px 0"}
                ) 
                solara.Button(
                    label="Remove Info",
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
        
    DisplayImages()
    DateDropdown() 
    DraggableGrid()
    solara.Text(f"Zoom: {zoom.value}")
    solara.Text(f"Center: {center.value}")   