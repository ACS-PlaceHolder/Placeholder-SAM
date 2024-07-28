import boto3
import json
from decimal import Decimal
import requests
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MEMBER')  # DynamoDB 테이블 이름 직접 설정

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def get_coordinates_from_kakao(address, kakao_key):
    api_url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}&analyze_type=exact"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"KakaoAK {kakao_key}"
    }

    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if not data['documents']:
        raise ValueError('Address not found')
    
    mapx = data['documents'][0]['x']
    mapy = data['documents'][0]['y']
    
    return mapx, mapy

def handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
    }
    
    try:
        query_params = event.get('queryStringParameters', {})
        memberId = query_params.get('memberId')
        address = query_params.get('address')

        kakao_key = os.environ['KAKAO_API_KEY']
        if not memberId or not address:
            raise ValueError("Missing required query parameters: memberId or address")
    except (KeyError, ValueError) as e:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': f'Invalid request, missing parameter: {str(e)}'})
        }

    try:
        # Kakao API를 사용하여 좌표 얻기
        mapx, mapy = get_coordinates_from_kakao(address, kakao_key)
    except (requests.RequestException, ValueError) as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': f'Error fetching coordinates: {str(e)}'})
        }

    try:
        # MEMBER 항목 조회
        response = table.query(
            KeyConditionExpression=Key('member_partition_key').eq("MEMBER#" + memberId) 
            & Key('member_sort_key').begins_with('INFO#' + memberId)
        )
        items = response.get('Items', [])
        if not items:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'message': 'Member not found'})
            }
        
        item = items[0]  # 첫 번째 항목 선택

        # mapX와 mapY 업데이트
        table.update_item(
            Key={
                'member_partition_key': item['member_partition_key'],
                'member_sort_key': item['member_sort_key']
            },
            UpdateExpression="set mapx = :x, mapy = :y",
            ExpressionAttributeValues={
                ':x': Decimal(mapx),
                ':y': Decimal(mapy)
            },
            ReturnValues="UPDATED_NEW"
        )

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'mapX': str(mapx),
                'mapY': str(mapy)
            }, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Could not update member location'})
        }
