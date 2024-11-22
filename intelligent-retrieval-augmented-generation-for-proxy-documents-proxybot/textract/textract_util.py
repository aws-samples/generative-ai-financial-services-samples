import os
import boto3
from typing import List
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from textractor import Textractor
from textractor.data.constants import TextractFeatures
from textractor.data.text_linearization_config import TextLinearizationConfig
from parameters.parameters import check_folder_exists, text_data_path
from textract.textract_logger import get_logger


logging = get_logger(__name__)


class PdfTextExtractor:
    def __init__(
        self,
        session,
        ticker,
        year,
        bucket_name,
        text_data_path,
        profile_name=None,
        region_name="us-east-1",
    ):
        self.session = session
        self.ticker = ticker
        self.year = year
        self.bucket_name = bucket_name
        self.text_data_path = text_data_path
        if region_name:
            self.textractor = Textractor(region_name=region_name)
        elif profile_name:
            self.textractor = Textractor(profile_name=profile_name)
        else:
            raise ValueError("Either region_name or profile_name must be provided")

    def extract_text(self):
        document_file_path = f"s3://{self.bucket_name}/{self.ticker}/{self.year}.pdf"
        logging.info(f"Document path - {document_file_path}")
        document = self.textractor.start_document_analysis(
            file_source=document_file_path,
            features=[TextractFeatures.LAYOUT, TextractFeatures.TABLES],
            save_image=False,
        )
        config = TextLinearizationConfig(
            hide_figure_layout=False,
            hide_header_layout=True,
            hide_footer_layout=True,
            hide_page_num_layout=True,
            hide_table_layout=False,
            table_prefix="<tables><table>",
            table_suffix="</table>",
            title_prefix="# ",
            section_header_prefix="## ",
        )
        logging.info("Getting content by setting content config")
        content = document.get_text(config=config)

        logging.info(f"{document.document}")
        headers_to_split_on = [("#", "Header 1")]

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
            return_each_line=False,
        )

        md_header_splits: List[Document] = markdown_splitter.split_text(content)
        logging.info(f"{len(md_header_splits)} chunks to be stored in {text_data_path}")
        self.save_extract_text(md_header_splits)

        return md_header_splits, document

    def save_extract_text(self, md_header_splits):
        for i, text in enumerate(md_header_splits):
            text_content = text.page_content
            if text.metadata:
                header_name = text.metadata["Header 1"]
                file_name = f"14A_{self.ticker}_{self.year}_{i:03d}_{header_name}.txt"
            else:
                file_name = f"14A_{self.ticker}_{self.year}_{i:03d}.txt"
            check_folder_exists(os.path.join(self.text_data_path, self.ticker))
            file_name_path = os.path.join(self.text_data_path, self.ticker, file_name)
            logging.info(f"{file_name_path}")
            with open(file_name_path, "a") as output_file:
                output_file.write(text_content)
            logging.info(f"Processed {i}")
        return {"status_code": 200}
