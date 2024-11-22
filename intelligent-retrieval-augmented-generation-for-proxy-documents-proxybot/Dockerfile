# Use the official Python image as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV POETRY_VERSION="1.3.2" \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501

# Install Poetry
RUN pip install "poetry==${POETRY_VERSION}"

# Copy the project files into the container
COPY pyproject.toml poetry.lock* /app/

# Configure Poetry:
# - No virtualenvs inside the docker container
# - Do not ask any interactive question
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Copy the current directory contents into the container
COPY . /app

# Expose the port for Streamlits
EXPOSE 8501

# Define a healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# # Define the command to run on container start
CMD ["streamlit", "run", "app.py", "--theme.base=light", "--logger.level=info", \
     "--browser.gatherUsageStats", "false", "--server.port=8080", "--server.fileWatcherType=watchdog"]