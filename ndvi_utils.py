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
import warnings

warnings.filterwarnings("ignore")

def normalize_bands(img):
    normalized_img = np.zeros_like(img, dtype=np.float32)
    for i in range(img.shape[0]):
        band = img[i, :, :]
        min_val = np.min(band)
        max_val = np.max(band)
        
        if min_val == max_val:
            normalized_img[i, :, :] = 0
        else:
            normalized_img[i, :, :] = (band - min_val) / (max_val - min_val)
    return normalized_img

def ndvi_time_series(tif_file, geom=None):
    with rasterio.open(tif_file) as src:
        full_img = src.read()
        normalized_full_img = normalize_bands(full_img)
        nir_full = normalized_full_img[7, :, :]
        red_full = normalized_full_img[5, :, :]

        print(f"NIR Full min: {np.min(nir_full)}, max: {np.max(nir_full)}")
        print(f"Red Full min: {np.min(red_full)}, max: {np.max(red_full)}")

        if np.max(nir_full) > 0 and np.max(red_full) > 0:
            ndvi_full = np.where((nir_full + red_full) == 0, np.nan, (nir_full - red_full) / (nir_full + red_full))
            ndvi_full_mean = np.nanmean(ndvi_full)
        else:
            ndvi_full_mean = np.nan
            ndvi_full = np.zeros_like(nir_full)

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

def ndvi_time_series_farm(tif_file, geoms=None):
    """
    Calculate NDVI values for a list of geometries from a TIFF file.
    
    Parameters:
    tif_file (str): Path to the TIFF file
    geoms (list): List of geometry objects
    
    Returns:
    dict: Dictionary with geometry objects as keys and a tuple of (mean_ndvi, ndvi_array) as values
    """
    # Initialize results dictionary
    results = {}
    
    # If no geometries provided, return empty dictionary
    if not geoms:
        return results
        
    with rasterio.open(tif_file) as src:
        # Process each geometry
        for geom in geoms:
            if geom is None:
                continue
                
            # Convert geometry to GeoDataFrame with correct CRS
            gdf = gpd.GeoDataFrame({'geometry': [shape(geom)]}, crs="EPSG:4326")
            gdf = gdf.to_crs(src.crs)
            
            # Mask/clip the raster with the geometry
            clipped_img, _ = mask(dataset=src, shapes=gdf.geometry, crop=True)
            normalized_clipped_img = normalize_bands(clipped_img)
            
            nir_clipped = normalized_clipped_img[7, :, :]
            red_clipped = normalized_clipped_img[5, :, :]
            
            print(f"NIR Clipped min: {np.min(nir_clipped)}, max: {np.max(nir_clipped)}")
            print(f"Red Clipped min: {np.min(red_clipped)}, max: {np.max(red_clipped)}")
            
            if np.max(nir_clipped) > 0 and np.max(red_clipped) > 0:
                ndvi_clipped = np.where(
                    (nir_clipped + red_clipped) == 0, 
                    np.nan, 
                    (nir_clipped - red_clipped) / (nir_clipped + red_clipped)
                )
                ndvi_clipped_mean = np.nanmean(ndvi_clipped)
            else:
                ndvi_clipped_mean = np.nan
                ndvi_clipped = np.zeros_like(nir_clipped)
            
            # Add to results dictionary with the geometry as key
            results[geom] = (ndvi_clipped_mean, ndvi_clipped)
    
    return results

def plot_rgb_and_ndvi(rgb_img, ndvi, title, save_path=None):
    plt.figure(figsize=(14, 6))

    plt.subplot(1, 2, 1)
    plt.imshow(rgb_img)
    plt.title('RGB Image')
    plt.axis('off')

    plt.subplot(1, 2, 2)
    plt.imshow(ndvi, cmap='RdYlGn')
    plt.title(f'NDVI ({title})')
    plt.axis('off')

    plt.colorbar(label='NDVI')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
