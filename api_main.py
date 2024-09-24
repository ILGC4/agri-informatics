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
import state
import warnings

warnings.filterwarnings("ignore")

def normalize_bands(img):
    normalized_img = np.zeros_like(img, dtype=np.float32)
    for i in range(img.shape[0]):
        band = img[i, :, :]
        min_val = np.min(band)
        max_val = np.max(band)
        
        # If the band is constant, fill with zeros instead of dividing by zero
        if min_val == max_val:
            normalized_img[i, :, :] = 0
        else:
            normalized_img[i, :, :] = (band - min_val) / (max_val - min_val)
    return normalized_img

def ndvi_time_series(tif_file, geom=None):
    with rasterio.open(tif_file) as src:
        # Read the entire image (global normalisatuin)
        full_img = src.read()
        normalized_full_img = normalize_bands(full_img)
        nir_full = normalized_full_img[7, :, :]
        red_full = normalized_full_img[5, :, :]

        # min and max of NIR and Red band
        print(f"NIR Full min: {np.min(nir_full)}, max: {np.max(nir_full)}")
        print(f"Red Full min: {np.min(red_full)}, max: {np.max(red_full)}")

        # Proceed only if NIR and Red have valid ranges
        if np.max(nir_full) > 0 and np.max(red_full) > 0:
            ndvi_full = np.where((nir_full + red_full) == 0, np.nan, (nir_full - red_full) / (nir_full + red_full))
            ndvi_full_mean = np.nanmean(ndvi_full)
        else:
            ndvi_full_mean = np.nan
            ndvi_full = np.zeros_like(nir_full)

        # If geometry is provided, clip the image
        if geom:
            gdf = gpd.GeoDataFrame({'geometry': [shape(geom)]}, crs="EPSG:4326")
            gdf = gdf.to_crs(src.crs)
            clipped_img, _ = mask(dataset=src, shapes=gdf.geometry, crop=True)
            normalized_clipped_img = normalize_bands(clipped_img)
            nir_clipped = normalized_clipped_img[7, :, :]
            red_clipped = normalized_clipped_img[5, :, :]

            print(f"NIR Clipped min: {np.min(nir_clipped)}, max: {np.max(nir_clipped)}")
            print(f"Red Clipped min: {np.min(red_clipped)}, max: {np.max(red_clipped)}")

            if np.max(nir_clipped) > 0 and np.max(red_clipped) > 0:
                ndvi_clipped = np.where((nir_clipped + red_clipped) == 0, np.nan, (nir_clipped - red_clipped) / (nir_clipped + red_clipped))
                ndvi_clipped_mean = np.nanmean(ndvi_clipped)
            else:
                ndvi_clipped_mean = np.nan
                ndvi_clipped = np.zeros_like(nir_clipped)

            return ndvi_full_mean, ndvi_full, ndvi_clipped_mean, ndvi_clipped

        return ndvi_full_mean, ndvi_full, None, None


def plot_rgb_and_ndvi(rgb_img, ndvi, title, save_path=None):
    plt.figure(figsize=(14, 6))

    # Plot RGB
    plt.subplot(1, 2, 1)
    plt.imshow(rgb_img)
    plt.title('RGB Image')
    plt.axis('off')

    # Plot NDVI
    plt.subplot(1, 2, 2)
    plt.imshow(ndvi, cmap='RdYlGn')
    plt.title(f'NDVI ({title})')
    plt.axis('off')

    plt.colorbar(label='NDVI')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)

async def main():
    credentials = {'API_KEY': 'PLAKdc2fbb92b95b4abea465658318f59e1a'}  # jiya's
    geom_list = read_geojson("Data/output.geojson")
    if isinstance(geom_list, dict):
        geom_list = [geom_list]
    
    # create an instance of the PlanetData class
    planet_data = PlanetData(
        credentials=credentials,
        clear_percent_filter_value=(50, 100),  # clear images between 50% to 100%
        date_range={'gte': '2024-05-07', 'lte': '2024-05-14'}, 
        cloud_cover_filter_value=(0, 100),  # max cloud cover of 80%
        item_types=['PSScene'],  # satellite images
        limit=10,  # limit the number of images to retrieve
        directory="./Images/",  # directory to save downloaded stuff
        interval=3
    )

    # Iterate over each geometry
    for geom_idx, geom in enumerate(geom_list):
        print(f"Processing geometry {geom_idx + 1}...")
        
        # Download assets based on the current geometry
        results, item_list, search_df = await planet_data.download_multiple_assets(geom=geom, asset_type_id='ortho_analytic_8b_sr')
        tif_files = [result for result in results if pathlib.Path(result).suffix == '.tif']

        # Iterate over each tiff file for the current geometry
        for idx, tif_file in enumerate(tif_files):
            filename = str(tif_file)
            date_str = filename[7:15]  # Extract date from filename
            
            with rasterio.open(tif_file) as src:
                # Get NDVI for both full image and clipped area
                ndvi_full_mean, ndvi_full, ndvi_clipped_mean, ndvi_clipped = ndvi_time_series(tif_file, geom)

                print(f"Full image NDVI mean for {filename}: {ndvi_full_mean}")
                if ndvi_clipped_mean is not None:
                    print(f"Clipped NDVI mean for {filename}: {ndvi_clipped_mean}")
                else:
                    print(f"No clipped NDVI for {filename}.")

                # Normalize for RGB img
                full_img = src.read()
                normalized_full_img = normalize_bands(full_img)
                blue = normalized_full_img[1, :, :]
                green = normalized_full_img[3, :, :]
                red = normalized_full_img[5, :, :]
                rgb_img_full = np.dstack((red, green, blue))

                # RGB and NDVI for full
                plot_rgb_and_ndvi(rgb_img_full, ndvi_full, "Full Image", save_path=f'plots/{date_str}_full_image_{idx + 1}.png')

                # RGB and NDVI for clipped
                if ndvi_clipped is not None:
                    clipped_img, _ = mask(dataset=src, shapes=gpd.GeoDataFrame({'geometry': [shape(geom)]}, crs="EPSG:4326").to_crs(src.crs).geometry, crop=True)
                    normalized_clipped_img = normalize_bands(clipped_img)
                    blue_clipped = normalized_clipped_img[1, :, :]
                    green_clipped = normalized_clipped_img[3, :, :]
                    red_clipped = normalized_clipped_img[5, :, :]
                    rgb_img_clipped = np.dstack((red_clipped, green_clipped, blue_clipped))

                    plot_rgb_and_ndvi(rgb_img_clipped, ndvi_clipped, "Clipped Area", save_path=f'plots/{date_str}_clipped_polygon_{geom_idx + 1}_tif_{idx + 1}.png')

if __name__ == "__main__":
    asyncio.run(main())
