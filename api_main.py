import asyncio
from api_utils import PlanetData 
async def main():
    credentials = {'API_KEY': 'PLAKdc2fbb92b95b4abea465658318f59e1a'} # mine (chaitanya)
    geom = {
             "coordinates": [
              [
                [80.71432368381613, 28.046503909233863],
                [80.71432368381613, 28.035485897499825],
                [80.72851428277824, 28.035485897499825],
                [80.72851428277824, 28.046503909233863],
                [80.71432368381613, 28.046503909233863]
               ]
             ],
            "type": "Polygon"
          }
    
    # an instance of class in utils
    planet_data = PlanetData(
        credentials=credentials,
        clear_percent_filter_value=(80, 100),  # clear images between 80% to 100%
        date_range={'gte': '2024-02-14', 'lte': '2024-04-01'}, 
        cloud_cover_filter_value=(0, 20),  # max cloud cover of 20%
        item_types=['PSScene'],  # satellite images
        limit=10,  # limit the number of images to retrieve
        directory="/Users/chaitanyamodi/Downloads/Images"  # directory to save downloaded stuff
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
