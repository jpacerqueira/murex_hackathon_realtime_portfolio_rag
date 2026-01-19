# Realtime Portfolio API Metadata Analyzer and API

A tool for analyzing and querying API metadata using GCP Gemini and RAG (Retrieval-Augmented Generation).

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
- GCP API key
- Docker (optional)

### Environment Variables
```bash
export GEMINI_API_KEY=your_api_key
export GEMINI_INFERENCE_MODEL=gemini-2.0-flash
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
  -e GEMINI_API_KEY=your_api_key \
  -e GEMINI_INFERENCE_MODEL=gemini-2.0-flash \
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
    "region_name": "us-central1",
    "cache_size": 128,
    "pattern": ""
}
```

## License

MIT License

