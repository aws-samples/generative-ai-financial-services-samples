import re
import platform
import boto3
from botocore.config import Config
from langchain.chains.question_answering import load_qa_chain
from langchain_community.docstore import InMemoryDocstore
from langchain.vectorstores.opensearch_vector_search import OpenSearchVectorSearch
from langchain_handler.langchain_bedrock_wrappers import BedrockCached
import base64
from io import BytesIO 
import json
from textractor import Textractor
from textractor.data.constants import TextractFeatures
from textractor.data.text_linearization_config import TextLinearizationConfig
import os
import pypdfium2 as pdfium

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

def get_tag_text(text, tag_name):
    pattern = fr"<{tag_name}>(.*?)</{tag_name}>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return None

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

def create_or_retrieve_textract_file(file_path): 
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

        document = extractor.start_document_analysis(
            file_source=file_path, 
            features=[TextractFeatures.LAYOUT, TextractFeatures.TABLES],
            s3_upload_path=f"s3://{bucket_name}/genai-demo/textract_pdfs",
            save_image=f'./textract-processed/{file_path}'
        )

        all_text = document.get_text()  # Replace double newlines with single newline
        all_text = ' '.join(all_text.split())  # Remove extra whitespace

        # Upload the all_text to a text file in S3
        s3.put_object(
            Body=all_text.encode('utf-8'),
            Bucket=bucket_name,
            Key=f"genai-demo/{txt_file_key}",
        )

    return all_text

# Function to perform search and answer using the pdfs loaded into memory
# as base64 encodings of the pdfs -> images then sent to claude 3 directly
def search_and_answer_claude_3_direct(file_path, query):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"
    QUESTION_TAG = "QUESTION"
    DATA_TAG = "DATA"

    pdf = pdfium.PdfDocument(file_path)
    images = []
    for page_index in range(len(pdf)):
        page = pdf[page_index]
        bitmap = page.render()
        images.append(bitmap)
    encoded_messages = []
    for i in range(len(images)):
        buffered = BytesIO()
        pil_image = images[i].to_pil()
        pil_image.save(buffered, format='PNG')
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

        #get the text from the s3 bucket
        all_text = create_or_retrieve_textract_file(file_path)
        
        # append the question to the beginning 
        encoded_messages.insert(0, {"type": "text", "text": f"""You are a data entry specialist and expert forensic document examiner.
                Please answer the use question in the <{QUESTION_TAG}> XML tag, using only information in the data below. 
                Please give the answer formatted with markdownin in the <{ANSWER_TAG}> XML tag. Then provide the key words of the answer in a <{GROUND_TRUTH_TAG}> XML tag. 
                If the data the question asks for is not in the DATA then say I don't know and give an explanation why. Leave the ground truth empty if you don't know. 

                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>

                <{DATA_TAG}>
                """})
        
        #append closing tags to the data
        encoded_messages.append({"type": "text", "text": f"</{DATA_TAG}>"})

    messages = [{"role": "user", "content": encoded_messages}]

    bedrock_rt = boto3.client("bedrock-runtime")
    body = {"messages": messages, "max_tokens": 1000, "temperature": 0, "anthropic_version":"", "top_k": 250, "top_p": 1, "stop_sequences": ["User"]}
    response = bedrock_rt.invoke_model(modelId="anthropic.claude-3-sonnet-20240229-v1:0", body=json.dumps(body))
    text_resp = json.loads(response['body'].read().decode('utf-8'))
    full_string_text_response = text_resp['content'][0]['text']

    # get the answer from the response
    answer = get_tag_text(full_string_text_response, ANSWER_TAG)

    #get the ground truth from the response
    ground_truth = get_tag_text(full_string_text_response, GROUND_TRUTH_TAG)

    return answer, ground_truth, all_text

def search_and_answer_textract(file_path, query):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"
    QUESTION_TAG = "QUESTION"
    DATA_TAG = "DATA"
    
    all_text = create_or_retrieve_textract_file(file_path)

    # Prepare the input for Bedrock runtime
    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": f"""You are a data entry specialist and expert forensic document examiner.
                Please answer the use question in the <{QUESTION_TAG}> XML tag, using only information in the data below. 
                Please give the answer formatted with markdown in the <{ANSWER_TAG}> XML tag. Then provide the key words of the answer in a <{GROUND_TRUTH_TAG}> XML tag. 
                If the data the question asks for is not in the data tag then say I don't know and give an explanation why. Leave the ground truth empty if you don't know. 

                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>

                <{DATA_TAG}>
                {all_text}
                </{DATA_TAG}>
                """}]}
    ]

    # Send the input to Bedrock runtime
    bedrock_rt = boto3.client("bedrock-runtime")
    body = {"messages": messages, "max_tokens": 1000, "temperature": 0, "anthropic_version":"", "top_k": 250, "top_p": 1, "stop_sequences": ["User"]}
    response = bedrock_rt.invoke_model(modelId="anthropic.claude-3-sonnet-20240229-v1:0", body=json.dumps(body))
    text_resp = json.loads(response['body'].read().decode('utf-8'))
    full_string_text_response = text_resp['content'][0]['text']

    # get the answer from the response
    answer = get_tag_text(full_string_text_response, ANSWER_TAG)

    #get the ground truth from the response
    ground_truth = get_tag_text(full_string_text_response, GROUND_TRUTH_TAG)

    return answer, ground_truth, all_text