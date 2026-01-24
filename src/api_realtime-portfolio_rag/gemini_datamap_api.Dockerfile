FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the gcp/env_vars file
COPY gcp/gcp_env_vars .

# Copy requirements first to leverage Docker cache
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/config

# Expose port for the API
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Command to run the API
CMD ["python", "-m", "uvicorn", "datamap.realtime_portfolio_api:app", "--host", "0.0.0.0", "--port", "8000"]

