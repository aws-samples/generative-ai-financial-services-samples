import json
import boto3
from botocore.exceptions import ClientError

def fetch_model_ids():
    # Initialize Bedrock client
    client = boto3.client('bedrock', region_name='us-west-2')    

    # List models
    res = client.list_foundation_models(
        byInferenceType='ON_DEMAND'
    )
    model_ids = res['modelSummaries']
    model_ids = [
        el['modelId'] for el in model_ids 
        if'claude-3' in el['modelId']
                 ]

    return model_ids

def invoke_bedrock(model_id, prompt):
    
    client = boto3.client('bedrock-runtime', region_name='us-west-2')    
    # Format the request payload using the model's native structure.
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100000,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }
    # Convert the native request to JSON.
    request = json.dumps(native_request)

    try:
        # Invoke the model with the request.
        response = client.invoke_model(modelId=model_id, body=request)

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)

    # Decode the response body.
    model_response = json.loads(response["body"].read())

    # Extract and print the response text.
    response_text = model_response["content"][0]["text"]
    
    return response_text