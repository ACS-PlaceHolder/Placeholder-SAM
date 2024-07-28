import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key

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
            KeyConditionExpression=Key('hotplace_partition_key').eq(hotplace_partition_key) & Key('hotplace_sort_key').begins_with('Hotplace#')
        )
        items = response.get('Items', [])
        if not items:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'message': 'Hotplace not found'})
            }

        transformed_items = [
            {
                'hotplacePartitionKey': item['hotplace_partition_key'],
                'hotplaceSortKey': item['hotplace_sort_key'],
                'congestion': item.get('congestion'),
                'kakaoname': item.get('kakaoname'),
                'mapx': item.get('mapx'),
                'name': item.get('name'),
                'mapy': item.get('mapy')
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
