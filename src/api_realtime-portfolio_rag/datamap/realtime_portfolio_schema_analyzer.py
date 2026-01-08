from typing import List, Dict, Any, Tuple, Optional
try:
    from .gemini_datamap_rag import GeminiDatamapRAG
except ImportError:
    from datamap.gemini_datamap_rag import GeminiDatamapRAG
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DataMapAPIAnalyzer:
    def __init__(self, api_base_url: str = "", swagger_url: str = "", region_name: str = "us-central1", cache_size: int = 128):
        """Initialize the DataMapAPIAnalyzer with API configuration.
        
        Args:
            api_base_url (str): Base URL for the API to analyze
            swagger_url (str): URL to Swagger/OpenAPI specification
            region_name (str): GCP region name
            cache_size (int): Maximum number of endpoints to cache in memory
        """
        # Get GCP credentials from environment variables
        gcp_credentials = {
            'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY')
        }
        
        self.rag = GeminiDatamapRAG(
            api_base_url=api_base_url,
            swagger_url=swagger_url,
            region_name=region_name,
            gcp_credentials=gcp_credentials,
            cache_size=cache_size
        )
        self._initialize_rag()
    
    def _initialize_rag(self, pattern: Optional[str] = None):
        """Initialize the RAG system with the API specifications."""
        self.rag.build_rag_index(pattern)
    
    def analyze_api(self, query: str, context: str = "api", format_type: str = "json") -> Dict[str, Any]:
        """Analyze the API specification based on a natural language query."""
        analysis = self.rag.get_detailed_api_analysis(query, context, format_type)
        st.write(f"Analysis: {analysis}")
        return {
            "analysis": analysis,
            "query": query
        }
    
    def get_detailed_api_call_in_context(self, query: str, context: str = "api and endpoints", format_type: str = "json") -> Dict[str, Any]:
        """Get detailed API call in context."""
        return self.rag.get_detailed_api_call_in_context(query, context, format_type)
    
    def get_similar_api(self, query: str, k: int = 3) -> Tuple[List[str], List[float]]:
        """Get similar API endpoints with similarity scores."""
        return self.rag.query_api(query, k)
    
    def get_endpoint_spec(self, endpoint_path: str) -> Dict[str, Any]:
        """Get detailed specification information about a specific endpoint."""
        return self.rag.get_endpoint_spec(endpoint_path)
    
    def get_parameter_info(self, endpoint_path: str, parameter_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific parameter."""
        return self.rag.get_parameter_info(endpoint_path, parameter_name)
    
    def get_api_summary(self) -> Dict[str, Any]:
        """Get a summary of the entire API specification."""
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
    st.title("Realtime Portfolio API Analyzer")
    
    # Initialize session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = None
    
    # Check if GCP credentials are available
    if not os.getenv('GOOGLE_API_KEY'):
        st.error("GCP API key not found in environment variables. Please set GOOGLE_API_KEY.")
        return
    
    # API configuration
    col1, col2 = st.columns(2)
    with col1:
        api_base_url = st.text_input("API Base URL:", "")
    with col2:
        swagger_url = st.text_input("Swagger/OpenAPI URL:", "")
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        col1, col2 = st.columns(2)
        with col1:
            region_name = st.text_input("GCP Region:", "us-central1")
        with col2:
            cache_size = st.number_input("Cache Size:", min_value=1, max_value=1000, value=128)
        pattern = st.text_input("Endpoint Pattern (optional):", "")
    
    if st.button("Initialize Analyzer"):
        try:
            with st.spinner("Initializing API analyzer..."):
                st.session_state.analyzer = DataMapAPIAnalyzer(
                    api_base_url=api_base_url,
                    swagger_url=swagger_url,
                    region_name=region_name,
                    cache_size=cache_size
                )
                st.session_state.analyzer._initialize_rag(pattern if pattern else None)
                st.success("Analyzer initialized successfully!")
        except Exception as e:
            st.error(f"Error initializing analyzer: {str(e)}")
    
    if st.session_state.analyzer:
        # Query input
        query = st.text_input("Enter your query about the API specification:")
        
        if query and query.strip():  # Check if query is not empty or just whitespace
            try:
                # log the query context
                context = "api"
                format_type = "JSON"
                st.write(f"Query: {query}")
                st.write(f"Context: {context}")
                st.write(f"Format Type: {format_type}")
                # Analysis tab
                with st.expander("API Analysis"):
                    analysis = st.session_state.analyzer.analyze_api(query, context, format_type)
                    st.write("Analysis:")
                    st.write(analysis["analysis"])
                
                # API call in context tab
                with st.expander("API Call in Context"):
                    api_call = st.session_state.analyzer.get_detailed_api_call_in_context(query, context, format_type)
                    st.write("API Call:")
                    st.write(api_call)
                
                # Similar API tab
                with st.expander("Similar API Endpoints"):
                    similar_api, scores = st.session_state.analyzer.get_similar_api(query)
                    for i, (text, score) in enumerate(zip(similar_api, scores)):
                        st.write(f"Result {i+1} (Score: {score:.4f}):")
                        st.write(text)
                
                # API summary tab
                with st.expander("API Summary"):
                    summary = st.session_state.analyzer.get_api_summary()
                    st.write(f"Total Endpoints: {summary['total_endpoints']}")
                    
                    for endpoint in summary["endpoints"]:
                        with st.expander(f"Endpoint: {endpoint['method']} {endpoint['path']}"):
                            st.write(f"Description: {endpoint['description']}")
                            st.write(f"Tags: {', '.join(endpoint['tags'])}")
                            st.write(f"Parameters ({endpoint['parameter_count']}):")
                            st.write(endpoint["parameters"])
                            st.write(f"Has Request Body: {endpoint['has_request_body']}")
                            st.write(f"Response Codes: {', '.join(endpoint['response_codes'])}")
                            
                            # Show endpoint specification
                            endpoint_spec = st.session_state.analyzer.get_endpoint_spec(endpoint["path"])
                            if endpoint_spec:
                                st.write("Endpoint Details:")
                                df = pd.DataFrame(endpoint_spec.get("parameters", []))
                                if not df.empty:
                                    st.dataframe(df)
                                
                                # Parameter analysis
                                if endpoint_spec.get("parameters"):
                                    selected_parameter = st.selectbox(
                                        "Select a parameter for detailed analysis:",
                                        [param["name"] for param in endpoint_spec["parameters"]],
                                        key=f"param_select_{endpoint['path']}"
                                    )
                                    
                                    if selected_parameter:
                                        parameter_info = st.session_state.analyzer.get_parameter_info(
                                            endpoint["path"],
                                            selected_parameter
                                        )
                                        st.write("Parameter Analysis:")
                                        st.write(f"Name: {parameter_info.get('name', 'N/A')}")
                                        st.write(f"Type: {parameter_info.get('type', 'N/A')}")
                                        st.write(f"Required: {parameter_info.get('required', False)}")
                                        st.write(f"Location: {parameter_info.get('in', 'N/A')}")
                                        st.write(f"Description: {parameter_info.get('description', 'N/A')}")
            except Exception as e:
                st.error(f"Error processing query: {str(e)}")
                st.error("Please try again with a different query or check the logs for more details.")

if __name__ == "__main__":
    create_streamlit_app()

