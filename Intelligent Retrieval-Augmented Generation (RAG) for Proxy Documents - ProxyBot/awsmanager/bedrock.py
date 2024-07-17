import json
from parameters.logger import get_logger
from parameters.parameters import config
from langchain_community.embeddings import BedrockEmbeddings
from awsmanager.manager import AWSClientSession

logging = get_logger(__name__)

try:
    bedrock_client = AWSClientSession().get_bedrock_client(runtime=True)
except Exception as error:
    print(f"Error creating bedrock client: {error}")
    bedrock_client = None

bedrock_embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v1",
    client=bedrock_client,
    region_name=config["aws_params"]["region_name"],
)


def get_text_embedding(body, bedrock_client, model_id="amazon.titan-embed-text-v1"):
    response = bedrock_client.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
    )
    return json.loads(response.get("body").read()).get("embedding")
