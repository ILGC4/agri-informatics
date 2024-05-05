from datetime import datetime
from planet import Auth
from planet import Session, data_filter,reporting
import os
import asyncio
import pandas as pd
import json
from datetime import timedelta
import sys
from Utils.database_utils import check_area_coverage, add_new_image

class PlanetData():
    
    def __init__(self,credentials,clear_percent_filter_value, date_range=None,cloud_cover_filter_value=0.1,item_types=None,limit=100,directory="output", frequency = None):

        self.clear_percent_filter_value=clear_percent_filter_value
        self.cloud_cover_filter_value=cloud_cover_filter_value
        self.date_range=date_range
        self.credentials=credentials
        self.directory=directory
        self.item_types=item_types
        self.limit=limit
        self.frequency=frequency
        self.client=self.__get_client__()

    def __get_combined_filter__(self):
        base_filters = []

        if self.geom:
            geom_filter = data_filter.geometry_filter(self.geom)
            base_filters.append(geom_filter)

        if self.clear_percent_filter_value:
            clear_percent_filter = data_filter.range_filter('clear_percent', gt=self.clear_percent_filter_value[0], lt=self.clear_percent_filter_value[1])
            base_filters.append(clear_percent_filter)

        publish_filter = data_filter.string_in_filter('publishing_stage', ['finalized'])
        base_filters.append(publish_filter)

        quality_filter = data_filter.string_in_filter('quality_category', ['standard'])
        base_filters.append(quality_filter)

        # Use generate_date_ranges to get datetime objects for filters
        date_ranges = self.generate_date_ranges(self.date_range['gte'], self.date_range['lte'], self.frequency)

        combined_filters = []
        for date_range in date_ranges:
            date_filter = data_filter.date_range_filter("acquired", gte=date_range['gte'], lte=date_range['lte'])
            combined_filters.append(data_filter.and_filter([date_filter] + base_filters))

        return combined_filters
    
    def generate_date_ranges(self, start_date, end_date, frequency):
        date_ranges = []
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            if next_date > end_date:
                next_date = end_date
            
            # Here, store the datetime objects directly rather than converting them to strings
            date_ranges.append({
                'gte': current_date,  # Directly use datetime object
                'lte': next_date      # Directly use datetime object
            })
            
            current_date += timedelta(days=frequency)
            if current_date > end_date:
                break
        print("Date Ranges", date_ranges)
        return date_ranges
    
    def __get_client__(self):
        API_KEY = self.credentials['API_KEY']
        os.environ['PL_API_KEY'] = API_KEY
        client = Auth.from_key(API_KEY)
        return client
    
    async def __create_request__(self):
        combined_filter=self.__get_combined_filter__()
        async with Session() as sess:
            cl = sess.client('data')
            request = await cl.create_search(name='planet_client_demo',search_filter=combined_filter, item_types=self.item_types)
        return request   

    async def search(self):
        combined_filters = self.__get_combined_filter__()
        item_list_total = []
        search_df_total = pd.DataFrame()

        async with Session() as sess:
            cl = sess.client('data')
            for each_combined_filter in combined_filters:
                print("Current combined filter:", each_combined_filter)
                request = await cl.create_search(name='planet_client_demo', search_filter=each_combined_filter, item_types=self.item_types)
                items = cl.run_search(search_id=request['id'], limit=self.limit)
                item_list = [i async for i in items]
                if item_list:
                    # changed item list total from _ to ensure 1 image per day
                    item_list_total, search_df = self.filter_search_result(item_list)
                    # item_list_total.extend(item_list)
                    search_df_total = pd.concat([search_df_total, search_df], ignore_index=True)
                else:
                    print("No images found for the days given that satisfy the filters")

        if len(item_list_total) == 0:
            print("No images found for the days given that satisfy the filters")
            sys.exit(1)

        csv_file_path = os.path.join(self.directory, "filter_df.csv")
        search_df_total.to_csv(csv_file_path, index=False)
        print(f"DataFrame saved to {csv_file_path}")

        return item_list_total, search_df_total
    
    async def activate_assets(self,item_id,item_type,asset_type_id):

        async with Session() as sess:
            cl = sess.client('data')
            # Get Asset
            asset_desc = await cl.get_asset(item_type_id=item_type,item_id=item_id,asset_type_id=asset_type_id)
            # Activate Asset
            await cl.activate_asset(asset=asset_desc)
            # Wait Asset
            with reporting.StateBar(state='creating') as bar:
                bar.update(state='created', order_id=item_id)
                await cl.wait_asset(asset=asset_desc, callback=bar.update_state)

            return asset_desc
    
    def filter_search_result(self,item_list):
        new_item_list=[]
        all_properties=[]
        for item in item_list:
            properties=item['properties']
            properties['id']=item['id']
            properties['date']=item['id'].split("_")[0]
            all_properties.append(properties)
        search_df=pd.DataFrame(all_properties)
        print(search_df)
        search_df_filtered=search_df.sort_values('cloud_cover', ascending=True).drop_duplicates(['date'])
        filtered_item_ids=search_df_filtered['id'].tolist()

        for item in item_list:
            if item['id'] in filtered_item_ids:
                new_item_list.append(item)

        search_df_filtered['acquired']=pd.to_datetime(search_df_filtered['acquired'])  
        return new_item_list,search_df_filtered

    async def download_asset(self, item_id=None, asset_type_id=None, item_type='PSScene', retries=3):
        attempt = 0
        while attempt < retries:
            try:
                await self.activate_assets(item_id, item_type, asset_type_id)
                async with Session() as sess:
                    cl = sess.client('data')
                    asset_desc = await cl.get_asset(item_type_id=item_type, item_id=item_id, asset_type_id=asset_type_id)
                    asset_path = await cl.download_asset(asset=asset_desc, directory=self.directory, overwrite=True)
                    print(f"Downloaded asset {item_id} to {asset_path}")
                    return asset_path
            except Exception as e:
                print(f"Failed to download asset {item_id}, attempt {attempt+1} of {retries}: {str(e)}")
                attempt += 1
                await asyncio.sleep(2**attempt)  # exponential backoff
        raise Exception(f"Failed to download asset {item_id} after {retries} attempts")
    
    async def download_asset_with_database_check(self,item_id=None, asset_type_id=None, date=None, item_type='PSScene', retries=3):
        attempt = 0
        asset_path = check_area_coverage(polygon = self.geom, date = date, )
        if asset_path is not None:
            return asset_path
        else:
            while attempt < retries:
                try:
                    await self.activate_assets(item_id, item_type, asset_type_id)
                    async with Session() as sess:
                        cl = sess.client('data')
                        asset_desc = await cl.get_asset(item_type_id=item_type, item_id=item_id, asset_type_id=asset_type_id)
                        asset_path = await cl.download_asset(asset=asset_desc, directory=self.directory, overwrite=True)
                        print(f"Downloaded asset {item_id} to {asset_path}")
                        add_new_image(tile_id = item_id, acquisition_date = date, geojson_polygon = self.geom, image_path = asset_path)
                        return asset_path
                except Exception as e:
                    print(f"Failed to download asset {item_id}, attempt {attempt+1} of {retries}: {str(e)}")
                    attempt += 1
                    await asyncio.sleep(2**attempt)  # exponential backoff
            raise Exception(f"Failed to download asset {item_id} after {retries} attempts")

    async def download_multiple_assets(self, geom=None, asset_type_id=None, item_type='PSScene', id_list=None):
        self.geom = geom
        print("self geom",self.geom)
        name = extract_last_three_digits_string(self.geom)
        print("name:", name)
        item_list, search_df = await self.search()
        csv_file_path = os.path.join(self.directory, f"{name}_filter_df.csv")
        search_df.to_csv(csv_file_path, index=False)
        print(f"DataFrame saved to {csv_file_path}")
        
        if id_list is None:
            download_tasks = [self.download_asset_with_database_check(item['id'], asset_type_id, item['properties']['date']) for item in item_list]
        else:
            download_tasks = [self.download_asset_with_database_check(idx, asset_type_id) for idx in id_list]
            item_list = id_list

        results = await asyncio.gather(*download_tasks, return_exceptions=True)  # retry logic inside download_asset
        return results, item_list, search_df
    
    
def read_geojson(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        geometries = []
        #geojson is dict and a collection
        if isinstance(data, dict) and data.get('type', '') == 'FeatureCollection':
            for feature in data['features']:
                geometries.append(feature['geometry'])
        elif isinstance(data, list):  #geojson has a list of polygons
            for feature in data:
                if 'geometry' in feature:
                    geometries.append(feature['geometry'])
        else:  #geojson has one polygon, is a dict but no collection
            if 'geometry' in data:
                geometries.append(data['geometry'])
        if len(geometries) == 1:
            return geometries[0]  # Return a single geometry dictionary if only one geometry
        else:
            return geometries
        
def extract_last_three_digits_string(geom):
    coordinates = geom['coordinates']
    last_three_digits_list = []
    for coord_set in coordinates:
        for coordinate in coord_set:
            longitude = coordinate[0]  # Long is the first element in each coordinate set
            longitude_str = str(longitude)
            longitude_parts = longitude_str.split('.')
            last_three_digits = longitude_parts[1][-3:]
            last_three_digits_list.append(last_three_digits)
    last_three_digits_string = '_'.join(last_three_digits_list)
    
    return last_three_digits_string