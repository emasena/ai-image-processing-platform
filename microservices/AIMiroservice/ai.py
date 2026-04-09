import os
import json
import boto3
import base64

# Environment variables
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
IMAGE_BUCKET = os.environ['WEBSITE_ASSETS_BUCKET']

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    # Parse the JSON body from the event
    body = json.loads(event.get('body', '{}'))

    # Extract the imageId from the body
    image_id_with_query = body.get('imageId')
    print("Event:", event)
    print(f"Image ID with query: {image_id_with_query}")

    # Extract just the image ID part before any query parameters
    image_id = image_id_with_query.split('?')[0] if '?' in image_id_with_query else image_id_with_query
    print(f"Extracted Image ID: {image_id}")

    image_bytes = get_image(IMAGE_BUCKET, f"images/uploads/{image_id}")
    image_base64 = base64.b64encode(image_bytes).decode()
    print(f"Image base64 size: {len(image_base64)}")

    description = generate_summary(image_base64)
    print(f"Generated description: {description}")

    store_in_dynamodb(image_id, description)
    print("Stored in DynamoDB successfully.")

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'imageId': image_id, 'description': description})
    }


def get_image(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()


def generate_summary(image_base64):
    prompt = """
    Analyze the image provided and generate a concise, engaging description suitable for a general audience. 
    Start with an overview of the scene, followed by specific details about the main subjects and notable background elements. 
    Focus on the emotions displayed, any apparent activities, and significant objects. Use descriptive but straightforward language.
    Avoid technical terms and ensure the text is ready for display on a webpage. Here are two examples of ideal descriptions:

    Example 1: "A serene beach scene at sunset. The orange hues of the sky reflect on the calm waters, with a lone figure walking along the shore, leaving footprints in the soft sand."

    Example 2: "A bustling city street under the glow of neon signs. People navigate the crowded sidewalks, with a street musician in the foreground drawing an attentive audience."

    Now, provide a similar description for the following image:
    """


    print("Invoking Bedrock model")
    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "system": prompt,
                "messages": [{
                    "role": "user",
                    "content": [{
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    }]
                }]
            })
        )
        print("Response from Bedrock:", response)

        # Add this line to print the keys of the response
        print("Response keys:", response.keys())

        if 'body' in response and hasattr(response['body'], 'read'):
            try:
                # Wrap the reading of the body in a try-except block
                result = json.loads(response['body'].read().decode())
                print("Bedrock response:", result)
                return result  # Adjust based on the actual structure of the response
            except Exception as e:
                print(f"Error reading response body: {e}")
                return None
        else:
            print("Response body not found or cannot be read.")
            return None
    except Exception as e:
        print(f"An error occurred during Bedrock model invocation: {e}")
        return None
def store_in_dynamodb(image_id, description):
    table = dynamodb.Table(DYNAMODB_TABLE)
    dynamodb_key = f"uploads/{image_id}"  # Prefix the image ID with "uploads/"
    print(f"Storing in DynamoDB table {DYNAMODB_TABLE} for ImageKey {dynamodb_key}")
    try:
        response = table.put_item(
            Item={
                'ImageKey': dynamodb_key,  # Use the prefixed key
                'AI_Description': description  # Change 'Description' to 'AI_Description' to match your table's schema
            }
        )
        print(f"Successfully stored in DynamoDB. Response: {response}")
    except Exception as e:
        print(f"Error storing in DynamoDB: {e}")
        raise
