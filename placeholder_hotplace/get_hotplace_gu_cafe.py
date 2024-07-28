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
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
    }

    try:
        query_params = event.get('queryStringParameters', {})
        hotplace_partition_key = query_params.get('gu')
        if not hotplace_partition_key:
            raise ValueError("Missing required query parameter: gu")
    except (KeyError, ValueError) as e:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': str(e)})
        }

    try:
        response = table.query(
            KeyConditionExpression=Key('hotplace_partition_key').eq(hotplace_partition_key) & Key('hotplace_sort_key').begins_with('Place#'),
            FilterExpression=Attr('category_group_name').eq('카페')
        )
        items = response.get('Items', [])
        if not items:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'message': 'Hotplace not found'})
            }

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

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(transformed_items, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Could not retrieve hotplace'})
        }