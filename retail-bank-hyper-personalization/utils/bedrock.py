import json
import boto3
from botocore.exceptions import ClientError

def fetch_model_ids():
    # Initialize Bedrock client
    client = boto3.client('bedrock', region_name='us-west-2')    

    # List models
    res = client.list_inference_profiles(
        maxResults=100,  # Maximum number of results to return
        typeEquals='SYSTEM_DEFINED'  # Filter by profile type (SYSTEM_DEFINED or APPLICATION)
    )
    profiles = res['inferenceProfileSummaries']  # List of inference profile summaries

    model_ids = [
        el['inferenceProfileId'] for el in profiles 
        if any(substring in el['inferenceProfileId'] for substring in ['claude-3-5', 'llama3-3-70b', 'nova'])
                    ]
    return model_ids

def invoke_bedrock(model_id, prompt):
    client = boto3.client('bedrock-runtime', region_name='us-west-2')
    
    # Create the request structure for the Converse API
    request = {
        'modelId': model_id,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {
                        'text': prompt
                    }
                ]
            }
        ],
        'inferenceConfig': {
            'maxTokens': 4096,
            'temperature': 0.5
        }
    }

    try:
        # Use the converse API to send the request
        response = client.converse(**request)
        
        # Extract the response text
        response_text = response['output']['message']['content'][0]['text']
        return response_text

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)