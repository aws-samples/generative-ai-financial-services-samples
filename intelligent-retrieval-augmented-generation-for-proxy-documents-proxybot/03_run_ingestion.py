import os
import time
from botocore.exceptions import NoCredentialsError
from data_pipeline.pipeline import (
    documents_loading_splitting,
    create_aoss_indices,
    bulk_ingest_data,
)
from parameters.parameters import (
    text_data_path,
    ticker_dict,
    START_YEAR,
    END_YEAR,
    s3_pdf_upload,
)
from awsmanager.manager import AWSClientSession
from parameters.logger import get_logger
from awsmanager.s3_manager import FileUploader
from utils.utils import get_directory_size
from parameters.parameters import text_data_path, PROXY_TEXT_BUCKET

logging = get_logger(__name__)

documents_dicts = {}
aws_session = AWSClientSession()

try:
    # Step 0 - Initialise and create AOSS indices
    print("Executing...Step 0 - Initialise and create AOSS indices")
    aoss_client = create_aoss_indices(aws_session)

    # Step 1 - Upload extracted text files to S3
    print("Executing...Step 1 - Upload extracted text files to S3")
    s3_upload = s3_pdf_upload
    if s3_upload:
        logging.info(f"Uploading files from {text_data_path} to {PROXY_TEXT_BUCKET}")
        actual_size, readable_size = get_directory_size(text_data_path)
        logging.info(f"Size of {text_data_path} is {readable_size}")
        uploader = FileUploader(
            session=aws_session,
            local_directory=text_data_path,
            bucket_name=PROXY_TEXT_BUCKET,
            file_types=["txt"],
        )
        uploader.upload_files()
        if actual_size >= 1024 * 1024:
            # Allows for 30s rest from the AOSS collection set
            time.sleep(20)

    # Step 2 - Data Ingestion to AOSS
    print("Executing...Step 2 - Data Ingestion to AOSS")
    for company in ticker_dict:
        ticker = ticker_dict[company]
        for year in range(START_YEAR, END_YEAR + 1, 1):
            data_source = os.path.join(text_data_path, ticker)
            data_source = f"text_data/{ticker}"
            print(data_source)
            documents_dicts[ticker] = documents_loading_splitting(
                docs_source=data_source, ticker=ticker, document_date=year
            )
            try:
                data_source = os.path.join(text_data_path, ticker)
                data_source = f"text_data/{ticker}"
                print(data_source)
                documents_dicts[ticker] = documents_loading_splitting(
                    docs_source=data_source, ticker=ticker, document_date=year
                )
                bulk_ingest_data(
                    aws_session,
                    input_docs=documents_dicts[ticker],
                    ticker=ticker,
                    document_date=year,
                )
            except Exception as e:
                logging.error(f"File {ticker} and {year} might not exist")
                logging.error(f"Error extracting text from {ticker} {year}")
                logging.error(f"Resulting in following error: {e}")
                continue
    logging.info("All run processes completed, please validate results")

except NoCredentialsError:
    print("Exiting due to credential errors.")
