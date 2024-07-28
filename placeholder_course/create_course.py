import json
import boto3
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import requests
from io import StringIO

# 오레곤 리전의 Bedrock 클라이언트 생성
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')
s3 = boto3.client('s3')
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

def generate_message(bedrock_runtime, model_id, system_prompt, messages, max_tokens, temperature=0.3):
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
            "temperature": temperature
        })
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=body,
        )
        
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        return response_body
    except Exception as e:
        raise RuntimeError(f"Failed to invoke model: {str(e)}")

def handler(event, context):
    try:
        headers = {
           'Access-Control-Allow-Origin': '*',
           'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
           'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
        }

        # event['body']를 JSON 객체로 변환
        body = json.loads(event['body'])
        
        required_fields = ['memberId', 'gu', 'parameter1', 'parameter2', 'parameter3']
        for field in required_fields:
            if field not in body:
                raise ValueError(f"Missing required field: {field}")
        
        memberId = body['memberId']
        gu = body['gu']
        keyword1, keyword2, keyword3 = body['parameter1'], body['parameter2'], body['parameter3']
        
        # JSON 파일 가져오기
        json_file = s3.get_object(Bucket='place-data-for-recording', Key=f'refine_json_for_bedrock/today/places_{gu}.json')
        json_content = json_file['Body'].read().decode('utf-8')
        
        # JSON 파일을 데이터로 변환
        data = json.loads(json_content)
        
        # 프롬프트에 포함할 장소 정보 추출
        place_info = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 모델 호출을 위한 프롬프트 생성
        prompt = (
            f"다음은 장소에 대한 전체 데이터입니다:\n{place_info}\n"
            "첫째, 혼잡도 점수 기준에 따라 각 장소에 점수를 매기세요. \n"
            "혼잡도 점수 기준:\n 혼잡도 '여유'는 10점을 추가하고, '보통'은 20점을 추가하며, '약간 붐빔'은 30점을 추가하고, '붐빔'은 40점을 추가합니다. 그런 다음 1000 min_pop 수마다 0.1점을 추가합니다. 그 후 평점에서 5.0을 뺀 결과를 더합니다. \n"
            "예시 계산 결과:\n id 1 12:00 - 0.0 점, id 1 15:00 - 0.0 점, id 1 18:00 - 0.0 점, id 2 12:00 - 0.0 점, id 2 15:00 - 0.0 점, ... . \n"
            "둘째, 이 계산 결과를 바탕으로 혼잡도 점수가 전반적으로 낮은 코스를 추천하세요. 코스는 3개의 장소로 구성됩니다.\n"
            f"코스 1: 혼잡도 점수가 전반적으로 낮은 {keyword1} 코스\n"
            f"코스 2: 혼잡도 점수가 전반적으로 낮은 {keyword2} 코스\n"
            f"코스 3: 혼잡도 점수가 전반적으로 낮은 {keyword3} 코스\n"
            "코스에서 장소의 순서는 각 장소의 혼잡도 점수가 가장 낮은 시간을 고려하여 결정됩니다.\n"
            "셋째, 지정된 응답 형식으로만 응답하세요.\n"
            f'convert_to_csv/today/places_{gu}.csv' "이 csv 파일에 있는 id로만으로 코스를 만들어야 합니다."
            "keyword가 다이어트 실패 하기 좋은 이면 category_group_name이 음식점인 것을 무조건 2개는 포함하고 나머지 카테고리 중 한개를 포함합니다.\n"
            "keyword가 대화하기 좋은 이면 category_group_name이 음식점과 카페를 무조건 각각 한개씩은 포함합니다.\n"
            "keyword가 SNS 자랑하기 좋은 이면 category_group_name이 카페와 놀거리를 무조건 한개씩은 포함합니다.\n"
            "keyword가 땡땡이 치기 좋은 이면 category_group_name이 음식점,카페,놀거리를 각각 하나씩 포함합니다.\n"
            f"응답 형식: {{\"courses\": {{\"{keyword1}\": [\"id\", \"id\", \"id\"], \"{keyword2}\": [\"id\", \"id\", \"id\"], \"{keyword3}\": [\"id\", \"id\", \"id\"]}}}}\n"
            "중요: 지정된 형식으로만 응답을 제공하고 추가 정보나 설명을 포함하지 마세요.\n"
            "id값을 정확히 리턴해야 합니다. 없는 값을 만들면 안됩니다. 위의 응답형식을 그대로 따르세요.\n"
        )
        
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        system_prompt = "You are a manager who plans appointment schedules for a day. Create an itinerary tailored to specific keywords using information about a given location."
        
        # 메시지 생성 후 모델 호출
        messages = [{"role": "user", "content": prompt}]
        response_body = generate_message(bedrock_runtime, model_id, system_prompt, messages, max_tokens=1024, temperature=0.3)
        
        # 응답 추출
        course_response = response_body.get('content', {})
        course_text = course_response if course_response else {}
        if course_response:
            for item in course_response:
                if item.get('type') == 'text':
                    course_text = item.get('text', '')
                    break
        
        # Bedrock에서 반환된 코스를 파싱하여 각 키워드에 따른 리스트로 변환
        courses = json.loads(course_text).get('courses', {})
        
        course_details = []
        for keyword, course_ids in courses.items():
            member_info = member_table.get_item(
                Key={
                    'member_partition_key': f'MEMBER#{memberId}',
                    'member_sort_key': f'INFO#{memberId}'
                }
            ).get('Item', {})
            
            startX = member_info.get('mapx')
            startY = member_info.get('mapy')
            
            details_list = []
            for course_id in course_ids:
                details = get_hotplace_details(gu, course_id)
                if details:
                    endX = details.get('mapx')
                    endY = details.get('mapy')
                    time = get_duration(startX, startY, endX, endY)
                    congestion = get_congestion(gu, details.get('area_cd'))
                    details_list.append({
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
            course_details.append(details_list)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(course_details, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }

    except ValueError as ve:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': str(ve)}, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except RuntimeError as re:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(re)}, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f"Unexpected error: {str(e)}"}, cls=DecimalEncoder, ensure_ascii=False, indent=4)
        }
