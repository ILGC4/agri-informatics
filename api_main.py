import asyncio
from Utils.api_utils import PlanetData 
async def main():
    credentials = {'API_KEY': 'PLAKbc1515084b754a179875fd75af529072'} # zoya's
    geom = {
            "coordinates": [
            [
              [80.753117, 27.960661], 
              [80.754393, 27.961983], 
              [80.755917, 27.961016], 
              [80.754066, 27.959855], 
              [80.753117, 27.960661]
              ]
            ],
            "type": "Polygon"
          }  
      
    # an instance of class in utils
    planet_data = PlanetData(
        credentials=credentials,
        clear_percent_filter_value=(80, 100),  # clear images between 80% to 100%
        date_range={'gte': '2024-03-14', 'lte': '2024-04-01'}, 
        cloud_cover_filter_value=(0, 20),  # max cloud cover of 20%
        item_types=['PSScene'],  # satellite images
        limit=10,  # limit the number of images to retrieve
        directory="/Users/chaitanyamodi/Downloads/agri-informatics/Images/"  # directory to save downloaded stuff
    )
    
    results, item_list, search_df = await planet_data.download_multiple_assets(geom=geom, asset_type_id='ortho_analytic_8b_sr')
    
    print("Downloaded assets:")
    print(results)
    print("Items list:")
    print(item_list)
    print("Search DataFrame:")
    print(search_df)

if __name__ == "__main__":
    asyncio.run(main())
