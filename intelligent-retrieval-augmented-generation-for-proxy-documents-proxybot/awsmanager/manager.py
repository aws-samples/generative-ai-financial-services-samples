import boto3
import json
from botocore.exceptions import ClientError
from botocore.config import Config
from parameters.logger import get_logger
from parameters.parameters import config, aws_profile

logging = get_logger(__name__)


class AWSResourceManager:
    aws_session = None

    @classmethod
    def initialise_session(cls):
        use_temporary_credentials = config.getboolean(
            "aws_params", "use_temporary_credentials", fallback=False
        )
        if use_temporary_credentials:
            # Temporary credentials using STS - Not used
            role_arn = config.get("aws_params", "role_arn")
            role_session_name = config.get("aws_params", "role_session_name")
            sts = boto3.client("sts")
            assumed_role_object = sts.assume_role(
                RoleArn=role_arn, RoleSessionName=role_session_name
            )
            credentials = assumed_role_object["Credentials"]
            cls.aws_session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=config.get("aws_params", "region_name"),
            )
        elif aws_profile == None:
            cls.aws_session = boto3.Session()
            print("Session initialised using default profile or environment variables")
        else:
            cls.aws_session = boto3.Session(profile_name=aws_profile)
            print(f"Session initialised using profile {aws_profile}")

    @classmethod
    def get_session(cls):
        if cls.aws_session is None:
            cls.initialise_session()
        return cls.aws_session


class AWSClientSession:
    def __init__(self, session=None):
        if session is None:
            session = AWSResourceManager.get_session()
        self.session = session

    def get_iam_client(self):
        return self.session.client("iam")

    def get_aoss_client(self):
        return self.session.client("opensearchserverless")

    def get_s3_client(self):
        return self.session.client("s3")

    def get_sts_client(self):
        return self.session.client("sts")

    def obtain_credentials(self):
        return self.session.get_credentials()

    def get_secrets_manager(self):
        return self.session.client("secretsmanager")

    def get_region(self):
        return self.session.region_name

    def get_profile(self):
        return self.session.profile_name

    def get_bedrock_client(self, runtime=False):
        retry_config = Config(
            retries={
                "max_attempts": 8,
                "mode": "standard",
            },
        )
        if runtime:
            service_name = "bedrock-runtime"
        else:
            service_name = "bedrock"
        logging.info(f"Using service: {service_name}")
        try:
            bedrock = self.session.client(
                service_name=service_name, config=retry_config
            )
            logging.info(f"Bedrock client created")
            if not runtime:
                logging.info("Not using runtime")
                logging.info(bedrock.list_foundation_models())
            return bedrock
        except Exception as error:
            logging.error(f"Error creating bedrock client: {error}")
            return None


class AWSSecretsManager:
    def __init__(self, session):
        self.session = session
        self.secrets_client = session.get_secrets_manager()

    def load_credentials_from_json(self, json_file_path):
        if json_file_path:
            with open(json_file_path, "r") as file:
                aws_credentials = json.load(file)
            return aws_credentials
        else:
            return {}

    def create_or_update_secret(self, secret_name, secret_data):
        try:
            self.secrets_client.create_secret(
                Name=secret_name,
                SecretString=json.dumps(secret_data),
                Description=f"Secret for {secret_name}",
            )
            logging.info(f"Created secret: {secret_name}")
        except self.secrets_client.exceptions.ResourceExistsException:
            self.secrets_client.update_secret(
                SecretId=secret_name, SecretString=json.dumps(secret_data)
            )
            logging.info(f"Updated secret: {secret_name}")

    def check_secret_exists(self, secret_name):
        try:
            self.secrets_client.describe_secret(SecretId=secret_name)
            return True
        except self.secrets_client.exceptions.ResourceNotFoundException:
            return False

    def store_credentials(
        self, aws_secret_name, credentials_dict=None, json_file_path=None
    ):
        if self.session.get_profile():
            secret_name = f"{self.session.get_profile()}/{aws_secret_name}"
            if credentials_dict:
                self.create_or_update_secret(secret_name, credentials_dict)
            else:
                aws_credentials = self.load_credentials_from_json(json_file_path)
                self.create_or_update_secret(secret_name, aws_credentials)

    def get_secret_credentials(self, aws_secret_name):
        if self.session.get_profile():
            secret_name = f"{self.session.get_profile()}/{aws_secret_name}"
            if self.check_secret_exists(secret_name):
                secret = self.secrets_client.get_secret_value(SecretId=secret_name)
                return json.loads(secret["SecretString"])
        return None

    def delete_secret(self, aws_secret_name):
        if self.session.get_profile():
            secret_name = f"{self.session.get_profile()}/{aws_secret_name}"
        else:
            secret_name = aws_secret_name
        try:
            secret_info = self.secrets_client.describe_secret(SecretId=secret_name)
            logging.info(f"Secret info: {secret_info}")
        except self.secrets_client.exceptions.ResourceNotFoundException:
            logging.error(f"Secret {secret_name} not found")
            return None
        try:
            self.secrets_client.delete_secret(
                SecretId=secret_name, ForceDeleteWithoutRecovery=True
            )
            logging.info(f"Deleted secret: {secret_name}")
        except Exception as error:
            logging.error(f"Error deleting secret: {error}")


def create_bucket_if_not_exists(aws_session, bucket_name):
    s3_client = aws_session.get_s3_client()
    logging.info(f"Checking session {s3_client}")
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logging.info(
            f"Bucket '{bucket_name}' already exists. \n"
            f"Please provide a unique name. "
            f"Update the 'config.ini' file with a unique 'bucket_prefix' "
            f"and rerun the code. "
        )
    except ClientError as error:
        error_code = error.response["Error"]["Code"]
        if error_code == "404":
            logging.info(f"Bucket '{bucket_name}' does not exist. " f"Creating it now.")
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                logging.info(f"Created bucket {bucket_name}")
                return f"Bucket {bucket_name} was created successfully"
            except ClientError as error:
                logging.error(f"The following error has occurred: {error}\n")
                return f"The following error has occurred: {error}"
        elif error_code == "403":
            logging.info(
                f"Bucket '{bucket_name}' already exists. "
                f"But you do not have permission to access it"
            )
            return (
                f"Bucket '{bucket_name}' already exists. "
                f"But you do not have permission to access it"
            )
        else:
            logging.info(f"An error occurred during bucket check: {error}\n")
            return f"An error occurred during bucket check: {error}"
    return True


def delete_bucket(aws_session, bucket_name):
    s3_client = aws_session.get_s3_client()

    try:
        # Delete all objects in the bucket
        paginator = s3_client.get_paginator("list_objects_v2")
        while True:
            response = paginator.paginate(Bucket=bucket_name)
            delete_us = dict(Objects=[])
            for page in response:
                logging.info(f"Going through page {page}")
                if "Contents" in page:
                    for obj in page["Contents"]:
                        delete_us["Objects"].append({"Key": obj["Key"]})
                    if len(delete_us["Objects"]) > 0:
                        s3_client.delete_objects(Bucket=bucket_name, Delete=delete_us)
            if "IsTruncated" not in page or not page["IsTruncated"]:
                logging.info(f"No more objects to delete")
                break
        # Check for versioning on the bucket and delete all versions and delete markers
        versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
        if versioning and "Status" in versioning and versioning["Status"] == "Enabled":
            paginator = s3_client.get_paginator("list_object_versions")
            for version_page in paginator.paginate(Bucket=bucket_name):
                logging.info(f"Going through version page {version_page}")
                delete_us = {"Objects": []}
                for version in version_page.get("Versions", []):
                    delete_us["Objects"].append(
                        {"Key": version["Key"], "VersionId": version["VersionId"]}
                    )
                for marker in version_page.get("DeleteMarkers", []):
                    delete_us["Objects"].append(
                        {"Key": marker["Key"], "VersionId": marker["VersionId"]}
                    )
                if delete_us["Objects"]:
                    s3_client.delete_objects(Bucket=bucket_name, Delete=delete_us)
        s3_client.delete_bucket(Bucket=bucket_name)
        logging.info(f"Bucket '{bucket_name}' deleted successfully.")
    except ClientError as error:
        logging.error(f"The following error has occurred: {error}\n")
        return f"The following error has occurred: {error}"
    return True


def delete_bucket_minimal(aws_session, bucket_name):
    s3_client = aws_session.get_s3_client()
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        logging.info(f"Bucket '{bucket_name}' deleted successfully.")
    except ClientError as error:
        logging.error(f"The following error has occurred: {error}\n")
        return f"The following error has occurred: {error}"
    return True
