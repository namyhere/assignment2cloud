import json
import os
import decimal
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import datetime
import pandas as pd
import requests

API_KEY = 'yRc-tMeDvrrPo8ElLQo-TaOfL86NF9U0ERPdS3tsoa2vTlQSUJyAClT2oJiGN0mnLfqNVF34TjOow-13_ck8VO_QSv6DWM-uC5U8qR2xOZ4R1CXKCdzyo6qLVFNOY3Yx'
ENDPOINT = 'https://api.yelp.com/v3/businesses/search'
HEADERS = {'Authorization': 'bearer %s' % API_KEY}
LIMIT = 50
restaurants = {}
cuisines = ['Italian', 'Chinese', 'Mexican', 'Indian', 'Japanese', 'Thai', 'American', 'Korean', 'Arab']
location = 'Manhattan'
businesses = []

def get_restaurants(term, location, offset):

    parameters = {
        'term' : term.replace(' ', '+'),
        'location' : location.replace(' ', '+'),
        'limit' : LIMIT,
        'offset' : offset,
    }

    return requests.get(url = ENDPOINT, params = parameters, headers = HEADERS)

for cuisine in cuisines:
    for offset in range(0, 1000, 50):
        response = get_restaurants(term = cuisine, location = location, offset = offset)
        restaurants = response.json()['businesses']
        for restaurant in restaurants:
            restaurant_id = restaurant['id']
            restaurant_name = restaurant['name']
            cuisine_type = cuisine
            restaurant_address = "'" + (", ").join(restaurant['location']['display_address']) + "'"
            latitude = decimal.Decimal(str(restaurant['coordinates']['latitude']))
            longitude = decimal.Decimal(str(restaurant['coordinates']['longitude']))
            restaurant_rating = decimal.Decimal(str(restaurant['rating']))
            review_count = restaurant['review_count']
            price = restaurant.get('price', None)

            businesses.append([restaurant_id, restaurant_name, cuisine_type, restaurant_address,
                            latitude, longitude, restaurant_rating, review_count, price])

df = pd.DataFrame(businesses, columns=['restaurantId', 'restaurantName', 'cuisineType', 'restaurantAddress', 
          'Longitude', 'Latitude', 'restaurantRating', 'reviewCount', 'priceRange'])
df['restaurantId'] = df['restaurantId'].str.replace('-', '')
df['restaurantId'] = df['restaurantId'].str.replace(' ', '')
df['restaurantId'] = df['restaurantId'].str.replace('_', '')
df = df.drop_duplicates(subset = 'restaurantId')
df['priceRange'].fillna('$$', inplace = True)
ACCESS_KEY = 'AKIAW6GPWFZDCFHIM63T'
SECRET_KEY = 'Ui+R8+kPkTOylJ0j895I9wqftMCETRGgwmj3LhfW'
dynamodb = boto3.resource('dynamodb', 
                          region_name='us-east-1',
                          aws_access_key_id=ACCESS_KEY, 
                          aws_secret_access_key=SECRET_KEY)
table = dynamodb.Table('yelp-restaurants')
host = 'search-restaurants-cbyh4tpkbi5k2x27arx725xx7y.us-east-1.es.amazonaws.com'
esClient = Elasticsearch(
    hosts=[{'host': host,'port':443}],
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    http_auth=('admin', 'Admin@12345')
    )
for index, row in df.iterrows():
    table.put_item(
        Item={
            'restaurantId' : row['restaurantId'], 
            'restaurantName' : row['restaurantName'],
            'cuisineType' : row['cuisineType'],
            'restaurantAddress' : row['restaurantAddress'], 
            'longitude' : row['Longitude'],
            'latitude' : row['Latitude'],
            'restaurantRating' : row['restaurantRating'],
            'reviewCount' : row['reviewCount'],
            'priceRange' : row['priceRange'],
            'insertedAtTimestamp': str(datetime.datetime.now())
           }
        )
    index_data = {
        'id': row['restaurantId'],
        'cuisine': row['cuisineType']
    }
    esClient.index(index="restaurants", 
             doc_type="Restaurant", 
             id=row['restaurantId'], 
             body=index_data, 
             refresh=True)