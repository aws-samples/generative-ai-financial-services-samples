import re
import platform
import boto3
import base64
from io import BytesIO 
import json
from textractor import Textractor
from textractor.data.constants import TextractFeatures
import os
import pypdfium2 as pdfium

# Ensure that the Python version is compatible with the requirements
def validate_environment():
    assert platform.python_version() >= "3.10.6"


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
    }

def get_tag_text(text, tag_name):
    pattern = fr"<{tag_name}>(.*?)</{tag_name}>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return None

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
            "type": "text",
            "text": "Image " + str(i+1) + " :"
        })
        encoded_messages.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": img_base64_str
            }
        })
    return encoded_messages

def call_claude_3_model(messages, system_prompt, model_id):
    bedrock_rt = boto3.client("bedrock-runtime")
    body = {"messages": [{"role": "user", "content": messages}], 
            "system":system_prompt, 
            "max_tokens": 1000, 
            "temperature": 0, 
            "anthropic_version": "", 
            "top_k": 250, 
            "top_p": 1, 
            "stop_sequences": ["User"]}
    response = bedrock_rt.invoke_model(modelId=model_id, body=json.dumps(body))
    text_resp = json.loads(response['body'].read().decode('utf-8'))
    return text_resp['content'][0]['text']

def extract_answer_and_ground_truth(text_response):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"

    answer = get_tag_text(text_response, ANSWER_TAG)
    ground_truth = get_tag_text(text_response, GROUND_TRUTH_TAG)

    return answer, ground_truth

def prepare_claude_3_vision_prompt(query, encoded_images):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"
    QUESTION_TAG = "QUESTION"
    DATA_TAG = "DATA"

    encoded_messages = []

    encoded_messages.extend(encoded_images)

    encoded_messages.append({"type": "text", "text": f"""
                Below is the question: 
                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>
               
                Given the question provided within the <{QUESTION_TAG}> XML tag, please answer the question using the images provided as input. 
                """})

    system_prompt = f"""You are a document analysis specialist and expert forensic document examiner.
                Please answer the user question in the <{QUESTION_TAG}> XML tag, using the images provided as input. 
                Please give the answer formatted with markdown in the <{ANSWER_TAG}> XML tag. 
                Please make sure the uploaded images as input. 
                Then provide the key words of the answer in a <{GROUND_TRUTH_TAG}> XML tag. 
                If the data the question asks for is not in the DATA then say I don't know and give an explanation why. 
                Leave the ground truth empty if you don't know. 
                """

    return encoded_messages, system_prompt

def prepare_textract_prompt(query, text_data):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"
    QUESTION_TAG = "QUESTION"
    DATA_TAG = "DATA"

    prompt = f"""Below is the user question:
                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>

                Below is the data in text format:
                <{DATA_TAG}>
                {text_data}
                </{DATA_TAG}>

                Given the question provided within the <{QUESTION_TAG}> XML tag, please answer the question using the <{DATA_TAG}> XML tag.
                """

    system_prompt = f"""You are a document analysis specialist and expert forensic document examiner.
                Please answer the user question in the <{QUESTION_TAG}> XML tag.
                Please give the answer formatted with markdown in the <{ANSWER_TAG}> XML tag. 
                Then provide the key words of the answer in a <{GROUND_TRUTH_TAG}> XML tag. 
                If the data the question asks for is not in the DATA then say I don't know and give an explanation why. 
                Leave the ground truth empty if you don't know. 
                """

    return prompt, system_prompt

def prepare_claude_3_vision_and_textract_prompt(query, encoded_images, all_text):
    ANSWER_TAG = "ANSWER"
    GROUND_TRUTH_TAG = "GROUND"
    QUESTION_TAG = "QUESTION"
    TEXT_DATA_TAG = "TEXT_DATA"
    IMAGE_DATA_TAG = "IMAGE_DATA"

    encoded_messages = []

    encoded_messages.extend(encoded_images)

    encoded_messages.append({"type": "text", "text": f"""
                Below is the extracted text data: 
                <{TEXT_DATA_TAG}>
                {all_text}
                </{TEXT_DATA_TAG}>
                                
                Below is the question from our user: 
                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>

                Given the question provided within the <{QUESTION_TAG}> XML tag, please answer the question using the <{TEXT_DATA_TAG}> XML tag and the images provided.
                """})


    system_prompt = f"""You are a document analysis specialist and expert forensic document examiner.
                Please answer the user question in the <{QUESTION_TAG}> XML tag, using both the text data provided in the <{TEXT_DATA_TAG}> XML tag and the images provided as input. 
                Please give the answer formatted with markdown in the <{ANSWER_TAG}> XML tag. 
                Please make sure to use the combination of the text data input and the images to answer the question. 
                Then provide the key words of the answer in a <{GROUND_TRUTH_TAG}> XML tag. 
                If the data the question asks for is not in the DATA then say I don't know and give an explanation why. 
                Leave the ground truth empty if you don't know. 
                """
    print(encoded_messages)
    return encoded_messages, system_prompt

def search_and_answer_pdf(file_path, query, ocr_tool, model_id):
    all_text = create_or_retrieve_textract_file(file_path)
    assert ocr_tool in ["Claude 3 Vision (Experimental)", "Claude 3 Vision & Textract (Experimental)", "Textract"]
    if ocr_tool == "Claude 3 Vision (Experimental)":
        print("Passing images to Claude 3 Vision as OCR")
        encoded_images = encode_pdf_to_base64(file_path)
        prompt, system_prompt = prepare_claude_3_vision_prompt(query, encoded_images)
    elif ocr_tool == "Claude 3 Vision & Textract (Experimental)":
        print("Passing images to Claude 3 Vision as OCR and Textract as OCR")
        encoded_images = encode_pdf_to_base64(file_path)
        prompt, system_prompt = prepare_claude_3_vision_and_textract_prompt(query, encoded_images, all_text)
    elif ocr_tool == "Textract": 
        print("Passing images to Claude 3 using Textract as OCR")
        prompt, system_prompt = prepare_textract_prompt(query, all_text)
    else: 
        print("Not a valid OCR tool selection")
    response_text = call_claude_3_model(prompt, system_prompt, model_id)
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
