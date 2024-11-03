import os
import datetime
import uuid
import random
import configparser
import boto3

def check_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Created folder {folder}")


config = configparser.ConfigParser()
main_path = os.getcwd()
config.read(os.path.join(main_path, "config.ini"))

NOW = datetime.datetime.now()
START_YEAR = int(config["ticker_list"]["start_year"])
END_YEAR = NOW.year

log_folder = os.path.join(main_path, "logs")
chatbot_logs_folder = os.path.join(log_folder, "chatbot_logs")
textract_logs_folder = os.path.join(log_folder, "textract_logs")
reviews_logs_folder = os.path.join(log_folder, "reviews_logs")
aoss_logs_folder = os.path.join(log_folder, "aoss_logs")
data_path = os.path.join(main_path, "data")
text_data_path = os.path.join(main_path, "text_data")
key_folder = os.path.join(main_path, "keys")

check_folder_exists(log_folder)
check_folder_exists(chatbot_logs_folder)
check_folder_exists(textract_logs_folder)
check_folder_exists(reviews_logs_folder)
check_folder_exists(aoss_logs_folder)
check_folder_exists(text_data_path)
check_folder_exists(key_folder)

timestamp_string = NOW.strftime("%Y-%m-%d")
chat_timestamp_string = NOW.strftime("%Y-%m-%d_%H-%M-%S")
proxybot_log = f"proxybot_{timestamp_string}.log"
aoss_log = f"aoss_{timestamp_string}.log"
textract_log = f"textract_{timestamp_string}.log"
reviews_log = f"reviews_{timestamp_string}.log"

bedrock_performance_file = "BEDROCK_PERF.csv"
answer_timing_file = "ANSWER_TIMING.csv"

log_files_dict = {
    "chats_log": os.path.join(chatbot_logs_folder, f"CHAT_{chat_timestamp_string}.log"),
    "conversation_log": os.path.join(
        chatbot_logs_folder, f"CONVERSATION_{chat_timestamp_string}.log"
    ),
    "disambiguated_log": os.path.join(
        chatbot_logs_folder, f"DISAMBIGUATE_{chat_timestamp_string}.log"
    ),
    "execution_log": os.path.join(log_folder, proxybot_log),
    "aoss_log": os.path.join(aoss_logs_folder, f"proxybot_{timestamp_string}.log"),
    "textract_log": os.path.join(textract_logs_folder, textract_log),
    "reviews_log": os.path.join(reviews_logs_folder, reviews_log),
    "bedrock_performance_log": os.path.join(
        chatbot_logs_folder, bedrock_performance_file
    ),
    "answer_timing_log": os.path.join(chatbot_logs_folder, answer_timing_file),
    "aoss_credential": os.path.join(key_folder, "aoss_credential.json"),
}

ANSWER_LENGTH = 200
ATTEMPT = 1
MAX_ATTEMPTS = 8
BEDROCK_PARAMS = {
    "temperature": 0.1,
    "top_k": 1,
    "top_p": 1,
    "stop_sequences": ["Human:"],
    "model": "anthropic.claude-instant-v1",
    "answer_length": ANSWER_LENGTH,
}

TEXT_SEARCH_CRITERIA = {"text_locator": "14a.+?\.txt"}
DATA_FOLDER = "PROXY_CHAPTER_DATA"
DATA_FOLDER_PATH = os.path.join(main_path, DATA_FOLDER)
ticker = "AAPL"
company = "Apple"
summary_14A_file = f"14a_{ticker}_summary.txt"
summary_education_file = f"14a_education_summary.txt"
first = True
conversation_history = []
separator_chatbot = f"{'-' * 40} PROXY BOT:"
separator_user = f"{'-' * 40} USER:"
RESPONSE_LENGTH = 256

ragbot_dict = {
    "data_folder": DATA_FOLDER,
    "data_folder_path": DATA_FOLDER_PATH,
    "ticker": ticker,
    "company": company,
    "summary_14A_file": summary_14A_file,
    "summary_education_file": summary_education_file,
    "first": first,
    "conversation_history": conversation_history,
    "separator_chatbot": separator_chatbot,
    "separator_user": separator_user,
    "response_length": RESPONSE_LENGTH,
}

colour_dict = {"c_red": "\x1b[31m", "c_green": "\033[92m", "c_norm": "\033[0m"}

DISAMBIGUITY_CLAUSE = False
AWS_DEFAULT_REGION = config["aws_params"]["region_name"]
boto3.setup_default_session(region_name=AWS_DEFAULT_REGION)
print(f"************* SET BOTO3 Default region: {boto3.DEFAULT_SESSION.region_name} *****************")
aws_session = boto3.Session()
session_region = aws_session.region_name
print(f"*************  BOTO3 region: {session_region} *****************")

rd = random.Random()
rd.seed(42)
bucket_prefix = config["s3_buckets"]["bucket_prefix"]
random_uuid = uuid.UUID(int=rd.getrandbits(128), version=4)
# Take first 8 characters of UUID hex
short_id = random_uuid.hex[:8]
s3_name_prefix = str(short_id)
s3_name_prefix = f"{bucket_prefix}-{s3_name_prefix}"

PROXY_TEXT_BUCKET = f"{s3_name_prefix}-text-data"
PROXY_PDF_BUCKET = f"{s3_name_prefix}-pdf-data"

s3_text_upload = config["s3_buckets"]["s3_text_upload"]
s3_pdf_upload = config["s3_buckets"]["s3_pdf_upload"]


ticker_list = config["ticker_list"]["ticker_list"].split(", ")
ticker_company_name = config["ticker_list"]["ticker_company_name"].split(", ")

ticker_dict = dict(zip(ticker_company_name, ticker_list))

aoss_parameters_dict = {
    "bulk_limit": 256,
    "chunk_size": 3000,
    "chunk_overlap": 100,
    "vector_size": 1536,  # Bedrock Titan Embedding limit
    "search_size": 3,
}

task_prefix = config["opensearch"]["task_prefix"]

aoss_params = dict(
    vector_store_name=f"{task_prefix}-rag",
    index_name=f"{task_prefix}-rag-index",
    encryption_policy_name=f"{task_prefix}-rag-encryption",
    network_policy_name=f"{task_prefix}-rag-network",
    access_policy_name=f"{task_prefix}-rag-access",
)

try:
    aws_profile = config.get("aws_params", "profile_name", fallback=None)
    print(f"Set profile: {aws_profile}")
    if aws_profile is not None and aws_profile == "":
        aws_profile = None
    if aws_profile == "None":
        aws_profile = None
except:
    os.environ["AWS_PROFILE"] = None
    pass

local_run = config["local"]["local_run"].lower()
local_run = {"true": True, "false": False}[local_run]

models_list = ["anthropic.claude-3-sonnet-20240229-v1:0"]
