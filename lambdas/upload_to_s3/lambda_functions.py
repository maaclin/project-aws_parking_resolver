import json
import base64
import boto3
import uuid

s3 = boto3.client('s3')

BUCKET_NAME = 'rental-ticket-uploads'  # Your S3 bucket name

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        image_base64 = body['image']
        image_bytes = base64.b64decode(image_base64)

        # Generate a unique filename
        filename = f"{uuid.uuid4()}.jpg"

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=image_bytes,
            ContentType='image/jpeg'
        )

        print(f"Uploaded {filename} to {BUCKET_NAME}")

        # Let S3 trigger OcrToAWS automatically
        return {
            'statusCode': 200,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({
                'message': 'Upload successful',
                'file_key': filename
            })
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({ 'error': str(e) })
        }

