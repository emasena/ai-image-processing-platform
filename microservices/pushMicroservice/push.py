from PIL import Image, ImageOps
import io
import boto3
import os
from datetime import datetime

# Initialize AWS SDK clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Environment variables
    upload_bucket = os.environ['UPLOAD_BUCKET']
    assets_bucket = os.environ['WEBSITE_ASSETS_BUCKET']
    table_name = os.environ['DYNAMODB_TABLE']

    for record in event['Records']:
        source_key = record['s3']['object']['key']
        source_bucket = record['s3']['bucket']['name']

        if source_bucket != upload_bucket:
            print(f"Event from unexpected bucket: {source_bucket}, expected: {upload_bucket}")
            continue

        # Download the image from S3
        image_obj = s3_client.get_object(Bucket=source_bucket, Key=source_key)
        image = Image.open(image_obj['Body'])

        # Resize the image if it exceeds the size limit
        if image_obj['ContentLength'] > 4.5 * 1024 * 1024:  # If image is larger than 4.5 MB
            print(f"Resizing image {source_key} as it exceeds the size limit.")
            image = resize_image(image)

        buffer = io.BytesIO()
        image_format = image.format if image.format else 'JPEG'  # Default to JPEG if format is not available
        image.save(buffer, format=image_format)
        image_bytes = buffer.getvalue()

        # Define the destination key in the website assets bucket
        destination_key = f'images/{source_key}'
        s3_client.put_object(Bucket=assets_bucket, Key=destination_key, Body=image_bytes)
        print(f'Image copied to {assets_bucket}/{destination_key}')

        # Update DynamoDB with image metadata
        table = dynamodb.Table(table_name)
        response = table.put_item(
            Item={
                'ImageKey': source_key,
                'AI_Description': 'AI description not yet generated',
                'UploadTime': datetime.utcnow().isoformat()
            }
        )
        print('DynamoDB updated:', response)

    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }

def resize_image(image, base_width=1024):
    """
    Resizes the image to a specified base width while maintaining the aspect ratio.
    """
    w_percent = (base_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    return image.resize((base_width, h_size), Image.Resampling.LANCZOS)

