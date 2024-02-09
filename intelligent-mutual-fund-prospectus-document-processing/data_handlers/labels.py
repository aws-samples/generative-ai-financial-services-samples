from typing import List
from utils.utils_os import read_jsonl, read_json
import re


# Function to load a master list of labels (datapoints to question mapping)
def load_labels_master(datapoint_master_file) -> List[str]:
    """Load datapoints:question mapping"""
    return read_json(datapoint_master_file)


# Function to load labels for a specific document
def load_labels(doc_path, datapoint_labels_file) -> List[str]:
    print(doc_path)
    print(datapoint_labels_file)
    """
    Load doc labels.
    The file might be pdf / txt / _page_.txt.
    The labels json refers to .pdf
    Let's find corresponding labels regardless of the file extension.
    """

    # Extract the document name from the path and preprocess it
    doc_name = doc_path.split("/")[-1]
    doc_base = doc_name[:-4]  # cut extension
    doc_base = re.sub(r"_\d$", "", doc_base)  # cut page number
    doc_base = doc_base.lower()
    nlen = len(doc_base)

    # Read labels from the JSONL file
    labels = read_jsonl(datapoint_labels_file)

    # Filter labels to find those corresponding to the given document
    labels = [x for x in labels if x["FILENAME"][:nlen].lower() == doc_base]

    # Return the first matching label or an empty dictionary if none found
    return labels[0] if labels else {}
