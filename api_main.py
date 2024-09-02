import re
import json
import asyncio
import pathlib
import rasterio
import numpy as np
import geopandas as gpd
from shapely.geometry import shape
from rasterio.mask import mask
import matplotlib.pyplot as plt
from Utils.api_utils import PlanetData, read_geojson, extract_corner_coordinates

def ndvi_time_series(tif_file, geom):
    with rasterio.open(tif_file) as src:
        gdf = gpd.GeoDataFrame({'geometry': [shape(geom)]}, crs="EPSG:4326")
        gdf = gdf.to_crs(src.crs)
        clipped_img, _ = mask(dataset=src, shapes=gdf.geometry, crop=True)
        nir = clipped_img[3, :, :]  
        red = clipped_img[2, :, :]
        ndvi = (nir - red) / (np.where((nir + red) == 0, 1, (nir + red)))
        return ndvi.mean()  



def normalize_bands(img):
    normalized_img = np.zeros_like(img, dtype=np.float32)
    for i in range(img.shape[0]):
        band = img[i, :, :]
        normalized_band = (band - np.min(band)) / (np.max(band) - np.min(band))
        normalized_img[i, :, :] = normalized_band
    return normalized_img

def plot_rgb_and_ndvi(rgb_img, ndvi, save_path=None):
    plt.figure(figsize=(14, 6))

    # Plot RGB
    plt.subplot(1, 2, 1)
    plt.imshow(rgb_img)
    plt.title('Selected Polygon')
    plt.axis('off')
    
    # Plot NDVI
    plt.subplot(1, 2, 2)
    plt.imshow(ndvi, cmap='RdYlGn')
    plt.title('Normalized Difference Vegetation Index (NDVI)')
    plt.axis('off')

    plt.colorbar(label='NDVI')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    # plt.show()

# function to handle API calls, data processing, and visualization
async def main():
    credentials = {'API_KEY': 'PLAKdc2fbb92b95b4abea465658318f59e1a'}  # jiya's
    geom_list = read_geojson("Data/output.geojson")  # Read the GeoJSON file
    if isinstance(geom_list, dict):
        geom_list = [geom_list]
    # print("geom:", geom_list)
        
    # create an instance of the PlanetData class
    planet_data = PlanetData(
        credentials=credentials,
        clear_percent_filter_value=(50, 100),  # clear images between 50% to 100%
        date_range={'gte': '2024-04-4', 'lte': '2024-04-10'}, 
        cloud_cover_filter_value=(0, 80),  # max cloud cover of 80%
        item_types=['PSScene'],  # satellite images
        limit=10,  # limit the number of images to retrieve
        directory="./Images/",  # directory to save downloaded stuff
        interval=5
    )
    # Iterate over each geometry
    for geom_idx, geom in enumerate(geom_list):
        print(f"Processing geometry {geom_idx + 1}...")
        
        # Download assets based on the current geometry
        results, item_list, search_df = await planet_data.download_multiple_assets(geom=geom, asset_type_id='ortho_analytic_8b_sr')
        tif_files = [result for result in results if pathlib.Path(result).suffix == '.tif']
        print("Results:", results)
        print("TIF files:", type(tif_files[0]))
        
        # Iterate over each TIFF file for the current geometry
        for idx, tif_file in enumerate(tif_files):
            filename = str(tif_file)  # Extract the filename from the PosixPath object
            date_str = filename[7:15]    # Extract the first eight characters of the filename as the date
            print("Date:", date_str)
            
            with rasterio.open(tif_file) as src:
                gdf = gpd.GeoDataFrame({'geometry': [shape(geom)]}, crs="EPSG:4326")
                gdf = gdf.to_crs(src.crs)
                
                # Clip satellite image
                clipped_img, clipped_transform = mask(dataset=src, shapes=gdf.geometry, crop=True)
                
                # Normalize bands of clipped image
                normalized_img = normalize_bands(clipped_img)
                blue = normalized_img[1,:,:]
                green = normalized_img[3,:,:]
                red = normalized_img[5,:,:]
                nir = normalized_img[7,:,:]
                ndvi = (nir - red) / (nir + red)
                rgb_img = np.dstack((red, green, blue))

                # Plot RGB image and NDVI
                plot_rgb_and_ndvi(rgb_img, ndvi)
                plot_rgb_and_ndvi(rgb_img, ndvi, save_path=f'plots/{date_str}_polygon_{geom_idx + 1}_tif_{idx + 1}.png')

    dates = []
    ndvi_values = []

    for tif_file in pathlib.Path('./path/to/tiff/files').glob('*.tif'):
        date_str = tif_file.stem[:6]  
        dates.append(date_str)
        ndvi_value = ndvi_time_series(tif_file, geom)
        ndvi_values.append(ndvi_value)
    
    with open('ndvi_data.json', 'w') as f:
        json.dump({'dates': dates, 'ndvi_values': ndvi_values}, f)

if __name__ == "__main__":
    asyncio.run(main())