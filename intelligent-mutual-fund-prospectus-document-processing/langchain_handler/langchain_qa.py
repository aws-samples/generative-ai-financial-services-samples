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

def get_llm(model_id):
    # Create a BedrockCached instance with model configurations
    llm = BedrockCached(
        model_id=model_id,
        client=amazon_bedrock_client(),
    )
    llm.model_kwargs = model_configs[model_id]
    llm.verbose = True
    return llm

def encode_pdf_to_base64(file_path):
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
            }
        })
    return encoded_messages

def prepare_claude_3_prompt(query, encoded_images):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"
    QUESTION_TAG = "QUESTION"
    DATA_TAG = "DATA"

    encoded_messages = []
    encoded_messages.insert(0, {"type": "text", "text": f"""You are a data entry specialist and expert forensic document examiner.
                Please answer the use question in the <{QUESTION_TAG}> XML tag, using only information in the data below. 
                Please give the answer formatted with markdown in the <{ANSWER_TAG}> XML tag. Then provide the key words of the answer in a <{GROUND_TRUTH_TAG}> XML tag. 
                If the data the question asks for is not in the DATA then say I don't know and give an explanation why. Leave the ground truth empty if you don't know. 

                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>

                <{DATA_TAG}>
                """})

    encoded_messages.extend(encoded_images)
    encoded_messages.append({"type": "text", "text": f"</{DATA_TAG}>"})

    return encoded_messages

def call_claude_3_model(messages, model_id):
    bedrock_rt = boto3.client("bedrock-runtime")
    body = {"messages": [{"role": "user", "content": messages}], "max_tokens": 1000, "temperature": 0, "anthropic_version": "", "top_k": 250, "top_p": 1, "stop_sequences": ["User"]}
    response = bedrock_rt.invoke_model(modelId=model_id, body=json.dumps(body))
    text_resp = json.loads(response['body'].read().decode('utf-8'))
    return text_resp['content'][0]['text']

def extract_answer_and_ground_truth(text_response):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"

    answer = get_tag_text(text_response, ANSWER_TAG)
    ground_truth = get_tag_text(text_response, GROUND_TRUTH_TAG)

    return answer, ground_truth

def prepare_textract_prompt(query, text_data):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"
    QUESTION_TAG = "QUESTION"
    DATA_TAG = "DATA"

    prompt = f"""You are a document analysis specialist and expert forensic document examiner.
                Please answer the use question in the <{QUESTION_TAG}> XML tag, using only information in the data below. 
                Please give the answer formatted with markdown in the <{ANSWER_TAG}> XML tag. Then provide the key words of the answer in a <{GROUND_TRUTH_TAG}> XML tag. 
                If the data the question asks for is not in the DATA then say I don't know and give an explanation why. Leave the ground truth empty if you don't know. 

                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>

                <{DATA_TAG}>
                {text_data}
                </{DATA_TAG}>
                """

    return prompt

def search_and_answer_pdf(file_path, query, ocr_tool, model_id):
    all_text = create_or_retrieve_textract_file(file_path)
    if ocr_tool == "Claude 3 Vision":
        print("Passing images to Claude 3 Vision as OCR")
        encoded_images = encode_pdf_to_base64(file_path)
        prompt = prepare_claude_3_prompt(query, encoded_images)
    else: 
        print("Passing images to Claude 3 using Textract as OCR")
        prompt = prepare_textract_prompt(query, all_text)
    response_text = call_claude_3_model(prompt, model_id)
    answer, ground_truth = extract_answer_and_ground_truth(response_text)

    return answer, ground_truth, all_text

def check_s3_for_text_file(bucket_name, s3_key):
    s3 = boto3.client('s3')
    try:
        s3.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except:
        return False

def download_text_file_from_s3(bucket_name, s3_key):
    s3 = boto3.client('s3')
    try:
        obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
        text_content = obj['Body'].read().decode('utf-8')
        return text_content
    except:
        return None

def process_pdf_with_textract(file_path, bucket_name):
    extractor = Textractor(profile_name="default")
    document = extractor.start_document_analysis(
        file_source=file_path,
        features=[TextractFeatures.LAYOUT, TextractFeatures.TABLES],
        s3_upload_path=f"s3://{bucket_name}/genai-demo/textract_pdfs",
        save_image=False
    )

    all_text = document.get_text()
    all_text = ' '.join(all_text.split())  # Remove extra whitespace

    return all_text

def upload_text_to_s3(text_content, bucket_name, s3_key):
    s3 = boto3.client('s3')
    s3.put_object(
        Body=text_content.encode('utf-8'),
        Bucket=bucket_name,
        Key=s3_key,
    )

def create_or_retrieve_textract_file(file_path):
    bucket_name = os.environ['BUCKET_NAME']
    s3_key = os.path.basename(file_path) + ".txt"

    if check_s3_for_text_file(bucket_name, s3_key):
        print(f"Text file {s3_key} already exists in bucket {bucket_name}. Downloading and using as context.")
        all_text = download_text_file_from_s3(bucket_name, s3_key)
    else:
        print(f"Text file {s3_key} does not exist in bucket {bucket_name}. Processing and uploading.")
        all_text = process_pdf_with_textract(file_path, bucket_name)
        upload_text_to_s3(all_text, bucket_name, s3_key)

    return all_text
