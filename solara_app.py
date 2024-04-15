import leafmap
import solara
from ipyleaflet import Map, DrawControl
import json
from leafmap.toolbar import change_basemap

global_geojson = None #cause literally nothing else was working i wanna kms so bad

zoom = solara.reactive(5)
center = solara.reactive((22.0, 78.0))

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

        # Initialize a variable to hold the GeoJSON data
        self.draw_data = None

        # Set up event handling for drawing on the map
        self.draw_control.on_draw(self.handle_draw)

    def handle_draw(self, target, action, geo_json):
        # Store the drawn GeoJSON data
        global global_geojson
        if action == "created":
            global_geojson=geo_json
            print("Shape drawn and stored: ", global_geojson)

    def export(self, file_path):
        global global_geojson
        print("this is the data:", global_geojson)
        if global_geojson is not None:
            with open(file_path, "w") as f:
                json.dump(global_geojson, f)
            print("GeoJSON data exported to: ", file_path)
        else:
            print("No data to export")


@solara.component
def Page():
    with solara.AppBarTitle():
        solara.Text("Sugarmill Farm Management Tool", style={"fontSize": "24px", "fontWeight": "bold", "textAlign": "center", "alignItems": "center"})
    
    map_instance = Map()


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
        global_geojson = None
        print("Resetting map to default location and zoom")
        default_center = locations["Default"]
        center.set(default_center)
        zoom.set(5)
        map_instance.center = default_center
        map_instance.zoom = 5
        selected_location.set("Select a location")  # Optionally reset the dropdown
        print(f"Map reset to center: {default_center} and zoom: 5")


    def export_geojson():
        file_path=r'/Users/chaitanyamodi/Downloads/agri-informatics/Data/output.geojson'
        map_instance.export(file_path)


    with solara.Column(style={"min-width": "500px", "display": "flex", "justifyContent": "center", "alignItems": "center", "flexDirection": "column"}):
        solara.Title("Sugarmill Farm Management Tool")
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