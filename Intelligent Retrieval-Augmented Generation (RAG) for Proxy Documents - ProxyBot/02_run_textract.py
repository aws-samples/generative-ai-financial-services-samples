import time
from botocore.exceptions import NoCredentialsError
from textract.textract_logger import get_logger
from utils.utils import get_directory_size
from awsmanager.s3_manager import FileUploader
from parameters.parameters import (
    data_path,
    text_data_path,
    PROXY_PDF_BUCKET,
    ticker_dict,
    START_YEAR,
    END_YEAR,
    s3_pdf_upload,
)
from textract.textract_util import PdfTextExtractor
from awsmanager.manager import AWSClientSession


logging = get_logger(__name__)
aws_session = AWSClientSession()
try:
    # Step 0 - Upload pdf files to S3 if needed
    logging.info(f"Starting...Step 0 - Upload pdf files to S3 if needed")
    s3_upload = s3_pdf_upload
    if s3_upload:
        logging.info(f"Uploading files from {data_path} to {PROXY_PDF_BUCKET}")
        actual_size, readable_size = get_directory_size(data_path)
        logging.info(f"Size of {data_path} is {readable_size}")
        uploader = FileUploader(
            session=aws_session,
            local_directory=data_path,
            bucket_name=PROXY_PDF_BUCKET,
            file_types=["pdf"],
        )
        uploader.upload_files()
        if actual_size >= 1024 * 1024:
            time.sleep(30)

    # Step 1 - Extract text from S3 pdf using Textractor
    logging.info("Starting...Step 1 - Extract text from S3 pdf using Textractor")
    for company in ticker_dict:
        ticker = ticker_dict[company]
        for year in range(START_YEAR, END_YEAR + 1, 1):
            try:
                extractor = PdfTextExtractor(
                    session=aws_session,
                    ticker=ticker,
                    year=year,
                    bucket_name=PROXY_PDF_BUCKET,
                    text_data_path=text_data_path,
                    profile_name=aws_session.get_profile(),
                    region_name=aws_session.get_region(),
                )
                _, _ = extractor.extract_text()
                logging.info(f"File {ticker} and {year} processed")
            except Exception as e:
                logging.error(f"File {ticker} and {year} might not exist")
                logging.error(f"Error extracting text from {ticker} {year}")
                logging.error(f"Resulting in the following error: {e}")
                continue
    logging.info("All run processes completed, please validate results")
except NoCredentialsError:
    logging.error("Exiting due to credential errors.")
