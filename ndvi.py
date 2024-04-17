import rasterio
import numpy as np
import matplotlib.pyplot as plt
import asyncio
import api_main 

def to_ndvi(images):
    with rasterio.open(images) as src:
        image = src.read()
        meta = src.meta
    
    def normalize_bands(band):
        return (band - band.min()) / (band.max() - band.min())
    
    normalized_image = np.zeros_like(image, dtype=np.float32)
    for i in range(image.shape[0]):
        normalized_image[i,:,:] = normalize_bands(image[i,:,:])
    
    blue = normalized_image[1,:,:]
    green = normalized_image[3,:,:]
    red = normalized_image[5,:,:]
    nir = normalized_image[7,:,:]
    
    ndvi = (nir - red) / (nir + red + 1e-15) # add + 1e-15 to avoid division by zero

    plt.figure(figsize=(15, 6))
    # Plot RGB
    plt.subplot(1, 2, 1)
    plt.imshow(np.dstack((red, green, blue)))
    plt.title('RGB Image')
    plt.xlabel('Column')
    plt.ylabel('Row')

    # Plot NDVI
    plt.subplot(1, 2, 2)
    plt.imshow(ndvi, cmap='RdYlGn')
    plt.colorbar(label='NDVI')
    plt.title('Normalized Difference Vegetation Index (NDVI)')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.tight_layout()
    plt.show()

async def process_images():
    tif_files = await api_main.main()  # retrieve .tif files from api_main
    for image in tif_files:
        to_ndvi(image)

if __name__ == "__main__":
    asyncio.run(process_images())
