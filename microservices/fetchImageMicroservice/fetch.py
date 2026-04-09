import json
import boto3
import os
import logging
from decimal import Decimal

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert decimal instances to floats
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    images_data = []

    # Log the start of the function
    logger.info("Function started. Event: %s", json.dumps(event))

    try:
        # List S3 objects in the 'images/uploads' prefix
        objects = s3_client.list_objects_v2(Bucket=os.environ['WEBSITE_ASSETS_BUCKET'], Prefix='images/uploads')
        logger.info("S3 objects listed successfully.")

        # DynamoDB table
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

        # Iterate over images, fetch metadata
        for obj in objects.get('Contents', []):
            image_key = obj['Key']
            logger.info("Processing image: %s", image_key)

            # Generate a presigned URL for the image
            presigned_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': os.environ['WEBSITE_ASSETS_BUCKET'], 'Key': image_key}, ExpiresIn=3600)
            logger.info("Generated presigned URL for image.")

            dynamodb_key = 'uploads/' + image_key.split('/')[-1]

            # Fetch DynamoDB metadata
            response = table.get_item(Key={'ImageKey': dynamodb_key})
            logger.info("Fetched DynamoDB metadata for image key: %s", dynamodb_key)

            # Initialize ai_description with a default value
            ai_description = 'No description available'

            # Check if 'Item' key exists in the response
            if 'Item' in response:
                item = response['Item']

                # Handle AI_Description as a plain string
                ai_description = item.get('AI_Description', 'No description available')

            images_data.append({'url': presigned_url, 'description': ai_description})
    except Exception as e:
        logger.error("An error occurred: %s", str(e))
        raise e

    # Log the successful completion of the function
    logger.info("Function completed successfully.")

    # Use DecimalEncoder to handle Decimal types in the response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(images_data, cls=DecimalEncoder)
    }
