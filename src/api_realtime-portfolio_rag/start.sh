#!/bin/bash

# Set GCP region
export GCP_REGION=us-central1

# First try to get credentials from environment variables
if [ -f "/app/gcp_env_vars" ]; then
    echo "Loading GCP credentials from gcp_env_vars file..."
    source /app/gcp_env_vars
fi

# If credentials are not set, try to get them from environment
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "GCP API key not found in environment"
    exit 1
fi

# Verify credentials are set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: GCP API key is not properly set"
    exit 1
fi

# Print the credentials (for debugging - be careful in production)
echo "Using GCP credentials:"
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:10}..." # Only show first 10 chars

# Set PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH

# Run the Streamlit application
echo "Starting Streamlit application..."
cd /app/datamap && streamlit run realtime_portfolio_schema_analyzer.py --server.port=8501 --server.address=0.0.0.0

