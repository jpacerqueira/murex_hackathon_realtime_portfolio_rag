import requests
import json
from typing import List, Dict, Any, Optional, Pattern
import logging
from functools import lru_cache
from datetime import datetime
from dotenv import load_dotenv
import re
from urllib.parse import urlparse
from pathlib import Path

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class APISwaggerDataSource:
    def __init__(
        self,
        api_base_url: str = "",
        swagger_url: str = "",
        swagger_file_path: str = "",
        api_sample_file_path: str = "",
        cache_size: int = 128,
    ):
        """Initialize API/Swagger data source handler.
        
        Args:
            api_base_url (str): Base URL for the API
            swagger_url (str): URL to Swagger/OpenAPI specification
            cache_size (int): Maximum number of endpoints to cache in memory
        """
        self.api_base_url = api_base_url
        self.swagger_url = swagger_url
        self.swagger_file_path = swagger_file_path
        self.api_sample_file_path = api_sample_file_path
        self._cache_size = cache_size
        self._swagger_spec = None

    def _resolve_path(self, file_path: str) -> Optional[Path]:
        """Resolve a file path against cwd or module directory."""
        if not file_path:
            return None
        candidate = Path(file_path)
        if candidate.is_absolute() and candidate.exists():
            return candidate
        cwd_candidate = Path.cwd() / candidate
        if cwd_candidate.exists():
            return cwd_candidate
        module_candidate = Path(__file__).resolve().parent / candidate
        if module_candidate.exists():
            return module_candidate
        logger.warning("File path not found: %s", file_path)
        return None

    def _read_text_file(self, file_path: str) -> Optional[str]:
        resolved = self._resolve_path(file_path)
        if not resolved:
            return None
        try:
            return resolved.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to read file %s: %s", resolved, str(e))
            return None

    def _load_swagger_from_file(self) -> Dict[str, Any]:
        """Load Swagger/OpenAPI specification from a local JSON file."""
        if not self.swagger_file_path:
            return {}
        content = self._read_text_file(self.swagger_file_path)
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Swagger file is not valid JSON: %s", str(e))
            return {}

    def _load_api_sample_text(self) -> Optional[str]:
        """Load API sample text from a local file."""
        if not self.api_sample_file_path:
            return None
        return self._read_text_file(self.api_sample_file_path)

    def _build_api_sample_endpoint(self, sample_text: str) -> Dict[str, Any]:
        """Create a pseudo-endpoint to embed API samples."""
        sample_text = (sample_text or "").strip()
        if len(sample_text) > 8000:
            sample_text = sample_text[:8000]
        return {
            "endpoint_path": "API_SAMPLE",
            "method": "SAMPLE",
            "description": "Sample API usage loaded from a local file.",
            "tags": ["sample"],
            "parameters": [],
            "request_body": sample_text,
            "responses": {
                "200": {
                    "description": "API sample content",
                    "schema": {"sample": sample_text},
                }
            },
            "operation_id": "API_SAMPLE",
        }
        
    def _fetch_swagger_spec(self) -> Dict[str, Any]:
        """Fetch and parse Swagger/OpenAPI specification."""
        if self._swagger_spec is not None:
            return self._swagger_spec

        try:
            swagger_file_spec = self._load_swagger_from_file()
            if swagger_file_spec:
                self._swagger_spec = swagger_file_spec
                return self._swagger_spec

            swagger_url = (self.swagger_url or "").strip()
            if not swagger_url:
                logger.warning("Swagger URL is empty; skipping Swagger fetch")
                self._swagger_spec = {}
                return self._swagger_spec

            if not self._is_valid_url(swagger_url):
                logger.warning("Swagger URL is invalid; skipping Swagger fetch")
                self._swagger_spec = {}
                return self._swagger_spec

            response = requests.get(swagger_url, timeout=30)
            response.raise_for_status()
            self._swagger_spec = response.json()
            return self._swagger_spec
        except Exception as e:
            logger.warning(f"Swagger fetch failed; skipping Swagger spec: {str(e)}")
            self._swagger_spec = {}
            return self._swagger_spec

    def _is_valid_url(self, url: str) -> bool:
        """Validate Swagger URL format."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except Exception:
            return False

    def _fetch_base_url_sample(self) -> Optional[Dict[str, Any]]:
        """Fetch a sample response from the API base URL."""
        api_url = (self.api_base_url or "").strip()
        if not api_url or not self._is_valid_url(api_url):
            return None

        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")

            content: Any
            if "application/json" in content_type:
                try:
                    content = response.json()
                except ValueError:
                    content = response.text
            else:
                content = response.text

            if isinstance(content, str):
                content = content[:2000]

            return {
                "status_code": response.status_code,
                "content_type": content_type,
                "content": content,
            }
        except Exception as e:
            logger.warning(f"Error fetching base URL sample: {str(e)}")
            return None
    
    @lru_cache(maxsize=128)
    def list_endpoints(self, pattern: Optional[str] = None) -> List[str]:
        """List all endpoints in the API specification.
        
        Args:
            pattern (Optional[str]): Regex pattern to filter endpoints
            
        Returns:
            List[str]: List of endpoint paths
        """
        try:
            spec = self._fetch_swagger_spec()
            paths = spec.get('paths', {})
            all_endpoints = []
            
            for path, methods in paths.items():
                for method in methods.keys():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        endpoint_key = f"{method.upper()} {path}"
                        all_endpoints.append(endpoint_key)
            
            if pattern:
                regex = re.compile(pattern)
                all_endpoints = [ep for ep in all_endpoints if regex.search(ep)]
            
            return all_endpoints
        except Exception as e:
            logger.error(f"Error listing endpoints: {str(e)}")
            raise
    
    @lru_cache(maxsize=128)
    def get_endpoint_spec(self, endpoint_key: str) -> Dict[str, Any]:
        """Get specification for a specific endpoint.
        
        Args:
            endpoint_key (str): Endpoint key in format "METHOD /path"
            
        Returns:
            Dict[str, Any]: Endpoint specification
        """
        try:
            spec = self._fetch_swagger_spec()
            paths = spec.get('paths', {})
            
            method, path = endpoint_key.split(' ', 1)
            method = method.lower()
            
            if path not in paths or method not in paths[path]:
                raise ValueError(f"Endpoint {endpoint_key} not found")
            
            endpoint_info = paths[path][method]
            
            # Extract parameters
            parameters = []
            for param in endpoint_info.get('parameters', []):
                param_info = {
                    'name': param.get('name', ''),
                    'in': param.get('in', ''),
                    'required': param.get('required', False),
                    'type': param.get('schema', {}).get('type', 'string'),
                    'description': param.get('description', '')
                }
                parameters.append(param_info)
            
            # Extract request body
            request_body = None
            if 'requestBody' in endpoint_info:
                content = endpoint_info['requestBody'].get('content', {})
                if content:
                    # Get first content type
                    content_type = list(content.keys())[0]
                    schema = content[content_type].get('schema', {})
                    request_body = json.dumps(schema, indent=2)
            
            # Extract responses
            responses = {}
            for status_code, response_info in endpoint_info.get('responses', {}).items():
                response_data = {
                    'description': response_info.get('description', ''),
                    'schema': None
                }
                if 'content' in response_info:
                    content = response_info['content']
                    if content:
                        content_type = list(content.keys())[0]
                        schema = content[content_type].get('schema', {})
                        response_data['schema'] = schema
                responses[status_code] = response_data
            
            return {
                "endpoint_path": path,
                "method": method.upper(),
                "description": endpoint_info.get('description', endpoint_info.get('summary', '')),
                "tags": endpoint_info.get('tags', []),
                "parameters": parameters,
                "request_body": request_body,
                "responses": responses,
                "operation_id": endpoint_info.get('operationId', '')
            }
        except Exception as e:
            logger.error(f"Error getting endpoint spec for {endpoint_key}: {str(e)}")
            raise
    
    def get_all_endpoints(self, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get specification information for all endpoints.
        
        Args:
            pattern (Optional[str]): Regex pattern to filter endpoints
            
        Returns:
            List[Dict[str, Any]]: List of endpoint specifications
        """
        try:
            endpoint_keys = self.list_endpoints(pattern)
            api_specs: List[Dict[str, Any]] = []
            if endpoint_keys:
                api_specs = [self.get_endpoint_spec(key) for key in endpoint_keys]
            else:
                api_url = (self.api_base_url or "").strip()
                if api_url and self._is_valid_url(api_url):
                    sample = self._fetch_base_url_sample()
                    response_schema = None
                    response_description = "Base URL provided without Swagger. Limited endpoint details."
                    if sample:
                        response_description += (
                            f" Status: {sample.get('status_code')}. "
                            f"Content-Type: {sample.get('content_type')}"
                        )
                        content = sample.get("content")
                        if isinstance(content, (dict, list)):
                            response_schema = content
                        elif content:
                            response_schema = {"sample": content}

                    api_specs = [
                        {
                            "endpoint_path": api_url,
                            "method": "GET",
                            "description": "API base URL provided without Swagger. Limited endpoint details.",
                            "tags": ["base-url"],
                            "parameters": [],
                            "request_body": None,
                            "responses": {
                                "200": {
                                    "description": response_description,
                                    "schema": response_schema,
                                }
                            },
                            "operation_id": "GET_BASE_URL",
                        }
                    ]

            sample_text = self._load_api_sample_text()
            if sample_text:
                api_specs.append(self._build_api_sample_endpoint(sample_text))

            return api_specs
        except Exception as e:
            logger.error(f"Error getting all endpoints: {str(e)}")
            raise
    
    def get_parameter_info(self, endpoint_key: str, parameter_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific parameter.
        
        Args:
            endpoint_key (str): Endpoint key in format "METHOD /path"
            parameter_name (str): Name of the parameter to analyze
            
        Returns:
            Dict[str, Any]: Parameter information
        """
        try:
            endpoint_spec = self.get_endpoint_spec(endpoint_key)
            for param in endpoint_spec.get('parameters', []):
                if param['name'] == parameter_name:
                    return param
            raise ValueError(f"Parameter {parameter_name} not found in endpoint {endpoint_key}")
        except Exception as e:
            logger.error(f"Error getting parameter info for {parameter_name} in {endpoint_key}: {str(e)}")
            raise
    
    def clear_cache(self) -> None:
        """Clear the LRU cache for both endpoint listing and specification retrieval."""
        self.list_endpoints.cache_clear()
        self.get_endpoint_spec.cache_clear()
        self._swagger_spec = None

