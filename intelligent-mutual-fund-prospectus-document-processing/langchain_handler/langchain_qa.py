import re
import platform
import boto3
from botocore.config import Config
from langchain.chains.question_answering import load_qa_chain
from langchain_community.docstore import InMemoryDocstore
from langchain.vectorstores.opensearch_vector_search import OpenSearchVectorSearch
from langchain_handler.langchain_bedrock_wrappers import BedrockCached
import base64
from pdf2image import convert_from_path
from io import BytesIO 
import json
from textractor import Textractor
import os

# Ensure that the Python version is compatible with the requirements
def validate_environment():
    assert platform.python_version() >= "3.10.6"


# Function to create a Bedrock client for interacting with AWS services
def amazon_bedrock_client():
    config = Config(retries={"max_attempts": 8})

    # Return a Bedrock client session
    return boto3.Session().client(
        "bedrock-runtime",
        config=config,
    )


# Function to get configurations for different Bedrock models
def amazon_bedrock_models():
    return {
        "anthropic.claude-3-sonnet-20240229-v1:0": {
            "temperature": 0.0,
            "top_p": .999,
            "max_tokens": 2048,
            "stop_sequences": ["\n\nHuman"],
        },      
        "anthropic.claude-3-haiku-20240307-v1:0": {
            "temperature": 0.0,
            "top_p": .999,
            "max_tokens": 2048,
            "stop_sequences": ["\n\nHuman"],
        },
        "anthropic.claude-v2": {
            "temperature": 0.0,
            "max_tokens": 300,
            "stop_sequences": ["\n\nHuman"],
        },
        "anthropic.claude-instant-v1": {
            "temperature": 0.0,
            "max_tokens": 300,
            "stop_sequences": ["\n\nHuman"],
        },
        "amazon.titan-tg1-large": {"temperature": 0.0, "maxTokenCount": 300},
    }


# Function to create a cached Bedrock LLM instance
def amazon_bedrock_llm(model_id, verbose=False):
    model_configs = amazon_bedrock_models()
    assert model_id in model_configs

    # Create a BedrockCached instance with model configurations
    llm = BedrockCached(
        model_id=model_id,
        client=amazon_bedrock_client(),
    )
    llm.model_kwargs = model_configs[model_id]
    llm.verbose = True
    return llm

# Function to perform search and answer using the pdfs loaded into memory
# as base64 encodings of the pdfs -> images then sent to claude 3 directly
def search_and_answer_claude_3_direct(file_path, query, img_format="png"):
    images = convert_from_path(file_path, fmt=img_format)
    encoded_messages = []
    for i in range(len(images)):
        buffered = BytesIO()
        images[i].save(buffered, format=images[i].format)
        img_byte = buffered.getvalue()
        img_base64 = base64.b64encode(img_byte)
        img_base64_str = img_base64.decode('utf-8')
        encoded_messages.append({
        "type": "image", 
        "source": {
            "type": "base64",
            "media_type": "image/png", 
            "data": img_base64_str
        }})
        
        # append the question to the end
        encoded_messages.append({"type": "text", "text": f"""You are a data entry specialist and expert forensic document examiner.
            {query}
            For numeric data points, read each digit one at a time, and append each to the resulting data point string.
            If the writing in a form field is hard to read, or has corrections, or overflows onto the margin, then surround your answer for that data point with a <LOW CONFIDENCE> XML tag.
            Examine each handwritten digit very carefully, looking at the overall stroke pattern and shape. If the digit could be interpreted as two or more different numeric values, surround the data point that contains it with a <LOW_CONFIDENCE REASON:> XML tag and write the reason in the tag.
            Additionally, look at the format of the overall form, and if you see handwriting that is not neat or is not printed within the form boxes, surround your whole answer with a <LOW_CONFIDENCE REASON:> XML tag and write the reason in the tag."""})

    messages = [{"role": "user", "content": encoded_messages}]

    bedrock_rt = boto3.client("bedrock-runtime")
    body = {"messages": messages, "max_tokens": 1000, "temperature": 0, "anthropic_version":"", "top_k": 250, "top_p": 1, "stop_sequences": ["User"]}
    response = bedrock_rt.invoke_model(modelId="anthropic.claude-3-sonnet-20240229-v1:0", body=json.dumps(body))
    text_resp = json.loads(response['body'].read().decode('utf-8'))
    return text_resp['content'][0]['text']

def search_and_answer_textract(file_path, query):
    s3 = boto3.client('s3')
    extractor = Textractor(profile_name="default")
    # Read from os env var called BUCKET_NAME and put in a var called "bucket_name"
    
    bucket_name = os.environ['BUCKET_NAME']
    s3_key = os.path.basename(file_path)  # Get the file name from the file path
    txt_file_key = f"{s3_key}.txt"  # Text file name with the same base name as the input file

    # Check if the text file exists in the S3 bucket
    try:
        s3.head_object(Bucket=bucket_name, Key=f"genai-demo/{txt_file_key}")
        print(f"Text file {txt_file_key} already exists in bucket {bucket_name}. Downloading and using as context.")
        obj = s3.get_object(Bucket=bucket_name, Key=f"genai-demo/{txt_file_key}")
        all_text = obj['Body'].read().decode('utf-8')
    except:
        print(f"Text file {txt_file_key} does not exist in bucket {bucket_name}. Processing and uploading.")
        document = extractor.start_document_text_detection(
            file_path,
            s3_upload_path=f"s3://{bucket_name}/genai-demo/{s3_key}",
        )
        all_text = document.get_text().replace('\n\n', '\n')  # Replace double newlines with single newline
        all_text = ' '.join(all_text.split())  # Remove extra whitespace

        # Upload the all_text to a text file in S3
        s3.put_object(
            Body=all_text.encode('utf-8'),
            Bucket=bucket_name,
            Key=f"genai-demo/{txt_file_key}",
        )

    # Prepare the input for Bedrock runtime
    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": all_text}, 
            {"type": "text", "text": f"""You are a data entry specialist and expert forensic document examiner.
            {query}"""}]}
    ]

    # Send the input to Bedrock runtime
    bedrock_rt = boto3.client("bedrock-runtime")
    body = {"messages": messages, "max_tokens": 1000, "temperature": 0, "anthropic_version":"", "top_k": 250, "top_p": 1, "stop_sequences": ["User"]}
    response = bedrock_rt.invoke_model(modelId="anthropic.claude-3-sonnet-20240229-v1:0", body=json.dumps(body))
    text_resp = json.loads(response['body'].read().decode('utf-8'))

    return text_resp['content'][0]['text'], all_text