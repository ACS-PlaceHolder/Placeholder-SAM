import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
member_table = dynamodb.Table('MEMBER')
hotplace_table = dynamodb.Table('HOTPLACE')

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

def convert_to_list(data):
    if isinstance(data, set):
        return list(data)
    return data

def handler(event, context):
    try:
        headers = {
           'Access-Control-Allow-Origin': '*',
           'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
           'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
        }


        query_params = event.get('queryStringParameters', {})
        memberId = query_params.get('memberId')
    except KeyError:
        return json.dumps({'message': 'Invalid request, missing path parameter memberId'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)

    try:
        response = member_table.query(
            KeyConditionExpression=Key('member_partition_key').eq(f'MEMBER#{memberId}') & Key('member_sort_key').begins_with('COURSE#')
        )
        items = response.get('Items', [])
        
        if not items:
            return json.dumps({'message': 'Member not found'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)

        member_details = []
        for item in items:
            gu = item['gu']
            courses = [item.get(f'course{i}') for i in range(1, 6)]
            course_details = []
            for course in courses:
                if course:
                    details = get_hotplace_details(gu, course)
                    if details:
                        course_details.append({
                            'hotplacePartitionKey': details.get('hotplace_partition_key'),
                            'hotplaceSortKey': details.get('hotplace_sort_key'),
                            'name': details.get('name'),
                            'areaCd': details.get('area_cd'),
                            'mapX': details.get('mapx'),
                            'mapY': details.get('mapy'),
                            'category': details.get('category_group_name'),
                            'address': details.get('address_name'),
                            'rating': details.get('rating'),
                            'imageUrl': details.get('imageurl'),
                            'placeUrl': details.get('placeurl'),
                            'menus': details.get('menu', []),
                            'keywords': details.get('keyword', [])
                        })
            member_details.append(course_details)

        return {
            'statusCode': 200,
            'headers': headers, 
            'body' : json.dumps(member_details, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return json.dumps({'message': 'Could not retrieve Member'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)
