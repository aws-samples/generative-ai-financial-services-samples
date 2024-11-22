import io
import os
import json
import PyPDF2
import pandas as pd
from botocore.exceptions import NoCredentialsError, ClientError
from parameters.logger import get_logger


logging = get_logger(__name__)


class FileReader:
    def __init__(self, session, bucket_name):
        self.session = session
        self.bucket_name = bucket_name
        self.s3_client = session.get_s3_client()

    def read_file(self, key, download=False, to_dataframe=False, file_format=None):
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            if download:
                self._download_file(key, response)
                return
            if to_dataframe:
                if file_format in ["csv", "txt"]:
                    return pd.read_csv(response["Body"])
                elif file_format == "parquet":
                    return pd.read_parquet(io.BytesIO(response["Body"].read()))
                elif file_format == "excel":
                    return pd.read_excel(io.BytesIO(response["Body"].read()))
                else:
                    logging.error(
                        f"Dataframe conversion not supported for {file_format}"
                    )
            else:
                if file_format == "json":
                    return json.load(response["Body"])
                elif file_format == "pdf":
                    reader = PyPDF2.PdfReader(response["Body"])
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                elif file_format in ["txt", "csv", "tsv"]:
                    return response["Body"].read()  # .decode('utf-8')
                else:
                    logging.error(f"File format {file_format} not supported")
        except Exception as e:
            logging.error(
                f"Failed to read file {key} from bucket {self.bucket_name}: {str(e)}"
            )

    def _download_file(self, key, response):
        file_name = key.split("/")[-1]
        with open(file_name, "wb") as f:
            f.write(response["Body"].read())
        logging.info(f"File {file_name} downloaded successfully")


class FileUploader:
    def __init__(self, session, local_directory, bucket_name, file_types=None):
        """
        Initialize the uploader with directory, bucket and file types.
        :param local_directory: Directory to upload files from.
        :param bucket_name: S3 bucket name to upload files to.
        :param file_types: List of file extensions to upload, e.g., ['pdf', 'jpg']. If None, all files are uploaded.
        """
        self.session = session
        self.local_directory = local_directory
        self.bucket_name = bucket_name
        self.file_types = file_types if file_types is not None else []
        self.s3_client = session.get_s3_client()
        self.ensure_bucket_exists()

    def ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if it does not."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            logging.error(f"Failed to access S3 bucket {self.bucket_name}: {str(e)}")
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                self.s3_client.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration={'LocationConstraint': self.session.get_region()})
            else:
                raise

    def upload_files(self):
        """Walk through the local directory and upload specified file types to S3."""
        for root, dirs, files in os.walk(self.local_directory):
            for file in files:
                if self.should_upload_file(file):
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, self.local_directory)
                    s3_path = relative_path.replace(os.sep, "/")
                    print(s3_path)
                    self.upload_file_to_s3(local_path, s3_path)

    def should_upload_file(self, file_name):
        """Check if a file matches the specified file types to be uploaded."""
        if not self.file_types:  # If no file types are specified, upload all files
            return True
        file_extension = file_name.split(".")[-1]
        return file_extension.lower() in [ft.lower() for ft in self.file_types]

    def upload_file_to_s3(self, local_path, s3_path):
        """Upload a single file to S3."""
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, s3_path)
            logging.info(f"Uploaded {local_path} to s3://{self.bucket_name}/{s3_path}")
        except NoCredentialsError:
            logging.error("Credentials not available for AWS S3.")


def generate_presigned_url(session, bucket_name, object_name, expiration=3600):
    """
    Generate a presigned URL to share an S3 object
    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    # Create a session using Amazon S3
    s3_client = session.get_s3_client()
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except NoCredentialsError:
        print("Credentials not available")
        return None
    return response


def show_presigned_url(session, bucket_name, ticker, source):
    object_name = f"{ticker}/{source}"  # Replace with your object key
    print(object_name)
    presigned_url = generate_presigned_url(
        session, bucket_name, object_name, expiration=3600
    )
    if presigned_url:
        return presigned_url
    else:
        return "Presign error"
