# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies (including build-essential and libpq-dev if needed for psycopg2 compilation, though we use psycopg2-binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user (Hugging Face requires UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's app directory
WORKDIR $HOME/app

# Copy the requirements file from the backend folder
COPY --chown=user backend/requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files
COPY --chown=user backend/ .

# Expose port 7860 as expected by Hugging Face Spaces
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
