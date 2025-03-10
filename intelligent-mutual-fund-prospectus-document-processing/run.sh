#!/bin/bash

# Check if BUCKET_NAME is set, if not prompt the user
if [ -z "$BUCKET_NAME" ]; then
  echo "BUCKET_NAME environment variable is not set."
  read -p "Please enter your S3 bucket name: " bucket_input
  export BUCKET_NAME="$bucket_input"
  echo "Set BUCKET_NAME=$BUCKET_NAME"
fi

# Check if COGNITO_ENABLED is set, if not prompt the user
if [ -z "$COGNITO_ENABLED" ]; then
  echo "COGNITO_ENABLED environment variable is not set."
  read -p "Enable Cognito authentication? (true/false): " cognito_input
  export COGNITO_ENABLED="$cognito_input"
  echo "Set COGNITO_ENABLED=$COGNITO_ENABLED"
fi

# If COGNITO_ENABLED is true, check if SECRET_NAME is set
if [ "$COGNITO_ENABLED" = "true" ]; then
  if [ -z "$SECRET_NAME" ]; then
    echo "When COGNITO_ENABLED is true, SECRET_NAME must also be set."
    read -p "Please enter your Cognito secret name: " secret_input
    export SECRET_NAME="$secret_input"
    echo "Set SECRET_NAME=$SECRET_NAME"
  fi
fi

# First, run the nltk_stopword.py script to ensure stopwords are downloaded
python utils/nltk_stopword.py

# Then, run the Streamlit app
streamlit run app.py --theme.base light --logger.level info --browser.gatherUsageStats false
