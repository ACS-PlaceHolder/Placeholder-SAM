import boto3
import json
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import requests

dynamodb = boto3.resource('dynamodb')
member_table = dynamodb.Table('MEMBER')
hotplace_table = dynamodb.Table('HOTPLACE')
google_api_key = os.environ['GOOGLE_API_KEY']

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def get_hotplace_details(gu, course):
    response = hotplace_table.get_item(
        Key={
            'hotplace_partition_key': gu,
            'hotplace_sort_key': f'Place#{course}'
        }
    )
    return response.get('Item', None)

def get_congestion(gu, area_cd):
    response = hotplace_table.query(
        KeyConditionExpression=Key('hotplace_partition_key').eq(gu) & Key('hotplace_sort_key').begins_with(f'Hotplace#{area_cd}')
    )
    items = response.get('Items', [])
    if items:
        return items[0].get('congestion')
    return None

def get_duration(startX, startY, endX, endY):
    api_url = f"https://maps.googleapis.com/maps/api/directions/json?origin={startY},{startX}&destination={endY},{endX}&mode=transit&key={google_api_key}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return None
    data = response.json()
    try:
        duration_text = data['routes'][0]['legs'][0]['duration']['text']
        duration_minutes = duration_text.split()[0]  
        return duration_minutes
    except (IndexError, KeyError):
        return None

def handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
    }

    try:
        query_params = event.get('queryStringParameters', {})
        memberId = query_params.get('memberId')
        if not memberId:
            raise ValueError("Missing required query parameter: memberId")
    except (KeyError, ValueError) as e:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': f'Invalid request, missing parameter: {str(e)}'})
        }

    try:
        response = member_table.query(
            KeyConditionExpression=Key('member_partition_key').eq(f'MEMBER#{memberId}') & Key('member_sort_key').begins_with(f'COURSE#'),
            FilterExpression=Attr('now').eq('TRUE')
        )
        items = response.get('Items', [])
        
        if not items:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'message': 'Member not found'})
            }

        member_info = member_table.get_item(
            Key={
                'member_partition_key': f'MEMBER#{memberId}',
                'member_sort_key': f'INFO#{memberId}'
            }
        ).get('Item', {})

        startX = member_info.get('mapx')
        startY = member_info.get('mapy')
        
        course_details = []
        for item in items:
            gu = item['gu']
            courses = [item.get(f'course{i}') for i in range(1, 6)]
            for course in courses:
                if course:
                    details = get_hotplace_details(gu, course)
                    if details:
                        endX = details.get('mapx')
                        endY = details.get('mapy')
                        time = get_duration(startX, startY, endX, endY)
                        congestion = get_congestion(gu, details.get('area_cd'))
                        course_details.append({
                            'name': details.get('name'),
                            'id': details.get('hotplace_sort_key').split('#')[1],
                            'category': details.get('category_group_name'),
                            'address': details.get('address_name'),
                            'budget': details.get('rating'),
                            'congestion': congestion,
                            'mapX': endX,
                            'mapY': endY,
                            'imageUrl': details.get('imageurl'),
                            'time': time
                        })
                        startX, startY = endX, endY

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(course_details, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Could not retrieve Member'})
        }
