import rasterio
from rasterio.plot import show
from rasterio.plot import show_hist
from rasterio.mask import mask
from shapely.geometry import box
import geopandas as gpd
from fiona.crs import from_epsg
import pycrs
import os
import json
# %matplotlib inline

fp = os.path.join('Images', '20240403_051921_25_24a4_3B_AnalyticMS_SR_8b.tif')
out_tif = os.path.join('Images', 'clipped.tif')

data = rasterio.open(fp)
print(data.crs.data)
# show((data, 4), cmap='terrain')

def read_geojson(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        geometries = []
        #geojson is dict and a collection
        if isinstance(data, dict) and data.get('type', '') == 'FeatureCollection':
            for feature in data['features']:
                geometries.append(feature['geometry'])
        elif isinstance(data, list):  #geojson has a list of polygons
            for feature in data:
                if 'geometry' in feature:
                    geometries.append(feature['geometry'])
        else:  #geojson has one polygon, is a dict but no collection
            if 'geometry' in data:
                geometries.append(data['geometry'])
        if len(geometries) == 1:
            return geometries[0]  # Return a single geometry dictionary if only one geometry
        else:
            return geometries

path = os.path.join('Data', 'output.geojson')
geom = read_geojson(path)
print(geom)
geom_list = list(geom.values())
cordinates = geom_list[1][0]
flat_coordinates = [coord for sublist in cordinates for coord in sublist]
x_cord, y_cord = zip(*cordinates)
minx, miny = min(x_cord), min(y_cord)
maxx, maxy = max(x_cord), max(y_cord)
bbox = box(minx, miny, maxx, maxy)

geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0], crs=from_epsg(4326)) 
geo = geo.to_crs(crs=data.crs.data)
print("crs", geo.crs)


def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

coords = getFeatures(geo)
print(coords)

out_img, out_transform = mask(dataset=data, shapes=coords, crop=True)
out_meta = data.meta.copy()
epsg_code = int(data.crs.data['init'][5:])
print(epsg_code)
out_meta.update({"driver": "GTiff",
                 "height": out_img.shape[1],
                 "width": out_img.shape[2],
                 "transform": out_transform,
                 "crs": pycrs.parse.from_epsg_code(epsg_code).to_proj4()}
                         )
with rasterio.open(out_tif, "w", **out_meta) as dest:
        dest.write(out_img)
clipped = rasterio.open(out_tif)
show((clipped, 5), cmap='terrain')