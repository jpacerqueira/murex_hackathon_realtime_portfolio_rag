# Realtime Portfolio API Metadata Analyzer and API

A tool for analyzing and querying API metadata using a local Llama server and RAG (Retrieval-Augmented Generation).

## Features

- Natural language querying of API specifications
- Similarity-based metadata retrieval
- Endpoint-level metadata analysis
- REST API interface
- Streamlit web interface

## API Documentation

The API provides the following endpoints:

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Root
- **GET /** - Returns API status
- **Response**: `{"message": "Realtime Portfolio API"}`

#### 2. API Analysis
- **POST /analyze** - Analyze API specification based on natural language query
- **Request Body**:
  ```json
  {
    "query": "What are the main endpoints in the API?",
    "k": 3,
    "context": "api",
    "format_type": "json"
  }
  ```
- **Response**: Analysis results with query context

#### 3. API Call Example
- **POST /api_call** - Get example API call based on query
- **Request Body**:
  ```json
  {
    "query": "get user data",
    "context": "api",
    "format_type": "json"
  }
  ```
- **Response**: API call example with proper request structure

#### 4. Similar Endpoints
- **POST /similar** - Get similar API endpoints
- **Request Body**:
  ```json
  {
    "query": "user endpoints",
    "k": 5
  }
  ```
- **Response**: Similar API endpoints with similarity scores

#### 5. Endpoint Details
- **POST /endpoint** - Get detailed information about a specific endpoint
- **Request Body**:
  ```json
  {
    "endpoint_path": "/api/users"
  }
  ```
- **Response**: Endpoint metadata including parameters and responses

#### 6. API Summary
- **GET /api_summary** - Get summary of entire API specification
- **Response**: Summary of all endpoints with parameter counts and names

### Interactive API Documentation
Access the Swagger UI at:
```
http://localhost:8000/docs
```

Access the ReDoc documentation at:
```
http://localhost:8000/redoc
```

## Setup

### Prerequisites
- Python 3.9+
- Local Llama server (Ollama or llama.cpp server)
- Docker (optional)

### Environment Variables
```bash
export LLAMA_BASE_URL=http://localhost:11434
export LLAMA_API_KEY=local
export LLAMA_INFERENCE_MODEL=llama3.2
export LLAMA_EMBEDDING_MODEL=nomic-embed-text
export LLAMA_EMBEDDINGS_PROVIDER=ollama  # openai, ollama, or hf
export HF_EMBEDDING_MODEL=all-MiniLM-L6-v2
export HF_EMBEDDING_CACHE_DIR=/embedding_model
export DATAMAP_CONFIG_PATH=config/datamap_config.json
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/realtime_portfolio_rag.git
cd realtime_portfolio_rag
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running with Docker

1. Build the Docker image:
```bash
docker build -t realtime-portfolio-api .
```

2. Run the container:
```bash
docker run -p 8000:8000 \
  -e LLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e LLAMA_INFERENCE_MODEL=llama3.2 \
  -e LLAMA_EMBEDDING_MODEL=nomic-embed-text \
  -e LLAMA_EMBEDDINGS_PROVIDER=openai \
  realtime-portfolio-api
```

### Running Locally

1. Start the API server:
```bash
python -m datamap.realtime_portfolio_api
```

2. Start the Streamlit app:
```bash
streamlit run datamap/realtime_portfolio_schema_analyzer.py
```

## Configuration

The API uses a JSON configuration file (`config/datamap_config.json`) with the following structure to map API endpoints from Swagger/OpenAPI specifications:

```json
{
    "api_base_url": "https://api.example.com",
    "swagger_url": "https://api.example.com/swagger.json",
    "region_name": "local",
    "cache_size": 128,
    "pattern": ""
}
```

## License

MIT License

