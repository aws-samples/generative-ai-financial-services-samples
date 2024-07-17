import numpy as np
import os
import json
from parameters.logger import get_logger
from parameters.parameters import PROXY_TEXT_BUCKET, aoss_parameters_dict, main_path
from utils.utils import get_raw_data
from awsmanager.s3_manager import FileReader
from awsmanager.manager import AWSClientSession, AWSSecretsManager
from awsmanager.bedrock import get_text_embedding, bedrock_client
from parameters.parameters import AWS_DEFAULT_REGION, config
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

logging = get_logger(__name__)

BULK_LIMIT = aoss_parameters_dict["bulk_limit"]
CHUNK_SIZE = aoss_parameters_dict["chunk_size"]
CHUNK_OVERLAP = aoss_parameters_dict["chunk_overlap"]
VECTOR_SIZE = aoss_parameters_dict["vector_size"]
SEARCH_SIZE = aoss_parameters_dict["search_size"]

# AOSS Settings
aws_session = AWSClientSession()
ASM = AWSSecretsManager(aws_session)
aoss_secrets = ASM.get_secret_credentials(config["secret"]["aoss_credentials_name"])
aoss_host = aoss_secrets["aoss_host"]
aoss_port = aoss_secrets["aoss_port"]
aoss_index = aoss_secrets["aoss_index"]
aoss_region = AWS_DEFAULT_REGION
service = "aoss"
credentials = aws_session.obtain_credentials()

aoss_auth = AWSV4SignerAuth(credentials, aoss_region, service)
aoss_client = OpenSearch(
    hosts=[{"host": aoss_host, "port": aoss_port}],
    http_auth=aoss_auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    pool_maxsize=20,
    timeout=50000,
)


def create_context(sources, ticker, _date, local_run):
    logging.info(f"Sources: {sources}")
    logging.info(f"Ticker: {ticker}")
    data_list = []
    _date = str(_date)

    for source in sources:
        file_path = os.path.join(main_path, source)
        logging.info(f"File path: {file_path} processed")
        main_text_length = len(f"14A_{ticker}_{_date}_XXX")
        logging.info(f"Starting -> file path: {file_path}...")

        if local_run:
            print(source)
            file_path = os.path.join(main_path, source)
            print(file_path)
            logging.info(f"File path: {file_path} processed")
            data_list.append((get_raw_data(file_path), source[:main_text_length]))
        else:
            file_name = os.path.basename(source)
            s3_file_path = f"{ticker}/{file_name}"
            logging.info(f"S3 File path: {s3_file_path} processed")
            loader = FileReader(aws_session, PROXY_TEXT_BUCKET)
            logging.info(s3_file_path)
            data_list.append(
                (
                    loader.read_file(s3_file_path, file_format="txt").decode(),
                    source[:main_text_length],
                )
            )
        logging.info(f"<DATA LIST> >> {data_list}")

    output_text = [
        f"<INFOTEXT FILE: {file}>\n{data}\n\n</INFOTEXT>" for data, file in data_list
    ]
    return "\n".join(output_text)


def get_index_response(
    user_input, document_date, ticker, local_run, search_size=SEARCH_SIZE
):
    user_input_json = json.dumps({"inputText": user_input})
    logging.info(f"User input: {user_input}")
    input_text_embeddings = get_text_embedding(user_input_json, bedrock_client)
    query = {
        "size": search_size,
        "_source": True,
        "query": {
            "bool": {
                "must": {
                    "knn": {
                        "vector_title": {
                            "vector": input_text_embeddings,
                            "k": search_size,
                        }
                    }
                },
                "filter": [
                    {"term": {"company": ticker}},
                    {"term": {"document_date": f"{document_date}"}},
                ],
            }
        },
    }
    # AOSS Client Search
    relevant_aoss_response = aoss_client.search(body=query, index=aoss_index)
    try:
        metadata_source_list = [
            str(hit["_source"]["metadata"]["source"].split("\\")[-1])
            for hit in relevant_aoss_response["hits"]["hits"]
        ]
        logging.info(f"Metadata source list: {metadata_source_list}")
        unique_source_list = []
        [
            unique_source_list.append(item)
            for item in metadata_source_list
            if item not in unique_source_list
        ]
        context_text = create_context(
            sources=unique_source_list,
            ticker=ticker,
            _date=document_date,
            local_run=local_run,
        )
    except Exception as error:
        logging.error(f"Exception error: {error}")
        context_text = "Sorry, I am not able to process your request at the moment. Please try again later."
        unique_source_list = []
        relevant_aoss_response = {}
        return context_text, unique_source_list, relevant_aoss_response
    return context_text, unique_source_list, relevant_aoss_response
