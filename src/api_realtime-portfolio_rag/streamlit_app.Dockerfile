# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    unzip \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy the gcp/env_vars file
COPY gcp/gcp_env_vars .

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .
COPY datamap/ .

# Make the start script executable
RUN chmod +x start.sh

# Set environment variables
ENV PYTHONPATH=/app
#ENV GCP_REGION=us-central1

# Expose Streamlit port
EXPOSE 8501

# Command to run the application
CMD ["./start.sh"]

