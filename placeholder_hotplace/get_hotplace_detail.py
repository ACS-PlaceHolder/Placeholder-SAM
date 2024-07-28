import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('HOTPLACE')  # DynamoDB 테이블 이름 직접 설정

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def handler(event, context):
    try:
        headers = {
           'Access-Control-Allow-Origin': '*',
           'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
           'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
        }


        query_params = event.get('queryStringParameters', {})
        hotplace_partition_key = query_params.get('hotplacePartitionKey')
        hotplace_sort_key = query_params.get('hotplaceSortKey')

    except KeyError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': 'Invalid request, missing path parameter gu'})
        }

    try:
        response = table.query(
            KeyConditionExpression=Key('hotplace_partition_key').eq(hotplace_partition_key) 
            & Key('hotplace_sort_key').begins_with('Place#' +hotplace_sort_key)
        )
        items = response.get('Items', [])

        # 반환되는 항목의 키 값을 변경
        transformed_items = [
            {
                'hotplacePartitionKey': item.get('hotplace_partition_key'),
                'hotplaceSortKey': item.get('hotplace_sort_key'),
                'name': item.get('name'),
                'areaCd': item.get('area_cd'),
                'mapX': str(item.get('mapx', '')),
                'mapY': str(item.get('mapy', '')),
                'category': item.get('category_group_name'),
                'address': item.get('address_name'),
                'rating': str(item.get('rating', '')),
                'imageUrl': item.get('imageurl'),
                'placeUrl': item.get('placeurl'),
                'menus': item.get('menu', []),
                'keywords': item.get('keyword', [])
            }
            for item in items
        ]

        if not items:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'message': 'Hotplace not found'})
            }

        return {
            'statusCode': 200,  
            'headers': headers,
            'body' : json.dumps(transformed_items[0], cls=DecimalEncoder, ensure_ascii=False, indent=4) 
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Could not retrieve hotplace'})
        }
