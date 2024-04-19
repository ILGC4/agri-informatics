from datetime import datetime
from planet import Auth
from planet import Session, data_filter,reporting
import os
import asyncio
import pandas as pd
import json

class PlanetData():
    
    def __init__(self,credentials,clear_percent_filter_value,date_range=None,cloud_cover_filter_value=0.1,item_types=None,limit=100,directory="output"):

        self.clear_percent_filter_value=clear_percent_filter_value
        self.cloud_cover_filter_value=cloud_cover_filter_value
        self.date_range=date_range
        self.credentials=credentials
        self.directory=directory
        self.item_types=item_types
        self.limit=limit
        self.client=self.__get_client__()

    def __get_combined_filter__(self):
        all_filters = []
        date_format = "%Y-%m-%d"  # dates are in 'YYYY-MM-DD' format

        if self.date_range:
            if 'gt' in self.date_range and 'lt' not in self.date_range:
                start_date = datetime.strptime(self.date_range['gt'], date_format)
                self.date_range_filter = data_filter.date_range_filter("acquired", gt=start_date)
            elif 'lt' in self.date_range and 'gt' not in self.date_range:
                end_date = datetime.strptime(self.date_range['lt'], date_format)
                self.date_range_filter = data_filter.date_range_filter("acquired", lt=end_date)
            else:
                start_date = datetime.strptime(self.date_range['gte'], date_format)
                end_date = datetime.strptime(self.date_range['lte'], date_format)
                self.date_range_filter = data_filter.date_range_filter("acquired", gt=start_date, lt=end_date)

            all_filters.append(self.date_range_filter)

        if self.geom!=None:
            geom_filter = data_filter.geometry_filter(self.geom)
            all_filters.append(geom_filter)

        if self.clear_percent_filter_value!=None:
            clear_percent_filter = data_filter.range_filter('clear_percent',self.clear_percent_filter_value[0],self.clear_percent_filter_value[1])
            all_filters.append(clear_percent_filter)
            
        if self.cloud_cover_filter_value!=None:
            cloud_cover_filter = data_filter.range_filter('cloud_percent',self.cloud_cover_filter_value[0],self.cloud_cover_filter_value[1])
            #all_filters.append(cloud_cover_filter)

        publish_filter = data_filter.string_in_filter('publishing_stage',['finalized']) 
        all_filters.append(publish_filter)   

        quality_filter = data_filter.string_in_filter('quality_category',['standard']) 
        all_filters.append(quality_filter) 

        instrument_filter=data_filter.string_in_filter('instrument',['PSB.SD'])
        #all_filters.append(instrument_filter)

        type_filter=data_filter.string_in_filter('item_type',['PSScene'])
        #all_filters.append(type_filter)

        asset_filter=data_filter.asset_filter(['ortho_analytic_8b','ortho_analytic_8b_xml','ortho_udm2'])
        #all_filters.append(asset_filter)

        combined_filter = data_filter.and_filter(all_filters)

        return combined_filter
    
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
       
        async with Session() as sess:
            request=await self.__create_request__()
            async with Session() as sess:
                cl = sess.client('data')
                items = cl.run_search(search_id=request['id'],limit=self.limit)
                item_list = [i async for i in items]

            item_list,search_df=self.filter_search_result(item_list)
            return item_list,search_df
    
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
        search_df_filtered=search_df.sort_values('clear_percent', ascending=False).drop_duplicates(['date'])
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
    
    async def download_multiple_assets(self, geom=None, asset_type_id=None, item_type='PSScene', id_list=None):
        self.geom = geom
        item_list, search_df = await self.search()
        csv_file_path = os.path.join(self.directory, "filter_df.csv")
        search_df.to_csv(csv_file_path, index=False)
        print(f"DataFrame saved to {csv_file_path}")
        
        if id_list is None:
            download_tasks = [self.download_asset(item['id'], asset_type_id) for item in item_list]
        else:
            download_tasks = [self.download_asset(idx, asset_type_id) for idx in id_list]
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