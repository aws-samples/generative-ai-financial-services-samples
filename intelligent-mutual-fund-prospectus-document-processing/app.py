import os
import pandas as pd
from pathlib import Path
from botocore.exceptions import ClientError
import streamlit as st
from utils.auth import Auth
import re
import json
import base64
from langchain_handler.langchain_qa import (
    search_and_answer_pdf,
    validate_environment,
    amazon_bedrock_models,
    run_tool_use
)
from utils.utils_text import (
    spans_of_tokens_ordered,
    spans_of_tokens_compact,
    spans_of_tokens_all,
    text_tokenizer,
)
from utils.utils_os import (
    read_yaml
)
import boto3
import io
from contextlib import closing


import time
import threading
from functools import wraps

def timeout_decorator(seconds=10):
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = []
            error = []
            
            def target():
                try:
                    result.append(func(*args, **kwargs))
                except Exception as e:
                    error.append(e)
            
            thread = threading.Thread(target=target)
            start_time = time.time()
            thread.start()
            thread.join(timeout=seconds)
            
            execution_time = time.time() - start_time
            print(f"Function '{func.__name__}' took {execution_time:.2f} seconds")
            
            if thread.is_alive():
                thread.join(timeout=0)  # Clean up the thread
                raise TimeoutError(f"Function execution timed out after {seconds} seconds")
            
            if error:
                raise error[0]
                
            return result[0] if result else None
            
        return wrapper
    return actual_decorator

# check if an env variable called BUCKET_NAME is existing
# if yes, continue, else error out and say "S3 Bucket must be set for Textract processing. Please see README for more information"
if "BUCKET_NAME" not in os.environ:
    raise Exception("S3 Bucket must be set for Textract processing. Please see README for more information")

if "SECRET_NAME" not in os.environ:
    raise Exception("Secret must be set for authentication in Cognito. Please see README for more information")

# Set page title
st.set_page_config(page_title="Q/A App", layout="wide")

# Initialise CognitoAuthenticator
authenticator = Auth.get_authenticator(os.environ['SECRET_NAME'])

# Authenticate user, and stop here if not logged in
is_logged_in = authenticator.login()
if not is_logged_in:
    st.stop()

def logout():
    # Set page title
    authenticator.logout()

def synthesize_speech(text, voice_id):
    polly_client = boto3.Session().client('polly')
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId=voice_id
    )

    stream = response.get('AudioStream')
    mp3_data = io.BytesIO()
    with closing(stream):
        mp3_data.write(stream.read())

    return mp3_data.getvalue()

comprehend = boto3.client('comprehend')

def analyze_sentiment(text):
    try:
        response = comprehend.detect_sentiment(Text=text, LanguageCode='en')
        sentiment = response['Sentiment']
        sentiment_score = response['SentimentScore']
        return sentiment, sentiment_score
    except Exception as e:
        print(f"Error: {e}")
        return None, None
    
def detect_pii_entities(text):
    try:
        response = comprehend.detect_pii_entities(Text=text, LanguageCode='en')
        entities = response.get('Entities', [])
        entity_texts = [
            f"- {entity['Type']}: {format_entity_text(entity, text)}"
            for entity in entities
        ]
        return entity_texts
    except ClientError as e:
        print(f"Error: {e}")
        return []
    
entity_colors = {
    'DEFAULT': {'color': '#e0e0e0', 'country': 'universal', 'emoji': '🌍'},
    'BANK_ACCOUNT_NUMBER': {'color': '#ff9999', 'country': 'US', 'emoji': '💳'},
    'CREDIT_DEBIT_NUMBER': {'color': '#ffcdd2', 'country': 'universal', 'emoji': '💳'},
    'ADDRESS': {'color': '#e0e0e0', 'country': 'universal', 'emoji': '🏠'},
    'AGE': {'color': '#f3e5f5', 'country': 'universal', 'emoji': '🕰️'},
    'AWS_ACCESS_KEY': {'color': '#b2dfdb', 'country': 'universal', 'emoji': '🔑'},
    'AWS_SECRET_KEY': {'color': '#b2dfdb', 'country': 'universal', 'emoji': '🔑'},
    'CREDIT_DEBIT_CVV': {'color': '#e1bee7', 'country': 'universal', 'emoji': '💳'},
    'CREDIT_DEBIT_EXPIRY': {'color': '#e1bee7', 'country': 'universal', 'emoji': '💳'},
    'DATE_TIME': {'color': '#c8e6c9', 'country': 'universal', 'emoji': '📅'},
    'DRIVER_ID': {'color': '#ffcdd2', 'country': 'universal', 'emoji': '🚗'},
    'EMAIL': {'color': '#b3e5fc', 'country': 'universal', 'emoji': '📧'},
    'INTERNATIONAL_BANK_ACCOUNT_NUMBER': {'color': '#ff9999', 'country': 'international', 'emoji': '💳'},
    'IP_ADDRESS': {'color': '#b2dfdb', 'country': 'universal', 'emoji': '🌐'},
    'LICENSE_PLATE': {'color': '#ffcdd2', 'country': 'universal', 'emoji': '🚗'},
    'MAC_ADDRESS': {'color': '#b2dfdb', 'country': 'universal', 'emoji': '🖥️'},
    'NAME': {'color': '#f3e5f5', 'country': 'universal', 'emoji': '👤'},
    'PASSWORD': {'color': '#e1bee7', 'country': 'universal', 'emoji': '🔒'},
    'PHONE': {'color': '#c8e6c9', 'country': 'universal', 'emoji': '📞'},
    'PIN': {'color': '#e1bee7', 'country': 'universal', 'emoji': '🔢'},
    'SWIFT_CODE': {'color': '#ff9999', 'country': 'universal', 'emoji': '💳'},
    'URL': {'color': '#b3e5fc', 'country': 'universal', 'emoji': '🌐'},
    'USERNAME': {'color': '#b3e5fc', 'country': 'universal', 'emoji': '👤'},
    'VEHICLE_IDENTIFICATION_NUMBER': {'color': '#ffcdd2', 'country': 'universal', 'emoji': '🚗'},
    'CA_HEALTH_NUMBER': {'color': '#ff9999', 'country': 'CA', 'emoji': '🏥'},
    'CA_SOCIAL_INSURANCE_NUMBER': {'color': '#ff9999', 'country': 'CA', 'emoji': '🏦'},
    'IN_AADHAAR': {'color': '#ff9999', 'country': 'IN', 'emoji': '🇮🇳'},
    'IN_NREGA': {'color': '#ff9999', 'country': 'IN', 'emoji': '🇮🇳'},
    'IN_PERMANENT_ACCOUNT_NUMBER': {'color': '#ff9999', 'country': 'IN', 'emoji': '🇮🇳'},
    'IN_VOTER_NUMBER': {'color': '#ff9999', 'country': 'IN', 'emoji': '🇮🇳'},
    'UK_NATIONAL_HEALTH_SERVICE_NUMBER': {'color': '#ff9999', 'country': 'UK', 'emoji': '🇬🇧'},
    'UK_NATIONAL_INSURANCE_NUMBER': {'color': '#ff9999', 'country': 'UK', 'emoji': '🇬🇧'},
    'UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER': {'color': '#ff9999', 'country': 'UK', 'emoji': '🇬🇧'},
    'BANK_ROUTING': {'color': '#ff9999', 'country': 'US', 'emoji': '💳'},
    'PASSPORT_NUMBER': {'color': '#ffcdd2', 'country': 'US', 'emoji': '🇺🇸'},
    'US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER': {'color': '#ff9999', 'country': 'US', 'emoji': '🇺🇸'},
    'SSN': {'color': '#ff9999', 'country': 'US', 'emoji': '🇺🇸'}
}

def format_entity_text(entity, text):
    entity_type = entity['Type']
    entity_text = text[entity['BeginOffset']:entity['EndOffset']]
    color = entity_colors[entity_type]['color']
    emoji = entity_colors[entity_type]['emoji']
    country = entity_colors[entity_type]['country']
    return f"<span style='background-color:{color};'>{country} - {emoji} - {entity_text}</span>"

# Remove whitespace from the top of the page and sidebar
st.write('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

# Set content to center
content_css = """
<style>
    .reportview-container .main .block-container{
        display: flex;
        justify-content: center;
    }
</style>
"""

# Inject CSS with Markdown
st.markdown(content_css, unsafe_allow_html=True)

# Define Streamlit cache decorators for various functions
# These decorators help in caching the output of functions to enhance performance
@st.cache_resource
def check_env():
    # Validate the environment for the langchain QA model
    validate_environment()
    
def list_model_providers():
    providers = {"Anthropic": {"provider": "anthropic", "model": "Claude 3"}, "Amazon Nova": {"provider": "amazon", "model": "Nova"}, "Meta": {"provider": "meta", "model": "Llama 3.2"}}
    return providers

@st.cache_data
def list_llm_models():
    models = list(amazon_bedrock_models().keys())
    return models

def clean_question(s):
    """Strip heading question number"""
    return re.sub(r"^[\d\.\s]+", "", s)

def markdown_bgcolor(text, bg_color):
    return f'<span style="background-color:{bg_color};">{text}</span>'

def markdown_fgcolor(text, fg_color):
    return f":{fg_color}[{text}]"

# Function to save the uploaded file
def save_uploaded_file(uploaded_file, upload_dir):
    try:
        # Get the file extension
        file_extension = os.path.splitext(uploaded_file.name)[1]
        
        # Check if the file is a PDF
        if file_extension.lower() == ".pdf":
            # Save the file to the specified directory
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"File '{uploaded_file.name}' uploaded successfully!")
        else:
            st.error("Only PDF files are allowed.")
    except Exception as e:
        st.error(f"Error uploading file: {e}")


def markdown_naive(text, tokens, bg_color=None):
    """
    The exact match of answer may not be the possible.
    Split the answer into tokens and find most compact span
    of the text containing all the tokens. Highlight them.
    """
    print("highlight tokens", tokens)

    for t in tokens:
        text = text.replace(t, markdown_bgcolor(t, bg_color))

    # Escaping markup characters
    text = text.replace("$", "\\$")
    return text

@timeout_decorator(seconds=10)
def markdown2(text, tokens, fg_color=None, bg_color=None):
    """
    The exact match of answer may not be the possible.
    Split the answer into tokens and find most compact span
    of the text containing all the tokens. Highlight them.
    """
    print("highlight tokens:", tokens)

    spans = []
    if len(tokens) < 20:  # OOM
        spans = spans_of_tokens_ordered(text, tokens)
        if not spans:
            spans = spans_of_tokens_compact(text, tokens)
            print("spans_of_tokens_compact:", spans)
    if not spans:
        spans = spans_of_tokens_all(text, tokens)
        print("spans_of_tokens_all:", spans)

    output, k = "", 0
    for i, j in spans:
        output += text[k:i]
        k = j
        if bg_color:
            output += markdown_bgcolor(text[i:j], bg_color)
        else:
            output += markdown_fgcolor(text[i:j], fg_color)
    output += text[k:]

    return output


def markdown_escape(text):
    """Escaping markup characters"""
    return re.sub(r"([\$\+\#\`\{\}])", "\\\1", text)

def get_file_list(document_repo_file_path):
    listdocs = os.listdir(document_repo_file_path)
    relative_paths = [os.path.join(document_repo_file_path, file) for file in listdocs]
    docs = [doc for doc in relative_paths if doc.endswith(".pdf") or doc.endswith(".xlsx")]

    return docs


def displayDoc(file):
    try:
        extension_file = Path(file).suffix
        file_format = extension_file.replace('.', '')
        
        # Opening file from file path
        with open(file, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode("utf-8")

        if file_format == "pdf":
            # Embedding PDF in HTML
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="850" type="application/pdf">'
            # Displaying File
            st.markdown(pdf_display, unsafe_allow_html=True)
        
        elif file_format == "xlsx":
            dataframe = pd.read_excel(file)
            st.write(dataframe)
            
    except Exception as e:
        st.error(f"Failed to display PDF: {e}")
        print(f"Failed to display PDF: {e}")  # For debugging in server logs

# The main function where the Streamlit app logic resides
def main():
    # Ensure the environment is set up correctly
    check_env()

    st.title("Intelligent Document Processing.")

    # Select a language model from the available options

    # Initialize session state variables
    if "modelProvider" not in st.session_state:
        st.session_state.modelProvider = None
    if "modelID" not in st.session_state:
        st.session_state.modelID = None
    if "claude3direct" not in st.session_state:
        st.session_state.claude3direct = False
    if "file_list" not in st.session_state:
        st.session_state.file_list = []

    
    col1, col2, col3, col4 = st.columns([1.8, 1.5, 1.8, 1.5])
    with col1: 
        model_providers = list_model_providers()
        model_provider = st.selectbox("Select Model Provider", list(model_providers.keys()))

        # Update session state variables
        st.session_state.modelProvider = model_provider
        
    compatible_models = [model for model in list_llm_models() if model_providers[st.session_state.modelProvider]['provider'] in model]
    
    with col2:
        # Select OCR Tool
        ocr_tools = ["Textract",f"{model_providers[st.session_state.modelProvider]['model']} Vision (Experimental)", f"{model_providers[st.session_state.modelProvider]['model']} Vision & Textract (Experimental)", "Converse API - DocumentBlock (Experimental)"]
        if (st.session_state.modelProvider == "Meta"):
            ocr_tools = [ocr_tools[0], ocr_tools[-1]]
        st.session_state.ocr_tool = st.selectbox("Select OCR Tool", ocr_tools)
        if (st.session_state.ocr_tool != "Textract") and (st.session_state.modelProvider == "Amazon Nova"):
            compatible_models.remove('us.amazon.nova-micro-v1:0')
        if (st.session_state.ocr_tool not in ["Textract", "Converse API - DocumentBlock (Experimental)"]) and (st.session_state.modelProvider == "Anthropic"):
            compatible_models.remove('us.anthropic.claude-3-5-haiku-20241022-v1:0')
    
    with col3: 
        model_id = st.selectbox("Select LLM", compatible_models)

        # Update session state variables
        st.session_state.modelID = model_id

    with col4: 
        demo_version = st.selectbox("Select Examples Version", ["Insurance Examples", "Mutual Fund Examples"])

        if demo_version == "Insurance Examples":
            document_repo_file_path = './docs/insurance/'
        elif demo_version == "Mutual Fund Examples":
            document_repo_file_path = './docs/mutual_fund/'
        
        data = read_yaml(document_repo_file_path + 'data.yaml')
        
        # Get questions
        questions = ["Ask your question"] + [row['prompt'] for row in data]
        questions = [f"{i}. {q}" for i, q in enumerate(questions)]
        
        
    col1, col2 = st.columns([1.5, 2.0])
    # Define doc_source_nm early on to ensure it's available when needed
    with col1:  # Right side - Only the full PDF display
        all_docs = get_file_list(document_repo_file_path)

        doc_path = st.selectbox("Select doc", all_docs, key="doc_selector", index=0)

        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'xlsx'])
        if uploaded_file is not None:
            save_uploaded_file(uploaded_file, upload_dir=document_repo_file_path)

        if doc_path.lower().endswith(".pdf") or doc_path.lower().endswith(".xlsx"):
            displayDoc(doc_path)
            

    with col2:  # Left side - All settings and displays except the full PDF
        # Select a language model from the available options
        with st.expander('Architecture Diagram', expanded=True): 
            if 'Vision (Experimental)' in st.session_state.ocr_tool:
                st.image("./assets/claude_3_vision_diagram.png", use_container_width=True)
            elif 'Vision & Textract (Experimental)' in st.session_state.ocr_tool:
                st.image("./assets/claude_3_vision_text_diagram.png", use_container_width=True)
            else: 
                st.image("./assets/textract_diagram.png", use_container_width=True)

        # Add a multiselect dropdown for Comprehend, Polly, and Textract
        selected_services = st.multiselect("Select Additional AI Services", ["Tool Use (Bedrock)", "Textract", "Comprehend", "Polly"])

        
        # Handling user input for the question
        question = st.selectbox("Select question", [""] + questions, )
        question = clean_question(question)

        # Allow user to input a custom question if needed
        if "Ask" in question:
            question = st.text_input(
                "Your Question: ", placeholder="Ask me anything ...", key="input"
            )

        # Early exit if no question is provided
        if not question:
            return

        # Construct the query by appending a trailer for concise answers
        query = question
        query = query.strip()

        # Display the formatted question
        st.write("**Question**")
        final_query = st.text_area(
            label="Preview",
            value=query,
            label_visibility="collapsed",
            height=500,
            disabled=False,
            max_chars=100000,
        )
        print("\n\nQ:", final_query)

        # code for processing the query and handling responses from Bedrock
        with st.expander("Amazon Bedrock", expanded=True):
            try:
                # Three attempts
                for _ in range(0, 3):
                    response, ground_truth, all_text, token_usage = search_and_answer_pdf(
                        file_path=doc_path,
                        query=final_query,
                        ocr_tool=st.session_state.ocr_tool, 
                        model_id=st.session_state.modelID,
                        )
                    break
            except Exception as e:
                ground_truth = ""
                all_text = ""
                token_usage = ""
                response = ""
                print(e)
            
            if response is None:
                response = ""
                print("BEDROCK RESPONSE WAS 'NONE'")
                
            print("BEDROCK RESPONSE:" + response)

            st.write(f"**Bedrock Response**: {response}")
            st.write("\n")
        
        # Display Pricing only when Bedrock returns a response
        if response:
            with st.expander("Amazon Bedrock Pricing", expanded=True):

                print("PRICING RESPONSE:", token_usage)
                
                input_token_cost = token_usage['inputTokens'] * amazon_bedrock_models()[st.session_state.modelID]['inputTokenCost'] / 1000
                output_token_cost = token_usage['outputTokens'] * amazon_bedrock_models()[st.session_state.modelID]['outputTokenCost'] / 1000
                cost = round(input_token_cost + output_token_cost, 5)

                st.write(f"**Cost**: ${cost}")
                st.write("\n")

        # Run Tool Use with Bedrock Response to keep consistency between the text response and the json format
        if "Tool Use (Bedrock)" in selected_services:
            with st.expander("Tool Use (Bedrock)", expanded=True):
                with st.spinner("Processing Query with Tool Use (Bedrock)"):
                    try:
                        tool_config = json.loads([row["toolConfig"] for row in data if row['prompt'] == question][0])
                        
                        if st.session_state.modelProvider in ["Amazon Nova", "Meta"]:
                            tool_config.pop('toolChoice', None)
                        
                        # Three attempts
                        for _ in range(0, 3):
                            tool_response = run_tool_use(
                                tool_config=tool_config,
                                all_text=response,
                                query=final_query,
                                model_id=st.session_state.modelID,
                            )
                            break
                    except IndexError as e:
                        tool_response = {"MESSAGE": "TOOL USE CANNOT BE USED FOR THIS QUESTION. PLEASE CREATE A NEW TOOL CONFIG FILE AND TRY AGAIN."}
                    except Exception as e:
                        tool_response = {}
                        print(e)
                
                if not isinstance(tool_response, dict):
                    print("TOOL USE RESPONSE IS NOT A VALID JSON FORMAT")
                    tool_response = {}

                print("TOOL USE RESPONSE:", tool_response)

                st.write(f"**Tool Use Response**:\n")
                st.json(tool_response)
                st.write("\n")

        if "Comprehend" in selected_services:
            print("Adding Comrehend analysis to response.")
            with st.expander("Amazon Comprehend", expanded=True):
                # Analyze sentiment of the question
                with st.spinner("Generating Question Sentiment with Amazon Comprehend"):
                    sentiment, sentiment_score = analyze_sentiment(final_query)

                # Display sentiment analysis results
                if sentiment is not None and sentiment_score is not None:
                    st.metric(label="Query Sentiment", value=sentiment, delta=None)
                    # Display sentiment scores using st.metric
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label="Positive", value=sentiment_score.get('Positive', 0.0))
                    with col2:
                        st.metric(label="Negative", value=sentiment_score.get('Negative', 0.0))
                    with col3:
                        st.metric(label="Neutral", value=sentiment_score.get('Neutral', 0.0))

                with st.spinner("Detecting PII entities with Amazon Comprehend"):
                    pii_entities = detect_pii_entities(final_query)

                if pii_entities:
                    st.info(f"{len(pii_entities)} PII entities detected in query.")
                    for entity in pii_entities:
                        st.write(entity, unsafe_allow_html=True)
                else:
                    st.info("No PII entities detected.")

        # Create a play button for Amazon Polly
        if "Polly" in selected_services:
            print("Adding Polly analysis to response.")
            with st.expander("Amazon Polly - Text to Speech", expanded=True):
                with st.spinner(f"Processing Amazon Polly voice response from {model_providers[st.session_state.modelProvider]['model']}"):
                    voice_id = 'Matthew'  # You can choose a different voice ID if desired
                    audio_data = synthesize_speech(response, voice_id)
                    st.audio(audio_data, format='audio/mp3')

        if "Textract" in selected_services:
            print("Adding Textract keyword highlighting to response.")
            with st.expander("Amazon Textract", expanded=True):
                with st.spinner("Processing Amazon Textract ground truth"):
                    # Load and display ground truth if available
                    if ground_truth:
                        st.markdown(
                            "**Answer keywords**: " + markdown_bgcolor(ground_truth, "yellow"),
                            unsafe_allow_html=True,
                        )
                        # Highlight and display evidence in the source documents
                        tokens_answer = text_tokenizer(ground_truth)
                        tokens_labels = text_tokenizer(f"{ground_truth}") if ground_truth else []
                        tokens_miss = set(tokens_labels).difference(tokens_answer)

                        # ... [code for marking and displaying the document content]
                        st.divider()

                        markd = markdown_escape(all_text)

                        # Adding timeout handling after 10 seconds. This avoid long running jobs that can trigger an exist signal for the whole streamlit app.
                        try:
                            markd = markdown2(text=markd, tokens=tokens_answer, bg_color="#90EE90")
                            markd = markdown2(text=markd, tokens=tokens_miss, bg_color="red")
                        except TimeoutError as e:
                            markd = all_text
                            print(e)

                        st.markdown(markd, unsafe_allow_html=True)
                    else:
                        st.write("**Answer keywords**: Not available")
                        ground_truth = ""

# Call the main function to run the app
main()
