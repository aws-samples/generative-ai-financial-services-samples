import re
import platform
import boto3
from botocore.config import Config
from langchain.chains.question_answering import load_qa_chain
from langchain.docstore import InMemoryDocstore
from langchain.vectorstores.opensearch_vector_search import OpenSearchVectorSearch
from langchain_handler.langchain_bedrock_wrappers import BedrockCached


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
        "anthropic.claude-v2": {
            "temperature": 0.0,
            "max_tokens_to_sample": 300,
            "stop_sequences": ["\n\nHuman"],
        },
        "anthropic.claude-instant-v1": {
            "temperature": 0.0,
            "max_tokens_to_sample": 300,
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


# Function to create an in-memory document store
def create_in_memory_store(docs):
    return InMemoryDocstore({doc.metadata["doc_id"]: doc for doc in docs})


# Function to load a QA chain for a given LLM
def chain_qa(llm, verbose=False):
    return load_qa_chain(llm, chain_type="stuff", verbose=verbose)


# Function to perform search and answer using a document store and a chain
def search_and_answer(store, chain, query, k=2, doc_source_contains=None):
    # Perform similarity search or document retrieval based on the store type
    if isinstance(store, OpenSearchVectorSearch):
        docs = store.similarity_search(
            query,
            k=k,
            # include_metadata=False,
            verbose=False,
        )
    elif isinstance(store, InMemoryDocstore):
        docs = [store.search(i) for i in range(k)]
    else:
        assert False, f"Unknown doc store {type(store)}"

    # Filter by name
    if doc_source_contains is not None:
        docs = [doc for doc in docs if doc_source_contains in doc.metadata["source"]]

    print("Langchain IR has retrieved {} docs".format(len(docs)))

    # Filter documents if necessary and run the chain to get a response
    response = chain.run(input_documents=docs, question=query)
    return {"response": response, "docs": docs}
