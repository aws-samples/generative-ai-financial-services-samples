import nltk
from nltk.data import find


def check_nltk_package(package_name):
    """
    Check if an NLTK package is already downloaded.
    Returns True if downloaded, False if not.
    """
    try:
        find(f'corpora/{package_name}')
    except LookupError:
        nltk.download(package_name)

if __name__ == "__main__":
    check_nltk_package("stopwords")
