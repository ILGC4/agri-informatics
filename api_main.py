import asyncio
from Utils.api_utils import PlanetData 
import pathlib
from Utils.api_utils import read_geojson
import rasterio
import numpy as np
import matplotlib.pyplot as plt

async def main():
    credentials = {'API_KEY': 'PLAK94fef94d4aa5492cb50dc94d2109a4bc'} # prof anupam
    
    # Read the GeoJSON file
    geom = read_geojson("Data/output.geojson")
    
    # Create an instance of the PlanetData class
    planet_data = PlanetData(
        credentials=credentials,
        clear_percent_filter_value=(20, 100),  # clear images between 80% to 100%
        date_range={'gte': '2024-04-01', 'lte': '2024-04-03'}, 
        cloud_cover_filter_value=(0, 80),  # max cloud cover of 20%
        item_types=['PSScene'],  # satellite images
        limit=10,  # limit the number of images to retrieve
        directory="./Images/", # directory to save downloaded stuff
        frequency=5
    )
    
    # Download assets based on the provided geometry
    results, item_list, search_df = await planet_data.download_multiple_assets(geom=geom, asset_type_id='ortho_analytic_8b_sr')
    tif_files = [result for result in results if pathlib.Path(result).suffix == '.tif']
    
    counter = 1
    for image in tif_files:
        print(tif_files)
        with rasterio.open(tif_files[0]) as src:
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
        # plt.savefig(f'plots/ndvi.png')
        plt.savefig(f'plots/ndvi{counter}.png')
        # plt.close()
        plt.show()
        counter += 1
        print('images_saved')
    print("done")

if __name__ == "__main__":
    asyncio.run(main())