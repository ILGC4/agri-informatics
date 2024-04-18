import asyncio
from Utils.api_utils import PlanetData 
import pathlib
from Utils.api_utils import read_geojson

async def filter_tiff_files(results): # Filter .tif files for ndvi
    tif_files = [result for result in results if pathlib.Path(result).suffix == '.tif']
    return tif_files

async def main():
    credentials = {'API_KEY': 'PLAK28bdd18f2ecb4022b2599de197421f8d'}  # shivangi's
    
    # Read the GeoJSON file
    geom = read_geojson("Data/output.geojson")
    
    # Create an instance of the PlanetData class
    planet_data = PlanetData(
        credentials=credentials,
        clear_percent_filter_value=(80, 100),  # clear images between 80% to 100%
        date_range={'gte': '2024-03-30', 'lte': '2024-04-04'}, 
        cloud_cover_filter_value=(0, 20),  # max cloud cover of 20%
        item_types=['PSScene'],  # satellite images
        limit=10,  # limit the number of images to retrieve
        directory="./Images/"  # directory to save downloaded stuff
    )
    
    # Download assets based on the provided geometry
    results, item_list, search_df = await planet_data.download_multiple_assets(geom=geom, asset_type_id='ortho_analytic_8b_sr')

    return results

if __name__ == "__main__":
    results = asyncio.run(main())
    tif_images = asyncio.run(filter_tiff_files(results))
    print("TIFF Images:", tif_images)
