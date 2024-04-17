import asyncio
from Utils.api_utils import PlanetData 
import pathlib
from Utils.api_utils import read_geojson

async def main():
  credentials = {'API_KEY': 'PLAK28bdd18f2ecb4022b2599de197421f8d'}  # shivangi's
  geom = read_geojson("Data/output2.geojson")

  #  an instance of the class in utils
  planet_data = PlanetData(
    credentials=credentials,
    clear_percent_filter_value=(80, 100),  # clear images between 80% to 100%
    date_range={'gte': '2024-03-30', 'lte': '2024-04-04'}, 
    cloud_cover_filter_value=(0, 20),  # max cloud cover of 20%
    item_types=['PSScene'],  # satellite images
    limit=10,  # limit the number of images to retrieve
    directory="./Images/"  # directory to save downloaded stuff
)
    
  # for poly in geom:
  #     print(poly)
  results, item_list, search_df = await planet_data.download_multiple_assets(geom=geom, asset_type_id='ortho_analytic_8b_sr')

  print("Downloaded assets:")
  print(results)
  print("Items list:")
  print(item_list)
  print("Search DataFrame:")
  print(search_df)

  tif_files = [result for result in results if pathlib.Path(result).suffix == '.tif']
  return tif_files

if __name__ == "__main__":
    tif_images = asyncio.run(main())
    print("TIFF Images:", tif_images)
