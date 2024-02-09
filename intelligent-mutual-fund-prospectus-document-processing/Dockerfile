# Use an official Python 3.10 base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Download stopwords
RUN python -m nltk.downloader stopwords

# Make port 8501 available for Streamlit
EXPOSE 8501

# Define the command to run on container start
CMD ["streamlit", "run", "app.py", "--theme.base", "light", "--logger.level", "info", "--browser.gatherUsageStats", "false"]
