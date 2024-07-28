import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MEMBER')  # DynamoDB 테이블 이름 직접 설정

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
        memberId = query_params.get('memberId')

    except KeyError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': 'Invalid request, missing path parameter gu'})
        }

    try:
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

        item = items[0]
        if 'mapx' in item:
            item['mapx'] = str(item['mapx'])
        if 'mapy' in item:
            item['mapy'] = str(item['mapy'])

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(item, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Could not retrieve member'})
        }
