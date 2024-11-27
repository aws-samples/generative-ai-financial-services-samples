import re
import platform
import boto3
from io import BytesIO 
from utils.utils_os import read_json
import textractcaller as tc
from textractprettyprinter.t_pretty_print import get_text_from_layout_json
import os
import pypdfium2 as pdfium
import nltk
nltk.download('stopwords')

# Ensure that the Python version is compatible with the requirements
def validate_environment():
    assert platform.python_version() >= "3.10.6"


# Function to get configurations for different Bedrock models
def amazon_bedrock_models():
    return {
        "us.anthropic.claude-3-haiku-20240307-v1:0": {
            "temperature": 0.0,
            "topP": .999,
            "maxTokens": 4096,
            "inputTokenCost": 0.00025,
            "outputTokenCost": 0.00125
        },
        "us.anthropic.claude-3-5-haiku-20241022-v1:0": {
            "temperature": 0.0,
            "topP": .999,
            "maxTokens": 4096,
            "inputTokenCost": 0.001,
            "outputTokenCost": 0.005
        },
        "us.anthropic.claude-3-sonnet-20240229-v1:0": {
            "temperature": 0.0,
            "topP": .999,
            "maxTokens": 4096,
            "inputTokenCost": 0.003,
            "outputTokenCost": 0.015
        },      
        "us.anthropic.claude-3-5-sonnet-20240620-v1:0": {
            "temperature": 0.0,
            "topP": .999,
            "maxTokens": 4096,
            "inputTokenCost": 0.003,
            "outputTokenCost": 0.015
        },
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0": {
            "temperature": 0.0,
            "topP": .999,
            "maxTokens": 4096,
            "inputTokenCost": 0.003,
            "outputTokenCost": 0.015
        }
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
        encoded_messages.append({
            "text": "Image " + str(i+1) + " :"
        })
        encoded_messages.append({
            "image": {
                "format": "png",
                "source": {
                            "bytes": img_byte
                        }
            }
        })
    return encoded_messages

def call_claude_3_model(prompt, system_prompt, model_id, tool_config=None):
    bedrock_rt = boto3.client("bedrock-runtime")
    inference_config = {"maxTokens": 4096, "temperature": 0, "topP": 1}
    params = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": prompt}], 
        "inferenceConfig": inference_config
        }
    if system_prompt:
        params["system"] = [{"text": system_prompt}]
    
    if tool_config:
        params["toolConfig"] = tool_config
    response = bedrock_rt.converse(**params)
    # Token Usage
    token_usage = response['usage']
    content = response['output']['message']['content'][0]
    # Detect Tool Use
    if response["stopReason"] == "tool_use":
        response_text = content['toolUse']['input']
    else:
        response_text = content["text"]

    return response_text, token_usage

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

    encoded_messages.append({"text": f"""
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

    prompt = [
        {
            "text": f"""Below is the user question:
                <{QUESTION_TAG}>
                {query}
                </{QUESTION_TAG}>

                Below is the data in text format:
                <{DATA_TAG}>
                {text_data}
                </{DATA_TAG}>

                Given the question provided within the <{QUESTION_TAG}> XML tag, please answer the question using the <{DATA_TAG}> XML tag.
                """
        }
    ]

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

    encoded_messages.append({"text": f"""
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

def run_tool_use(tool_config, all_text, query, model_id):
    prompt, system_prompt = prepare_textract_prompt(query, all_text)
    response_text, _ = call_claude_3_model(prompt, system_prompt, model_id, tool_config)
    return response_text

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
    
    response_text, token_usage = call_claude_3_model(prompt, system_prompt, model_id)
    answer, ground_truth = extract_answer_and_ground_truth(response_text)
    return answer, ground_truth, all_text, token_usage

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
    features = [
        tc.Textract_Features.LAYOUT,
        tc.Textract_Features.TABLES
    ]
    textract_json = tc.call_textract(
        input_document=f"s3://{bucket_name}/{os.path.basename(file_path)}",
        features=features
    )
    
    layout = get_text_from_layout_json(
        textract_json=textract_json,
        exclude_figure_text=True, # optional
        exclude_page_header=False, # optional
        exclude_page_footer=True, # optional
        exclude_page_number=True, # optional
        generate_markdown=True  # optional
        # save_txt_path="s3://<your-bucket-name") # optional
    )
    all_text = "".join([f"\n\n ======================= PAGE NUMBER: {idx} =======================\n\n{page.strip()}" for idx, page in layout.items()])

    return all_text

def upload_pdf_to_s3(file_path, bucket_name, s3_key):
    s3 = boto3.client('s3')
    s3.upload_file(
        Filename=file_path,
        Bucket=bucket_name,
        Key=s3_key,
    )

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
        upload_pdf_to_s3(file_path, bucket_name, os.path.basename(file_path))
        all_text = process_pdf_with_textract(file_path, bucket_name)
        upload_text_to_s3(all_text, bucket_name, s3_key)

    return all_text
