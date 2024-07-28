import boto3
import json
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
member_table = dynamodb.Table('MEMBER')

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
        return json.dumps({'message': 'Invalid request, missing path parameter memberId'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)

    try:
        # 'now' 속성이 'TRUE'인 아이템을 찾기 위한 쿼리
        response = member_table.query(
            KeyConditionExpression=Key('member_partition_key').eq(f'MEMBER#{memberId}') & Key('member_sort_key').begins_with(f'COURSE#'),
            FilterExpression=Attr('now').eq('TRUE')
        )
        items = response.get('Items', [])
        
        if not items:
            return json.dumps({'message': 'No items found with now=TRUE'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)

        # 각 아이템의 'now' 속성을 'FALSE'로 업데이트
        for item in items:
            member_table.update_item(
                Key={
                    'member_partition_key': item['member_partition_key'],
                    'member_sort_key': item['member_sort_key']
                },
                UpdateExpression="SET #now = :new_val",
                ExpressionAttributeNames={
                    '#now': 'now'
                },
                ExpressionAttributeValues={
                    ':new_val': 'FALSE'
                }
            )

        return {
            'statusCode': 200,
            'headers': headers,  
            'body' : json.dumps({'message': 'Updated items successfully'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return json.dumps({'message': 'Could not retrieve Member'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)
