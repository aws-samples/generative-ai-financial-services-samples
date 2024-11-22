import botocore
import json
import time
from opensearchpy import AWSV4SignerAuth
from aoss.aoss_logger import get_logger
from parameters.parameters import log_files_dict, config, aoss_params
from awsmanager.manager import AWSSecretsManager


logging = get_logger(__name__)

vector_store_name = aoss_params["vector_store_name"]
index_name = aoss_params["index_name"]
encryption_policy_name = aoss_params["encryption_policy_name"]
network_policy_name = aoss_params["network_policy_name"]
access_policy_name = aoss_params["access_policy_name"]


def aoss_create_encryption_security_policy(
    session, encryption_policy_name, vector_store_name
):
    aoss_client = session.get_aoss_client()
    try:
        logging.info(f"Creating encryption security policy {encryption_policy_name}...")
        response = aoss_client.create_security_policy(
            description="Encryption policy for AOSS collections",
            name=encryption_policy_name,
            policy=json.dumps(
                {
                    "Rules": [
                        {
                            "Resource": [f"collection/{vector_store_name}"],
                            "ResourceType": "collection",
                        }
                    ],
                    "AWSOwnedKey": True,
                }
            ),
            type="encryption",
        )
        logging.info(f"Encryption security policy {encryption_policy_name}...created")
        logging.info(f"{response}")
    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] == "ConflictException":
            logging.info(
                "[ConflictException] The policy name or rules conflict with an existing policy."
            )
            logging.error(
                f"Error creating encryption security policy or {encryption_policy_name} already exist: {error}"
            )
        else:
            raise error


def aoss_create_network_security_policy(
    session, network_policy_name, vector_store_name
):
    aoss_client = session.get_aoss_client()
    try:
        logging.info(f"Creating network security policy {network_policy_name}...")
        response = aoss_client.create_security_policy(
            description="Network policy for AOSS collections",
            name=network_policy_name,
            policy=json.dumps(
                [
                    {
                        "Description": "Public policy access for AOSS collection",
                        "Rules": [
                            {
                                "Resource": [f"collection/{vector_store_name}"],
                                "ResourceType": "collection",
                            },
                            {
                                "Resource": [f"collection/{vector_store_name}"],
                                "ResourceType": "dashboard",
                            },
                        ],
                        "AllowFromPublic": True,
                    }
                ]
            ),
            type="network",
        )
        logging.info(f"Network security policy {network_policy_name}...created")
        logging.info(f"{response}")
    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] == "ConflictException":
            logging.info(
                "[ConflictException] A network policy with this name already exists."
            )
            logging.error(
                f"Error creating network security policy or {network_policy_name} already exist: {error}"
            )
        else:
            raise error


def aoss_wait_for_collection_activation(session, vector_store_name):
    aoss_client = session.get_aoss_client()
    while True:
        try:
            logging.info("Checking collection activation")
            status = aoss_client.list_collections(
                collectionFilters={"name": vector_store_name}
            )["collectionSummaries"][0]["status"]
            if status in ("ACTIVE", "FAILED"):
                break
            time.sleep(30)
        except Exception as e:
            logging.error(f"Error while waiting for collection activation: {e}")
            pass


def aoss_create_access_policy(session, access_policy_name, vector_store_name):
    aoss_client = session.get_aoss_client()
    sts_client = session.get_sts_client()
    identity = sts_client.get_caller_identity()["Arn"]
    account_id = sts_client.get_caller_identity()["Account"]
    role_identity = f"arn:aws:iam::{account_id}:role/Admin"
    try:
        logging.info("Checking collection activation...")
        while True:
            status = aoss_client.list_collections(
                collectionFilters={"name": vector_store_name}
            )["collectionSummaries"][0]["status"]
            if status in ("ACTIVE", "FAILED"):
                break
            time.sleep(30)
        logging.info(f"Creating access policy {access_policy_name}...")
        response = aoss_client.create_access_policy(
            description="Data access policy for AOSS collection",
            name=access_policy_name,
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "Resource": [f"collection/{vector_store_name}"],
                                "Permission": ["aoss:*"],
                                "ResourceType": "collection",
                            },
                            {
                                "Resource": [f"index/{vector_store_name}/*"],
                                "Permission": [
                                    "aoss:*",
                                ],
                                "ResourceType": "index",
                            },
                        ],
                        "Principal": [identity, role_identity],
                        "Description": "Data access policy of AOSS",
                    }
                ]
            ),
            type="data",
        )
        logging.info(f"Access policy policy {access_policy_name}...created")
        logging.info(f"{response}")
    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] == "ConflictException":
            logging.info(
                "[ConflictException] An access policy with this name already exists."
            )
            logging.error(
                f"Error creating network security policy or {access_policy_name} already exist: {error}"
            )
        else:
            raise error


def create_aoss_credentials(session):
    aoss_client = session.get_aoss_client()
    try:
        collection_response = aoss_client.list_collections(
            collectionFilters={"name": vector_store_name}
        )
        collection_name = collection_response["collectionSummaries"][0]["name"]
        logging.info(f"Collection {collection_name} already exist, skipping creation")

        collection_id = collection_response["collectionSummaries"][0]["id"]
    except:
        logging.info(f"Collection {vector_store_name} does not exist, creating...")
        logging.info(f"Creating collection {vector_store_name}")
        collection_response = aoss_client.create_collection(
            name=vector_store_name,
            type="VECTORSEARCH",
        )
        collection_name = collection_response["createCollectionDetail"]["name"]
        logging.info(f"Collection {collection_name} created")
        collection_id = collection_response["createCollectionDetail"]["id"]
    service = "aoss"
    credentials = session.obtain_credentials()
    auth = AWSV4SignerAuth(credentials, config["aws_params"]["region_name"], service)
    try:
        region_name = config["aws_params"]["region_name"]
        aoss_port = 443
        aoss_url = "aoss.amazonaws.com"
        host = f"{collection_id}.{region_name}.{aoss_url}"
        logging.info(f"Host: {host}")
        logging.info(f"aoss_auth: {str(auth)}")
        aoss_credentials = {
            "aoss_host": host,
            "aoss_port": aoss_port,
            "aoss_index": index_name,
        }
        logging.info(f"Credentials: {aoss_credentials}")
        return aoss_credentials
    except Exception as e:
        logging.error(f"Error creating new AOSS credentials: {e}")
        return {"No credentials created"}


def delete_aoss(session, vector_store_name, action=True):
    aoss_client = session.get_aoss_client()
    if action:
        try:
            collection_response = aoss_client.list_collections(
                collectionFilters={"name": vector_store_name}
            )
            collection_name = collection_response["collectionSummaries"][0]["name"]
            logging.info(f"Collection {collection_name} exists")
        except:
            logging.info(
                f"Collection {vector_store_name} does not exist, skipping deletion"
            )
            pass
        try:
            collection_response = aoss_client.list_collections(
                collectionFilters={"name": vector_store_name}
            )
            collection_id = collection_response["collectionSummaries"][0]["id"]
            aoss_client.delete_collection(id=collection_id)
            logging.info(
                f"Collection {vector_store_name} with collection_id: {collection_id} deleted"
            )
        except Exception as e:
            logging.error(f"Error deleting collection {vector_store_name}: {e}")
            pass
        try:
            aoss_client.delete_security_policy(
                name=encryption_policy_name, type="encryption"
            )
            logging.info(f"Encryption policy {encryption_policy_name} deleted")
        except Exception as e:
            logging.error(
                f"Error deleting encryption policy {encryption_policy_name}: {e}"
            )
            logging.info(
                f"Encryption policy {encryption_policy_name} does not exist, skipping deletion"
            )
            pass
        try:
            aoss_client.delete_security_policy(name=network_policy_name, type="network")
            logging.info(f"Network policy {network_policy_name} deleted")
        except Exception as e:
            logging.error(f"Error deleting network policy {network_policy_name}: {e}")
            logging.info(
                f"Network policy {network_policy_name} does not exist, skipping deletion"
            )
            pass
        try:
            aoss_client.delete_access_policy(name=access_policy_name, type="data")
            logging.info(f"Access policy {access_policy_name} deleted")
        except Exception as e:
            logging.error(f"Error deleting access policy {access_policy_name}: {e}")
            logging.info(
                f"Access policy {access_policy_name} does not exist, skipping deletion"
            )
            pass
        logging.info(f"All AOSS resources deleted")


def aoss_creation(session, action, aoss_credentials_name):
    # Step 0 - Delete AOSS
    delete_aoss(session, vector_store_name, action)
    # Step 1 - Create AOSS Security Encryption
    aoss_create_encryption_security_policy(
        session, encryption_policy_name, vector_store_name
    )
    # Step 2 - Create AOSS Network Security
    aoss_create_network_security_policy(session, network_policy_name, vector_store_name)
    # Step 3 - Get AOSS Credentials
    aoss_credentials = create_aoss_credentials(session)
    with open(log_files_dict["aoss_credential"], "w", encoding="utf-8") as file:
        json.dump(aoss_credentials, file, ensure_ascii=False, indent=4)
        logging.info(f"AOSS Credentials written to `keys` folder")
    # Step 4 - Create AOSS Access Policy
    aoss_create_access_policy(session, access_policy_name, vector_store_name)
    ASM = AWSSecretsManager(session)
    ASM.store_credentials(aoss_credentials_name, credentials_dict=aoss_credentials)
    return aoss_credentials
