import nltk

try:
    # Check if stopwords are present
    print("Checking if NLTK stopwords (english) are already downloaded")
    print("NLTK stopwords (english) found")
except LookupError:
    # If not present, download them
    print("NLTK stopwords (english) NOT found. downloading...")
    nltk.download("stopwords")
    print("NLTK stopwords (english) download complete")
