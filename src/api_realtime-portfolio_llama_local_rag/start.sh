#!/bin/bash

set -euo pipefail

if [ -z "${LLAMA_BASE_URL:-}" ]; then
    export LLAMA_BASE_URL="http://host.docker.internal:11434/v1"
fi

if [ -z "${LLAMA_API_KEY:-}" ]; then
    export LLAMA_API_KEY="local"
fi

echo "Using Llama server: ${LLAMA_BASE_URL}"

# Set PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH

# Run the Streamlit application
echo "Starting Streamlit application..."
cd /app/datamap && streamlit run realtime_portfolio_schema_analyzer.py --server.port=8501 --server.address=0.0.0.0

