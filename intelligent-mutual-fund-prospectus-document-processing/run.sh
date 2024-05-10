#!/bin/bash

# First, run the nltk_stopword.py script to ensure stopwords are downloaded
python utils/nltk_stopword.py

# Then, run the Streamlit app
streamlit run app.py --theme.base light --logger.level info --browser.gatherUsageStats false
