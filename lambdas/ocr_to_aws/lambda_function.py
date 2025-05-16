import json
import base64
import boto3
import requests
import os

s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Step 1: Get bucket and key from event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        print(f"Processing file: {key} from bucket: {bucket}")

        # Step 2: Download image from S3 to /tmp/
        tmp_path = f"/tmp/{os.path.basename(key)}"
        s3_client.download_file(bucket, key, tmp_path)

        # Step 3: Read image and encode to base64
        with open(tmp_path, "rb") as f:
            image_bytes = f.read()
        encoded = base64.b64encode(image_bytes).decode("utf-8")

        # Step 4: Call Google Cloud Vision OCR
        response = requests.post(
            "https://us-central1-parking-ticket-ocr.cloudfunctions.net/extract_text",
            json={"image": encoded}
        )

        if response.status_code != 200:
            print("OCR API failed:", response.text)
            return {
                'statusCode': 500,
                'body': 'OCR API call failed'
            }

        extracted_text = response.json().get("text", "")
        print("OCR result:", extracted_text[:500])  # print first 500 chars

        # Step 5: Invoke the ProcessTicketOCR Lambda
        lambda_client.invoke(
            FunctionName='ProcessTicketOCR',
            InvocationType='Event',  # async
            Payload=json.dumps({
                'text': extracted_text,
                's3_key': key,
                's3_bucket': bucket
            }).encode('utf-8')
        )

        return {
            'statusCode': 200,
            'body': json.dumps("OCR + forwarding complete")
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

