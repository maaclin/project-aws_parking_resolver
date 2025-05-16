import json
import boto3
import os
import requests
from datetime import datetime

# AWS clients
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

# Constants
ADMIN_EMAIL = "ysolom90@gmail.com"
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event, indent=2))

        # Required inputs
        text = event['text']
        s3_key = event['s3_key']
        s3_bucket = event['s3_bucket']

        # Step 1: Parse with Gemini
        ticket_data = parse_with_gemini(text)
        print("Gemini output:", ticket_data)

        # Step 2: Lookup driver
        driver = find_driver(ticket_data.get('licence_plate', ''))
        print("Driver:", driver)

        # Step 3: Store in DynamoDB
        ticket_id = store_ticket(ticket_data, driver, s3_bucket, s3_key)
        print("Stored ticket ID:", ticket_id)

        # Step 4: Send email to driver or fallback
        if driver and 'email' in driver:
            send_email(driver['email'], ticket_data, ticket_id, s3_bucket, s3_key)
        else:
            notify_admin_missing_driver(ticket_data, ticket_id, s3_bucket, s3_key)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Processed successfully", "ticket_id": ticket_id})
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# --- Gemini API Call ---
def parse_with_gemini(ocr_text):
    import re

    prompt = f"""Extract the following fields from this parking fine text and return JSON:
- licence_plate
- issue_date
- reference_number
- price (fine)
- location
- authority
- driver_name
- address

Text:
{ocr_text}
"""
    headers = {
        "Content-Type": "application/json"
    }

    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    response = requests.post(
        f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
        headers=headers,
        json=body
    )

    result = response.json()
    print("Gemini raw response:", result)

    try:
        raw_text = result['candidates'][0]['content']['parts'][0]['text']
        # Remove Markdown code block wrapper like ```json ... ```
        json_text = re.sub(r"^```json\n|\n```$", "", raw_text.strip())
        return json.loads(json_text)

    except Exception as e:
        print("Gemini parsing failed, using fallback:", str(e))
        return {
            "licence_plate": "UNKNOWN",
            "issue_date": "UNKNOWN",
            "reference_number": "UNKNOWN",
            "price": "UNKNOWN",
            "location": "UNKNOWN",
            "authority": "UNKNOWN",
            "driver_name": "UNKNOWN",
            "address": "UNKNOWN"
        }
# --- DynamoDB: Store Ticket ---
def store_ticket(data, driver, bucket, key):
    table = dynamodb.Table('Tickets')
    ticket_id = f"ticket_{int(datetime.now().timestamp())}"
    now = datetime.now().isoformat()

    item = {
        'ticket_id': ticket_id,
        'licence_plate': data.get('licence_plate', 'UNKNOWN'),
        'issue_date': data.get('issue_date', 'UNKNOWN'),
        'price': data.get('price', 'UNKNOWN'),
        'authority': data.get('authority', 'UNKNOWN'),
        'driver_name': driver.get('driver_name', 'UNKNOWN') if driver else 'UNKNOWN',
        'driver_email': driver.get('email', 'UNKNOWN') if driver else 'UNKNOWN',
        'image_path': f"s3://{bucket}/{key}",
        'status': 'PENDING',
        'created_at': now,
        'updated_at': now
    }

    table.put_item(Item=item)
    return ticket_id

# --- Driver Lookup ---
def find_driver(licence_plate):
    if not licence_plate:
        return None
    table = dynamodb.Table('Drivers')
    try:
        response = table.get_item(Key={'licence_plate': licence_plate})
        return response.get('Item')
    except Exception as e:
        print("Driver lookup error:", str(e))
        return None

# --- SES Email to Driver ---
def send_email(to_email, data, ticket_id, bucket, key):
    form_base = os.environ['PAYMENT_FORM_URL']
    form_url = f"{form_base}?ticketId={ticket_id}"
    image_url = f"https://{bucket}.s3.amazonaws.com/{key}"

    html = f"""
    <html><body>
    <h3>Parking Ticket Notice</h3>
    <p>Your vehicle <strong>{data.get('licence_plate', 'UNKNOWN')}</strong> has received a parking fine.</p>
    <p><strong>Issue Date:</strong> {data.get('issue_date')}<br>
       <strong>Reference:</strong> {data.get('reference_number')}<br>
       <strong>Price:</strong> {data.get('price')}<br>
       <strong>Authority:</strong> {data.get('authority')}</p>
    <p>Please <a href="{form_url}">upload proof of payment</a>.</p>
    <p><a href="{image_url}">Click here to view the original ticket</a></p>
    </body></html>
    """

    ses.send_email(
        Source=os.environ['EMAIL_FROM_ADDRESS'],
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': f"Ticket for Vehicle {data.get('licence_plate')}"},
            'Body': {'Html': {'Data': html}}
        }
    )

# --- Fallback Email to Admin ---
def notify_admin_missing_driver(data, ticket_id, bucket, key):
    image_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    html = f"""
    <html><body>
    <h3>⚠️ Ticket Processing Failed</h3>
    <p>No driver found for licence plate <strong>{data.get('licence_plate')}</strong>.</p>
    <p>Ticket ID: {ticket_id}<br>
       Issue Date: {data.get('issue_date')}<br>
       Reference: {data.get('reference_number')}<br>
       Price: {data.get('price')}</p>
    <p><a href="{image_url}">View the uploaded ticket</a></p>
    </body></html>
    """

    ses.send_email(
        Source=os.environ['EMAIL_FROM_ADDRESS'],
        Destination={'ToAddresses': [ADMIN_EMAIL]},
        Message={
            'Subject': {'Data': "Ticket Processing Failed – No Driver Found"},
            'Body': {'Html': {'Data': html}}
        }
    )
