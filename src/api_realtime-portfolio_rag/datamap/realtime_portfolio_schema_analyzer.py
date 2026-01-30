from typing import List, Dict, Any, Tuple, Optional
try:
    from .gemini_datamap_rag import GeminiDatamapRAG
except ImportError:
    from datamap.gemini_datamap_rag import GeminiDatamapRAG
import streamlit as st
import pandas as pd
import os
import json
import requests
from dotenv import load_dotenv
import warnings
from urllib.parse import urlparse
from pathlib import Path

# Load environment variables
load_dotenv()

class DataMapAPIAnalyzer:
    def __init__(
        self,
        api_base_url: str = "",
        swagger_url: str = "",
        swagger_file_path: str = "",
        api_sample_file_path: str = "",
        region_name: str = "us-central1",
        cache_size: int = 128,
    ):
        """Initialize the DataMapAPIAnalyzer with API configuration.
        
        Args:
            api_base_url (str): Base URL for the API to analyze
            swagger_url (str): URL to Swagger/OpenAPI specification
            region_name (str): GCP region name
            cache_size (int): Maximum number of endpoints to cache in memory
        """
        # Get GCP credentials from environment variables
        gcp_credentials = {
            'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        }
        
        self.rag = GeminiDatamapRAG(
            api_base_url=api_base_url,
            swagger_url=swagger_url,
            swagger_file_path=swagger_file_path,
            api_sample_file_path=api_sample_file_path,
            region_name=region_name,
            gcp_credentials=gcp_credentials,
            cache_size=cache_size,
        )
        self.rag_ready = False
        self._initialize_rag()
    
    def _initialize_rag(self, pattern: Optional[str] = None) -> bool:
        """Initialize the RAG system with the API specifications."""
        built = self.rag.build_rag_index(pattern)
        self.rag_ready = bool(built)
        return self.rag_ready
    
    def analyze_api(self, query: str, context: str = "murex trade api", format_type: str = "json") -> Dict[str, Any]:
        """Analyze the API specification based on a natural language query."""
        if not self.rag_ready:
            raise ValueError("RAG index not built. Initialize the analyzer with a valid Swagger URL.")
        analysis = self.rag.get_detailed_api_analysis(query, context, format_type)
        st.write(f"Analysis: {analysis}")
        return {
            "analysis": analysis,
            "query": query
        }
    
    def get_detailed_api_call_in_context(self, query: str, context: str = "api and endpoints", format_type: str = "json") -> Dict[str, Any]:
        """Get detailed API call in context."""
        if not self.rag_ready:
            raise ValueError("RAG index not built. Initialize the analyzer with a valid Swagger URL.")
        return self.rag.get_detailed_api_call_in_context(query, context, format_type)
    
    def get_similar_api(self, query: str, k: int = 3) -> Tuple[List[str], List[float]]:
        """Get similar API endpoints with similarity scores."""
        if not self.rag_ready:
            raise ValueError("RAG index not built. Initialize the analyzer with a valid Swagger URL.")
        return self.rag.query_api(query, k)
    
    def get_endpoint_spec(self, endpoint_path: str) -> Dict[str, Any]:
        """Get detailed specification information about a specific endpoint."""
        if not self.rag_ready:
            raise ValueError("RAG index not built. Initialize the analyzer with a valid Swagger URL.")
        return self.rag.get_endpoint_spec(endpoint_path)
    
    def get_parameter_info(self, endpoint_path: str, parameter_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific parameter."""
        if not self.rag_ready:
            raise ValueError("RAG index not built. Initialize the analyzer with a valid Swagger URL.")
        return self.rag.get_parameter_info(endpoint_path, parameter_name)
    
    def get_api_summary(self) -> Dict[str, Any]:
        """Get a summary of the entire API specification."""
        if not self.rag_ready:
            raise ValueError("RAG index not built. Initialize the analyzer with a valid Swagger URL.")
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

def create_streamlit_app():
    """Create a Streamlit app for interacting with the API analyzer."""
    def _is_valid_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except Exception:
            return False

    def _parse_analysis_payload(raw: Any) -> Optional[Dict[str, Any]]:
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str):
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _parse_prism_payload(raw: Any) -> Optional[Dict[str, Any]]:
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str):
            return None
        text = raw.strip()
        if "```" in text:
            start = text.find("```")
            end = text.rfind("```")
            if start != -1 and end != -1 and end > start:
                fenced = text[start + 3 : end]
                fenced = fenced.lstrip()
                if fenced.lower().startswith("json"):
                    fenced = fenced[4:].lstrip()
                text = fenced.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _apply_dxc_theme() -> None:
        st.set_page_config(
            page_title="Realtime Portfolio API Analyzer",
            page_icon="📈",
            layout="wide",
        )
        candidate_paths = [
            Path("/app/shared/streamlit_theme.css"),
            Path(__file__).resolve().parents[2] / "shared" / "streamlit_theme.css",
        ]
        css = None
        for path in candidate_paths:
            if path.exists():
                try:
                    css = path.read_text(encoding="utf-8")
                    break
                except OSError as exc:
                    st.warning(f"Unable to load theme file: {exc}")
                    return
        if not css:
            st.warning("Theme file missing: /app/shared/streamlit_theme.css")
            return

        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    _apply_dxc_theme()

    st.title("Realtime Portfolio API Analyzer")
    
    # Initialize session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = None
    
    # Check if GCP credentials are available
    if not (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')):
        st.error("Gemini API key not found in environment variables. Please set GEMINI_API_KEY.")
        return
    
    # Learning source selection
    source_choice = st.radio("Learn API from:", ["URLs", "Local files"], horizontal=True)
    use_files = source_choice == "Local files"

    # API configuration
    col1, col2 = st.columns(2)
    with col1:
        api_base_url = st.text_input("API Base URL:", "", disabled=use_files)
    with col2:
        swagger_url = st.text_input("Swagger/OpenAPI URL:", "", disabled=use_files)

    if use_files:
        file_col1, file_col2 = st.columns(2)
        with file_col1:
            api_sample_file_path = st.text_input("API Sample File Path:", "/app/datamap/API_SAMPLE.txt")
        with file_col2:
            swagger_file_path = st.text_input("Swagger File Path:", "/app/datamap/SWAGGER_SAMPLE.json")
    else:
        api_sample_file_path = ""
        swagger_file_path = ""
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        col1, col2 = st.columns(2)
        with col1:
            region_name = st.text_input("GCP Region:", "us-central1")
        with col2:
            cache_size = st.number_input("Cache Size:", min_value=1, max_value=1000, value=128)
        pattern = st.text_input("Endpoint Pattern (optional):", "")
        mock_base_url = st.text_input(
            "Prism Mock Base URL:",
            os.getenv("PRISM_MOCK_BASE_URL", "http://prism-mock:4010"),
        )
    
    if st.button("Initialize Analyzer"):
        try:
            with st.spinner("Initializing API analyzer..."):
                if use_files:
                    swagger_file_exists = bool(swagger_file_path and os.path.exists(swagger_file_path))
                    api_sample_exists = bool(api_sample_file_path and os.path.exists(api_sample_file_path))
                    if not swagger_file_exists:
                        warning_msg = (
                            "Swagger file path is missing or invalid. "
                            "No Swagger endpoints will be learned from files."
                        )
                        st.warning(warning_msg)
                        warnings.warn(warning_msg)
                    if not api_sample_exists:
                        warning_msg = (
                            "API sample file path is missing or invalid. "
                            "No API sample content will be learned from files."
                        )
                        st.warning(warning_msg)
                        warnings.warn(warning_msg)
                else:
                    swagger_url_clean = (swagger_url or "").strip()
                    swagger_valid = _is_valid_url(swagger_url_clean)
                    api_url_clean = (api_base_url or "").strip()
                    api_url_valid = _is_valid_url(api_url_clean)
                    if not swagger_url_clean or not swagger_valid:
                        if api_url_valid:
                            warning_msg = (
                                "Swagger URL is optional. Initializing embeddings from the API Base URL only "
                                "because the Swagger URL is empty or invalid."
                            )
                        else:
                            warning_msg = (
                                "Swagger URL is optional. Initializing without learning embeddings because both "
                                "Swagger URL and API Base URL are empty or invalid."
                            )
                        st.warning(warning_msg)
                        warnings.warn(warning_msg)

                api_base_url_value = "" if use_files else api_base_url
                swagger_url_value = "" if use_files else swagger_url

                st.session_state.analyzer = DataMapAPIAnalyzer(
                    api_base_url=api_base_url_value,
                    swagger_url=swagger_url_value,
                    swagger_file_path=swagger_file_path,
                    api_sample_file_path=api_sample_file_path,
                    region_name=region_name,
                    cache_size=cache_size
                )
                built = st.session_state.analyzer._initialize_rag(pattern if pattern else None)
                if built:
                    st.success("Analyzer initialized successfully!")
                else:
                    st.warning(
                        "Analyzer initialized, but no Swagger endpoints were learned. "
                        "Check the Swagger URL if you expect embeddings."
                    )

                st.session_state.prism_mock_base_url = mock_base_url
                try:
                    token_url = f"{mock_base_url.rstrip('/')}/auth/token"
                    response = requests.post(token_url, timeout=10)
                    response.raise_for_status()
                    data = response.json() if response.content else {}
                    token = data.get("access_token") or data.get("token")
                    if token:
                        st.session_state.prism_access_token = token
                        st.info("Prism mock token retrieved during initialization.")
                    else:
                        st.warning("Prism mock token not found in response.")
                except Exception as e:
                    st.warning(f"Prism mock token request failed: {str(e)}")
        except Exception as e:
            st.error(f"Error initializing analyzer: {str(e)}")
    
    if st.session_state.analyzer and st.session_state.analyzer.rag_ready:
        # Query input
        query = st.text_input("Enter your query about the API specification:")
        
        if query and query.strip():  # Check if query is not empty or just whitespace
            try:
                if st.session_state.get("last_query") != query:
                    st.session_state.last_query = query
                    st.session_state.run_analysis = False
                    st.session_state.api_call_result = None

                if st.button("Start API Analysis"):
                    st.session_state.run_analysis = True

                # log the query context
                context = "murex trade api"
                format_type = "JSON"
                st.write(f"Query: {query}")
                st.write(f"Context: {context}")
                st.write(f"Format Type: {format_type}")
                # Analysis tab
                analysis = None
                if st.session_state.get("run_analysis"):
                    with st.expander("API Analysis"):
                        analysis = st.session_state.analyzer.analyze_api(query, context, format_type)
                        st.write("Analysis:")
                        st.write(analysis["analysis"])
                
                api_call = st.session_state.get("api_call_result")
                if api_call:
                    with st.expander("API steps in Context"):
                        st.write("API Call:")
                        st.write(api_call)

                with st.expander("Prism Mock Execution"):
                    mock_base_url = st.session_state.get(
                        "prism_mock_base_url",
                        os.getenv("PRISM_MOCK_BASE_URL", "http://prism-mock:4010"),
                    )
                    default_view_id = "44a30c97-a4c1-407e-8293-ecafd163e299"
                    view_id = st.text_input("View ID (for {viewId}):", default_view_id)

                    st.write("Token request (fixed):")
                    st.code("curl -X POST http://prism-mock:4010/auth/token")
                    st.write("Token response (example):")
                    st.json(
                        {
                            "access_token": "prism-static-token",
                            "token_type": "Bearer",
                            "expires_in": 3600,
                        }
                    )

                    current_token = st.session_state.get("prism_access_token", "")
                    if current_token:
                        st.write(f"Token loaded: {current_token[:10]}...")
                    else:
                        st.warning("No token loaded. Initialize the analyzer to fetch one.")

                    if current_token:
                        if st.button("Validate API Steps"):
                            api_call = st.session_state.analyzer.get_detailed_api_call_in_context(
                                query, context, format_type
                            )
                            st.session_state.api_call_result = api_call

                    if not api_call:
                        st.info("Validate API Steps to generate the mock steps.")
                        api_call_payload = None
                    else:
                        api_call_obj = api_call if isinstance(api_call, dict) else {"api_call": api_call}
                        api_call_payload = _parse_prism_payload(api_call_obj.get("api_call"))
                        st.info(f"JP - debugging API call payload: {api_call_payload}")
                    if not api_call_payload:
                        st.info("API call payload is not JSON; cannot extract steps.")
                    else:
                        if isinstance(api_call_payload, list):
                            steps = api_call_payload
                            api_calls = []
                            for step in steps:
                                request_info = step.get("request") or {}
                                endpoint = request_info.get("endpoint") or ""
                                api_calls.append(
                                    {
                                        "step": step.get("description")
                                        or step.get("action")
                                        or f"Step {step.get('step', '')}".strip(),
                                        "request": {
                                            "method": request_info.get("method") or "GET",
                                            "url": endpoint,
                                            "headers": request_info.get("headers") or {},
                                            "body": request_info.get("body"),
                                        },
                                    }
                                )
                        elif isinstance(api_call_payload, dict) and "api_workflow" in api_call_payload:
                            steps = api_call_payload.get("api_workflow") or []
                            api_calls = []
                            for step in steps:
                                request_info = step.get("request") or {}
                                endpoint = request_info.get("endpoint") or ""
                                api_calls.append(
                                    {
                                        "step": step.get("description")
                                        or step.get("action")
                                        or f"Step {step.get('step', '')}".strip(),
                                        "request": {
                                            "method": request_info.get("method") or "GET",
                                            "url": endpoint,
                                            "headers": request_info.get("headers") or {},
                                            "body": request_info.get("body"),
                                        },
                                    }
                                )
                        else:
                            steps = api_call_payload.get("steps") or []
                            api_calls = api_call_payload.get("api_calls") or []
                            if steps and not api_calls:
                                for step in steps:
                                    action = (step.get("action") or "").strip()
                                    method = "GET"
                                    url = ""
                                    if action:
                                        parts = action.split(" ", 1)
                                        if len(parts) == 2:
                                            method = parts[0].upper()
                                            url = parts[1].strip()
                                        else:
                                            url = action
                                    api_calls.append(
                                        {
                                            "step": step.get("description")
                                            or f"Step {step.get('step_id', '')}".strip(),
                                            "request": {
                                                "method": method,
                                                "url": url,
                                                "headers": step.get("headers") or {},
                                                "body": step.get("request_body"),
                                            },
                                        }
                                    )

                        if steps:
                            st.write("Execution Steps:")
                            for step in steps:
                                if isinstance(step, dict):
                                    label = step.get("description") or step.get("action") or str(step)
                                    st.write(f"- {label}")
                                else:
                                    st.write(f"- {step}")

                        if api_calls and st.button("Run Steps with Prism Mock"):
                            if not current_token:
                                st.warning("Please retrieve a token first.")
                            else:
                                for call in api_calls:
                                    request_info = call.get("request", {})
                                    method = (request_info.get("method") or "GET").upper()
                                    url = request_info.get("url") or ""
                                    parsed = urlparse(url)
                                    path = parsed.path or ""
                                    if parsed.query:
                                        path = f"{path}?{parsed.query}"
                                    target_url = f"{mock_base_url.rstrip('/')}{path}"
                                    target_url = target_url.replace(
                                        "{viewId}",
                                        view_id.strip() if view_id.strip() else default_view_id,
                                    )

                                    headers = dict(request_info.get("headers") or {})
                                    headers["Authorization"] = f"Bearer {current_token}"
                                    body = request_info.get("body")

                                    st.write(f"{call.get('step', 'Step')}: {method} {target_url}")
                                    try:
                                        response = requests.request(
                                            method,
                                            target_url,
                                            headers=headers,
                                            json=body if body else None,
                                            timeout=15,
                                            allow_redirects=False,
                                        )
                                        st.write(f"Status: {response.status_code}")
                                        if response.status_code in {301, 302, 303, 307, 308}:
                                            location = response.headers.get("Location", "")
                                            if location:
                                                if location.startswith("http"):
                                                    follow_url = location
                                                else:
                                                    follow_url = f"{mock_base_url.rstrip('/')}{location}"
                                                st.write(f"Redirecting to: {follow_url}")
                                                follow_resp = requests.get(
                                                    follow_url,
                                                    headers={"Authorization": f"Bearer {current_token}"},
                                                    timeout=15,
                                                )
                                                st.write(f"Redirect status: {follow_resp.status_code}")
                                                try:
                                                    st.json(follow_resp.json())
                                                except ValueError:
                                                    st.write(follow_resp.text)
                                                continue
                                        try:
                                            st.json(response.json())
                                        except ValueError:
                                            st.write(response.text)
                                    except Exception as e:
                                        st.error(f"Request failed: {str(e)}")
                
            except Exception as e:
                st.error(f"Error processing query: {str(e)}")
                st.error("Please try again with a different query or check the logs for more details.")
    elif st.session_state.analyzer and not st.session_state.analyzer.rag_ready:
        st.warning("RAG index not built yet. Initialize with a valid Swagger URL to enable queries.")

if __name__ == "__main__":
    create_streamlit_app()

