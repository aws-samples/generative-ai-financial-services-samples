import numpy as np
import json
import time
import hashlib
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from opensearchpy import exceptions
from parameters.logger import get_logger
from parameters.parameters import aoss_parameters_dict
from utils.utils import timer
from logics.aossclient import create_aoss_client
from awsmanager.bedrock import bedrock_embeddings, bedrock_client, get_text_embedding


logging = get_logger(__name__)


BULK_LIMIT = aoss_parameters_dict["bulk_limit"]
CHUNK_SIZE = aoss_parameters_dict["chunk_size"]
CHUNK_OVERLAP = aoss_parameters_dict["chunk_overlap"]
VECTOR_SIZE = aoss_parameters_dict["vector_size"]
SEARCH_SIZE = aoss_parameters_dict["search_size"]


@timer("Documents loading and splitting")
def documents_loading_splitting(docs_source, ticker, document_date, doc_type="txt"):
    logging.info("Start of loading documents")
    if doc_type == "txt":
        text_loader_kwargs = {"autodetect_encoding": True}
        loader = DirectoryLoader(
            docs_source,
            glob=f"**/14A_{ticker}_{document_date}_*.txt",
            loader_cls=TextLoader,
            loader_kwargs=text_loader_kwargs,
        )
        documents = loader.load()
    else:
        documents = []
    if documents != []:
        # To be re-assess for Semantic Chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        docs = text_splitter.split_documents(documents)
        avg_doc_length = lambda documents: sum(
            [len(doc.page_content) for doc in documents]
        ) // len(documents)
        avg_char_count_pre = avg_doc_length(documents)
        avg_char_count_post = avg_doc_length(docs)
        logging.info(
            f"The average length among {len(documents)} documents loaded is {avg_char_count_pre} characters."
        )
        logging.info(
            f"After the split, we have {len(docs)} documents more than the original {len(documents)}."
        )
        logging.info(
            f"Average length among {len(docs)} documents (after split) is {avg_char_count_post} characters."
        )
        logging.info("Splitting documents, completed")
        logging.info("Inspecting the bedrock documents embedding...")
        try:
            sample_embedding = np.array(
                bedrock_embeddings.embed_query(docs[0].page_content)
            )
            model_id = bedrock_embeddings.model_id
            logging.info(f"Embedding model Id: {model_id}")
            logging.info(f"Sample embedding of a documents chunk: {sample_embedding}")
            logging.info(f"Size of the embedding: {sample_embedding.shape}")
        except ValueError as error:
            if "AccessDeniedException" in str(error):
                logging.error(
                    f"\x1b[41m{error}\
                \nTo troubeshoot this issue please refer to the following resources.\
                \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
                \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n"
                )

                class StopExecution(ValueError):
                    def _render_traceback_(self):
                        pass

                raise StopExecution
            else:
                raise error
    else:
        docs = []
    return docs


@timer("Create AOSS indices")
def create_aoss_indices(aws_session, view_mapping=True):
    aoss_client, aoss_index = create_aoss_client(aws_session)
    index_body = {
        "settings": {"index.knn": True},
        "mappings": {
            "properties": {
                "page_content": {"type": "text"},
                "company": {"type": "keyword"},
                "document_date": {"type": "keyword"},
                "metadata": {
                    "properties": {
                        "source": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            },
                        }
                    }
                },
                "vector_title": {"type": "knn_vector", "dimension": VECTOR_SIZE},
            }
        },
    }
    if not aoss_client.indices.exists(index=aoss_index):
        try:
            aoss_client.indices.create(index=aoss_index, body=index_body)
        except exceptions.RequestError as error:
            logging.error(f"Exception error: {error}")
    else:
        logging.info(f"Index {aoss_index} already exists")
    # view mapping schema for OpenSearch Serverless.
    if view_mapping:
        mapping_json = aoss_client.indices.get_mapping(aoss_index)
        logging.info(mapping_json)
    # 30s delay for AOSS collection creation to cool off
    time.sleep(30)
    return aoss_client


# Bulk ingest function
@timer("Bulk ingestion of data")
def bulk_ingest_data(session, input_docs, ticker, document_date):
    aoss_client, aoss_index = create_aoss_client(session)
    # TODO - Optimise code
    actions = []
    bulk_size = 0
    LIMIT_CHECKER = 250
    action = {"index": {"_index": aoss_index}}
    logging.info(f"Ingesting {ticker}")
    for document in input_docs:
        bulk_size += 1
        input_json = json.dumps({"inputText": document.page_content})
        text_embeddings = get_text_embedding(input_json, bedrock_client)
        actions.append(action)
        json_data = {
            "company": ticker,
            "document_date": document_date,
            "content_hash": hashlib.sha256(document.page_content.encode()).hexdigest(),
            "page_content": document.page_content,
            "metadata": document.metadata,
            "vector_title": text_embeddings,
        }
        actions.append(json_data)
        # Only needed if interested in checking limit
        if bulk_size > LIMIT_CHECKER:
            aoss_client.bulk(body=actions)
            logging.info(f"Bulk request sent with size: {bulk_size}")
            bulk_size = 0
    logging.info(f"Remaining documents: {bulk_size}")
    aoss_client.bulk(body=actions)
    return {"status_code": 200}
