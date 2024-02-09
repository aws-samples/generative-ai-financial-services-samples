"""Abstact different ways to load the docs"""

from typing import Any, Iterable, List, Dict
from abc import ABC, abstractmethod
import os
import glob
from langchain.schema import Document
from langchain.docstore import InMemoryDocstore
from .load_pdf import load_doc
from utils.utils_os import read_text


# Abstract base class for different types of document sources
class DocSource(ABC):
    # Method to recommend the number of documents to retrieve, default is 1
    def recommended_k(self) -> int:
        return 1

    # Check if a document exists at the given path
    def exists(self, doc_path: str) -> bool:
        return os.path.exists(doc_path)

    # Sort and optionally rerank the documents based on certain criteria
    def rerank(self, doc_names):
        doc_names.sort()
        return doc_names

    # Create an in-memory document store from a list of documents
    def create_in_memory_store(self, docs):
        return InMemoryDocstore({doc.metadata["doc_id"]: doc for doc in docs})


# Concrete class to handle any type of documents stored in memory
class InMemoryAny(DocSource):
    def __init__(self, glob_pattern):
        print("Created", self.__class__.__name__)
        # Pattern to match document files
        self.glob_pattern = glob_pattern

    # Return the class name as a string
    def __str__(self):
        return "InMemoryAny"

    # List all documents that match the provided glob pattern
    def list_doc(self) -> List[str]:
        doc_paths = sorted(glob.iglob(self.glob_pattern))
        assert doc_paths, f"No documents found in {self.glob_pattern}"
        return doc_paths

    # Load a document from a local path and return a list of langchain Documents
    def load_doc_local(
        self, doc_path: str, n_pages=None, verbose=False
    ) -> List[Document]:
        """Create list of langchain Docs"""
        _, extension = os.path.splitext(doc_path)
        extension = extension.lower()

        # Load the document based on its file extension
        if extension == ".pdf":
            return load_doc(doc_path, n_pages=n_pages, verbose=verbose)
        elif extension == ".txt":
            # Create a Document instance for text files
            return [
                Document(
                    page_content=read_text(doc_path),
                    metadata=dict({"source": doc_path, "page": 0, "doc_id": 0}),
                )
            ]
        else:
            assert False, f"Unsupported format {extension} for {doc_path}"

    # Create an in-memory document store for a given document path
    def make_doc_store(self, doc_path: str) -> Any:
        docs = self.load_doc_local(doc_path)
        num_docs = len(docs)
        print(
            f"Creating in_memory store with {len(docs)} pages", self.__class__.__name__
        )
        return self.create_in_memory_store(docs), num_docs
