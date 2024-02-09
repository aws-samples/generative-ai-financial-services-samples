"""PDF parser and Loader"""

import re
import glob
from typing import List
import pdfplumber
from utils.utils_os import write_text
from langchain.schema import Document


# Function to clean and normalize text extracted from a PDF
def clean_text(s):
    s = "".join(c for c in s if ord(c) < 128)
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s


# Function to list all PDF documents in a given folder
def list_doc(folder):
    if folder[-1] != "/":
        folder = folder + "/"
    return list(glob.iglob(folder + "*.pdf"))


# Function to load a PDF document and extract its text content
def load_doc(doc_path, n_pages=None, verbose=False) -> List[Document]:
    # Verbose logging for debugging
    if verbose:
        print("Using pdfplumber:", doc_path)

    docs = []

    # Open the PDF file for reading
    with pdfplumber.open(doc_path) as pdf:
        # Iterate through the pages of the PDF
        for i, page in enumerate(pdf.pages):
            # Limit the number of pages processed if specified
            if n_pages and i == n_pages:
                break

            # Extract words from the page with specific settings for better accuracy
            text = " ".join(
                word["text"]
                for word in page.extract_words(
                    use_text_flow=True,
                    y_tolerance=0.5,
                    x_tolerance=1,
                    keep_blank_chars=True,
                )
            )

            # Create a Document object with extracted text and metadata
            docs += (
                Document(
                    page_content=text, metadata=dict({"source": doc_path, "page": i})
                ),
            )

    # Clean the extracted text and assign document IDs
    for i, doc in enumerate(docs):
        doc.page_content = clean_text(doc.page_content)
        doc.metadata["doc_id"] = i

        # Optional verbose logging
        if verbose:
            print(
                "doc_{}: len={}".format(
                    doc.metadata["doc_id"],
                    # doc.metadata['page'],
                    len(doc.page_content),
                )
            )

        # Save the extracted text to a separate file for review
        assert doc_path.lower().endswith(".pdf")
        txt_page_file = re.sub(
            r"\.pdf", f"_{i}_plumber.txt", doc_path, flags=re.IGNORECASE
        )
        write_text(txt_page_file, doc.page_content)
        print(f"Now you have {len(docs)} docs")

    # Verbose logging for the total number of documents processed
    if verbose:
        print(f"Now you have {len(docs)} docs")

    return docs
