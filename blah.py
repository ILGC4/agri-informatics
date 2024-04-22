import asyncio
from Utils.api_utils import PlanetData 
import pathlib
from Utils.api_utils import read_geojson
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def plot_ndvi(image):
    # counter = 1
    # for image in tif_files:
    with rasterio.open(image) as src:
        img = src.read()
        meta = src.meta
    
    def normalize_bands(band):
        return (band - band.min()) / (band.max() - band.min())
    
    normalized_image = np.zeros_like(img, dtype=np.float32)
    for i in range(img.shape[0]):
        normalized_image[i,:,:] = normalize_bands(img[i,:,:])
    
    blue = normalized_image[1,:,:]
    green = normalized_image[3,:,:]
    red = normalized_image[5,:,:]
    nir = normalized_image[7,:,:]
    
    ndvi = (nir - red) / (nir + red + 1e-15) # added + 1e-15 to avoid division by zero
    rgb_img = np.dstack((red, green, blue))

    # plot the images
    plt.figure(figsize=(15, 6))

    # Plot RGB
    plt.subplot(1, 2, 1)
    plt.imshow(rgb_img)
    plt.title('RGB Image')
    plt.axis('off')
    # Plot NDVI
    plt.subplot(1, 2, 2)
    plt.imshow(ndvi, cmap='RdYlGn')
    plt.title('Normalized Difference Vegetation Index (NDVI)')
    plt.axis('off')

    plt.colorbar(label='NDVI')
    plt.tight_layout()
    plt.show()
    # plt.savefig(f'plots/ndvi{counter}.png')
    # plt.close()
    # plt.show()
        # counter += 1
    print('images_saved')

if __name__ == '__main__':
    plot_ndvi('Images/20240404_051843_68_2484_3B_AnalyticMS_SR_8b.tif')