import json
import boto3
from boto3.dynamodb.conditions import Key

# DynamoDB 리소스 초기화
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('HOTPLACE')  # DynamoDB 테이블 이름 직접 설정

def query_parking_lots_by_gu(gu: str) -> list:
    response = table.query(
        KeyConditionExpression=Key('hotplace_partition_key').eq(gu) & Key('hotplace_sort_key').begins_with('Parkinglot#')
    )
    
    parking_lots = response.get('Items', [])
    for lot in parking_lots:
        lot['capacity'] = str(int(float(lot['capacity'])))
        lot['curParking'] = str(int(float(lot['curParking'])))
    
    return parking_lots

def handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
    }
    
    query_params = event.get('queryStringParameters', {})
    gu = query_params.get('gu') if query_params else None
    
    if not gu:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps("Missing 'gu' parameter")
        }
    
    try:
        parking_lots = query_parking_lots_by_gu(gu)
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(parking_lots, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps(str(e))
        }