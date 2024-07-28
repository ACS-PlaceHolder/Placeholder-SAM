import boto3
import json
from decimal import Decimal
import os
import random
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

        body = json.loads(event['body'])
        required_fields = ['memberId', 'gu', 'course1', 'course2', 'course3', 'course4', 'course5']
        for field in required_fields:
            if field not in body:
                raise ValueError(f"Missing required field: {field}")

        memberId = body['memberId']
        gu = body['gu']
        course1 = body['course1']
        course2 = body['course2']
        course3 = body['course3']
        course4 = body['course4']
        course5 = body['course5']

        member_partition_key = f"MEMBER#{memberId}"
        member_sort_key = f"COURSE#{random.randint(100000, 999999)}"
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': f'Invalid request: {str(e)}'})
        }

    try:
        # MEMBER 항목 업데이트
        table.update_item(
            Key={
                'member_partition_key': member_partition_key,
                'member_sort_key': member_sort_key
            },
            UpdateExpression="set gu = :g, course1 = :c1, course2 = :c2, course3 = :c3, course4 = :c4, course5 = :c5, #n = :now",
            ExpressionAttributeValues={
                ':g': gu,
                ':c1': course1,
                ':c2': course2,
                ':c3': course3,
                ':c4': course4,
                ':c5': course5,
                ':now': "TRUE"
            },
            ExpressionAttributeNames={
                '#n': 'now'
            },
            ReturnValues="UPDATED_NEW"
        )

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Member courses updated successfully'}, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': 'Could not update member courses'})
        }
