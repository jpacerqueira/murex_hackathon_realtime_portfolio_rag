from typing import List, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json
import os
from pathlib import Path
try:
    from .gemini_datamap_rag import GeminiDatamapRAG
except ImportError:
    from datamap.gemini_datamap_rag import GeminiDatamapRAG
from dotenv import load_dotenv
import logging
import numpy as np

# Load environment variables
load_dotenv()

# OpenAPI/Swagger documentation
description = """
Realtime Portfolio API helps you analyze and query API specifications using GCP Gemini and RAG.

## Features

* Natural language querying of API specifications
* Similarity-based API endpoint retrieval
* Endpoint and parameter-level API analysis
* Interactive API documentation
* Swagger/OpenAPI-based data source
"""

tags_metadata = [
    {
        "name": "root",
        "description": "Basic API information and health check",
    },
    {
        "name": "analysis",
        "description": "API analysis and operations",
    },
    {
        "name": "endpoints",
        "description": "Endpoint-specific operations and specifications",
    },
    {
        "name": "parameters",
        "description": "Parameter-specific operations and analysis",
    }
]

logger = logging.getLogger(__name__)

class DataMapAPIAnalyzer:
    def __init__(self, config_path: str):
        """Initialize the DataMapAPIAnalyzer with a configuration file path."""
        self.config_path = config_path
        self.config = self._load_config()
        
        # Validate GCP credentials
        google_api_key = os.getenv('GOOGLE_API_KEY')
        
        if not google_api_key:
            raise HTTPException(
                status_code=500,
                detail="GCP API key not found in environment variables. Please set GOOGLE_API_KEY."
            )
        
        # Get GCP credentials from environment variables
        gcp_credentials = {
            'GOOGLE_API_KEY': google_api_key
        }
        
        # Get API configuration with defaults
        api_base_url = self.config.get('api_base_url', '')
        swagger_url = self.config.get('swagger_url', '')
        region_name = self.config.get('region_name', 'us-central1')
        cache_size = self.config.get('cache_size', 128)
        
        logger.info(f"Initializing RAG with API configuration:")
        logger.info(f"API Base URL: {api_base_url}")
        logger.info(f"Swagger URL: {swagger_url}")
        logger.info(f"Region: {region_name}")
        
        # Initialize RAG with API configuration
        try:
            self.rag = GeminiDatamapRAG(
                api_base_url=api_base_url,
                swagger_url=swagger_url,
                region_name=region_name,
                gcp_credentials=gcp_credentials,
                cache_size=cache_size
            )
            self._initialize_rag()
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize RAG: {str(e)}"
            )
        
    def update_config(self, config: Dict[str, Any]):
        """Update the configuration with new values."""
        try:
            self.config.update(config)
            self._initialize_rag()
            logger.info("Updated configuration:")
            logger.info(f"API Configuration:")
            logger.info(f"  - Base URL: {self.config.get('api_base_url')}")
            logger.info(f"  - Swagger URL: {self.config.get('swagger_url')}")
            logger.info(f"  - Region: {self.config.get('region_name')}")
            logger.info(f"  - Pattern: {self.config.get('pattern')}")
            logger.info(f"  - Cache Size: {self.config.get('cache_size')}")
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Configuration file not found")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON configuration file")
    
    def _initialize_rag(self):
        """Initialize the RAG system with the API specifications."""
        try:
            if 'swagger_url' not in self.config:
                raise HTTPException(status_code=400, detail="Swagger URL not found in configuration")
            
            pattern = self.config.get('pattern')
            logger.info(f"Building RAG index with endpoints in pattern: {pattern}")
            
            self.rag.build_rag_index(pattern=pattern)
            logger.info("RAG index built successfully")
        except Exception as e:
            logger.error(f"Error initializing RAG: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error initializing RAG: {str(e)}"
            )
    
    def analyze_api(self, query: str, context: str = "api", format_type: str = "json") -> Dict[str, Any]:
        """Analyze the API specification based on a natural language query."""
        try:
            analysis = self.rag.get_detailed_api_analysis(query, context, format_type)
            return {
                "analysis": analysis,
                "query": query
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error analyzing API: {str(e)}")
        
    def get_api_call_in_context(self, query: str, context: str = "api", format_type: str = "json") -> Dict[str, Any]:
        """Get API call in context"""
        try:
            api_call = self.rag.get_detailed_api_call_in_context(query, context, format_type)
            return {
                "api_call": api_call,
                "query": query
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting API call in context: {str(e)}")
    
    def get_similar_api(self, query: str, k: int = 3) -> Tuple[List[str], List[float]]:
        """Get similar API endpoints with similarity scores."""
        try:
            return self.rag.query_api(query, k)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting similar API: {str(e)}")
    
    def get_endpoint_spec(self, endpoint_path: str) -> Dict[str, Any]:
        """Get detailed specification information about a specific endpoint."""
        try:
            spec = self.rag.get_endpoint_spec(endpoint_path)
            return spec
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting endpoint spec: {str(e)}")
    
    def get_parameter_info(self, endpoint_path: str, parameter_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific parameter."""
        try:
            return self.rag.get_parameter_info(endpoint_path, parameter_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting parameter info: {str(e)}")
    
    def get_api_summary(self) -> Dict[str, Any]:
        """Get a summary of the entire API specification."""
        try:
            all_endpoints = self.rag.api_cache
            summary = {
                "total_endpoints": len(all_endpoints),
                "endpoints": []
            }
            
            for endpoint_path, spec in all_endpoints.items():
                endpoint_info = {
                    "path": endpoint_path,
                    "method": spec.get("method", ""),
                    "description": spec.get("description", ""),
                    "tags": spec.get("tags", []),
                    "parameter_count": len(spec.get("parameters", [])),
                    "parameters": [param["name"] for param in spec.get("parameters", [])],
                    "has_request_body": spec.get("request_body") is not None,
                    "response_codes": list(spec.get("responses", {}).keys())
                }
                summary["endpoints"].append(endpoint_info)
            
            return summary
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting API summary: {str(e)}")

# FastAPI models
class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query about the API specification")
    k: int = Field(default=3, description="Number of results to return", ge=1, le=10)
    context: str = Field(default="api", description="Context for the query")
    format_type: str = Field(default="json", description="Format type for the response")

class EndpointRequest(BaseModel):
    endpoint_path: str = Field(..., description="Path of the endpoint to get specification for")

class ParameterRequest(BaseModel):
    endpoint_path: str = Field(..., description="Path of the endpoint")
    parameter_name: str = Field(..., description="Name of the parameter")

class AnalysisResponse(BaseModel):
    analysis: str = Field(..., description="Analysis results")
    query: str = Field(..., description="Original query")

class APICallResponse(BaseModel):
    api_call: str = Field(..., description="API call example")
    query: str = Field(..., description="Original query")

class SimilarResponse(BaseModel):
    similar_api: List[str] = Field(..., description="List of similar API endpoints")
    scores: List[float] = Field(..., description="Similarity scores for each entry")

class EndpointResponse(BaseModel):
    endpoint_path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    description: str = Field(..., description="Endpoint description")
    tags: List[str] = Field(..., description="Endpoint tags")
    parameters: List[Dict[str, Any]] = Field(..., description="Endpoint parameters")
    request_body: Optional[str] = Field(None, description="Request body schema")
    responses: Dict[str, Any] = Field(..., description="Response schemas")

class ParameterResponse(BaseModel):
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter data type")
    required: bool = Field(..., description="Whether parameter is required")
    description: str = Field(..., description="Parameter description")
    location: str = Field(..., description="Parameter location (query, path, header, etc.)")

class APISummaryResponse(BaseModel):
    total_endpoints: int = Field(..., description="Total number of endpoints")
    endpoints: List[Dict[str, Any]] = Field(..., description="List of endpoints with specifications")

class ConfigRequest(BaseModel):
    config: Dict[str, Any] = Field(..., description="Configuration data for the analyzer")

# Initialize FastAPI app with enhanced documentation
app = FastAPI(
    title="Realtime Portfolio API",
    description=description,
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Initialize analyzer
analyzer = None

@app.on_event("startup")
async def startup_event():
    global analyzer
    config_path = os.getenv('DATAMAP_CONFIG_PATH', 'config/datamap_config.json')
    try:
        if os.path.exists(config_path):
            analyzer = DataMapAPIAnalyzer(config_path)
    except Exception as e:
        print(f"Error initializing analyzer: {str(e)}")
        raise

@app.post("/initialize", tags=["root"])
async def initialize_analyzer(request: ConfigRequest):
    """Initialize the analyzer with provided configuration"""
    global analyzer
    try:
        # Update configuration with new values
        if analyzer:
            analyzer.update_config(request.config)
        else:
            # Save config to file first
            config_path = os.getenv('DATAMAP_CONFIG_PATH', 'config/datamap_config.json')
            with open(config_path, 'w') as f:
                json.dump(request.config, f, indent=2)
            analyzer = DataMapAPIAnalyzer(config_path)
        
        return {
            "message": "Analyzer initialized successfully",
            "configuration": request.config
        }
    except Exception as e:
        logger.error(f"Error initializing analyzer: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error initializing analyzer: {str(e)}"
        )

@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning API status"""
    return {"message": "Realtime Portfolio API"}

@app.post("/analyze", response_model=AnalysisResponse, tags=["analysis"])
async def analyze_api(request: QueryRequest):
    """Analyze API specification based on natural language query"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    try:
        return analyzer.analyze_api(request.query, request.context, request.format_type)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/api_call", response_model=APICallResponse, tags=["analysis"])
async def get_api_call(request: QueryRequest):
    """Get API call example in context"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    try:
        return analyzer.get_api_call_in_context(request.query, request.context, request.format_type)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/similar", response_model=SimilarResponse, tags=["analysis"])
async def get_similar(request: QueryRequest):
    """Get similar API endpoints with similarity scores"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    similar_api, scores = analyzer.get_similar_api(request.query, request.k)
    return {
        "similar_api": similar_api,
        "scores": scores
    }

@app.post("/endpoint", response_model=EndpointResponse, tags=["endpoints"])
async def get_endpoint(request: EndpointRequest):
    """Get detailed specification information about a specific endpoint"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    return analyzer.get_endpoint_spec(request.endpoint_path)

@app.post("/parameter", response_model=ParameterResponse, tags=["parameters"])
async def get_parameter(request: ParameterRequest):
    """Get detailed information about a specific parameter"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    return analyzer.get_parameter_info(request.endpoint_path, request.parameter_name)

@app.get("/api_summary", response_model=APISummaryResponse, tags=["analysis"])
async def get_api_summary():
    """Get summary of entire API specification"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer not initialized")
    return analyzer.get_api_summary()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

