import json
from typing import List, Dict, Any, Tuple, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
try:
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
except ImportError:
    try:
        from langchain_classic.chains import RetrievalQA
        from langchain_classic.prompts import PromptTemplate
    except ImportError:
        from langchain_community.chains import RetrievalQA
        from langchain_core.prompts import PromptTemplate
import os
from dotenv import load_dotenv
import logging
try:
    from .api_swagger_data_source import APISwaggerDataSource
except ImportError:
    from datamap.api_swagger_data_source import APISwaggerDataSource

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def _normalize_openai_base_url(base_url: str) -> str:
    if not base_url:
        return base_url
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"

def _get_env_default(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default

def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default

class LlamaLocalDatamapRAG:
    def __init__(
        self,
        api_base_url: str = "",
        swagger_url: str = "",
        region_name: str = "local",
        llama_config: Optional[Dict[str, str]] = None,
        cache_size: int = 128
    ):
        """Initialize the LlamaLocalDatamapRAG class with local Llama server configuration.
        
        Args:
            api_base_url (str): Base URL for the API to analyze
            swagger_url (str): URL to Swagger/OpenAPI specification
            region_name (str): Local region tag for logging/metadata
            llama_config (Optional[Dict[str, str]]): Dictionary containing Llama server configuration
            cache_size (int): Maximum number of API endpoints to cache in memory
        """
        self.region_name = region_name
        self.api_data_source = APISwaggerDataSource(api_base_url, swagger_url, cache_size)
        
        try:
            if llama_config:
                base_url = llama_config.get("LLAMA_BASE_URL")
                api_key = llama_config.get("LLAMA_API_KEY")
                logger.info("Using provided Llama server configuration")
            else:
                base_url = os.getenv("LLAMA_BASE_URL")
                api_key = os.getenv("LLAMA_API_KEY")
                logger.info("Using Llama server configuration from environment variables")

            if not base_url:
                base_url = "http://host.docker.internal:11434"
                logger.info("LLAMA_BASE_URL not set; defaulting to %s", base_url)

            if not api_key:
                api_key = "local"
                logger.info("LLAMA_API_KEY not set; using default local key")

            openai_base_url = _normalize_openai_base_url(base_url)
            embeddings_provider = _get_env_default("LLAMA_EMBEDDINGS_PROVIDER", "ollama").lower()
            if embeddings_provider == "hf":
                hf_model = _get_env_default("HF_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
                hf_cache = _get_env_default("HF_EMBEDDING_CACHE_DIR", "/embedding_model")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=hf_model,
                    cache_folder=hf_cache,
                )
                logger.info("Embeddings: Using HuggingFace (%s)", hf_model)
            elif embeddings_provider == "ollama":
                embedding_model = _get_env_default("LLAMA_EMBEDDING_MODEL", "nomic-embed-text")
                self.embeddings = OllamaEmbeddings(
                    model=embedding_model,
                    base_url=base_url,
                )
                logger.info("Embeddings: Using Ollama (%s)", embedding_model)
            else:
                embedding_model = _get_env_default("LLAMA_EMBEDDING_MODEL", "nomic-embed-text")
                self.embeddings = OpenAIEmbeddings(
                    model=embedding_model,
                    api_key=api_key,
                    base_url=openai_base_url,
                )
                logger.info("Embeddings: Using Llama server (%s)", embedding_model)

            inference_model = _get_env_default("LLAMA_INFERENCE_MODEL", "llama3.2")
            self.llm = ChatOpenAI(
                model=inference_model,
                api_key=api_key,
                base_url=openai_base_url,
                temperature=0.0,
                max_tokens=10000,
            )
            
            # Test the connection by making a simple embedding request
            test_embedding = self.embeddings.embed_query("test")
            if not test_embedding:
                raise ValueError("Failed to get test embedding from Llama server")
            
            logger.info("Successfully initialized Llama server client and models")
            
        except Exception as e:
            logger.error(f"Failed to initialize Llama server: {str(e)}")
            raise ValueError(f"Failed to initialize Llama server: {str(e)}")
    
    def _prepare_api_text(self, api_specs: List[Dict[str, Any]]) -> str:
        """Convert API specification information to text format for embedding."""
        try:
            text_chunks = []
            for endpoint in api_specs:
                endpoint_text = f"Endpoint: {endpoint['endpoint_path']}\n"
                endpoint_text += f"Method: {endpoint['method']}\n"
                endpoint_text += f"Description: {endpoint.get('description', 'N/A')}\n"
                endpoint_text += f"Tags: {', '.join(endpoint.get('tags', []))}\n"
                
                if endpoint.get('parameters'):
                    endpoint_text += "Parameters:\n"
                    for param in endpoint['parameters']:
                        endpoint_text += f"- {param['name']} ({param.get('type', 'unknown')}, {'required' if param.get('required', False) else 'optional'})\n"
                        if param.get('description'):
                            endpoint_text += f"  Description: {param['description']}\n"
                
                if endpoint.get('request_body'):
                    endpoint_text += f"Request Body: {endpoint['request_body']}\n"
                
                if endpoint.get('responses'):
                    endpoint_text += "Responses:\n"
                    for status_code, response in endpoint['responses'].items():
                        endpoint_text += f"- {status_code}: {response.get('description', 'N/A')}\n"
                        if response.get('schema'):
                            endpoint_text += f"  Schema: {json.dumps(response['schema'], indent=2)}\n"
                
                text_chunks.append(endpoint_text)
            
            return "\n\n".join(text_chunks)
            
        except Exception as e:
            logger.error(f"Error preparing API text: {str(e)}")
            raise ValueError(f"Error preparing API text: {str(e)}")
    
    def build_rag_index(self, pattern: Optional[str] = None):
        """Build the RAG index from API/Swagger specifications.
        
        Args:
            pattern (Optional[str]): Regex pattern to filter endpoints
        """
        try:
            # Get API specifications
            api_specs = self.api_data_source.get_all_endpoints(pattern)
            if not api_specs:
                logger.warning("No API endpoints found; skipping RAG index build")
                self.api_cache = {}
                self.vector_store = None
                return False

            self.api_cache = {item['endpoint_path']: item for item in api_specs}

            # Convert API specs to text
            api_text = self._prepare_api_text(api_specs)
            if not api_text.strip():
                logger.warning("Generated API text is empty; skipping RAG index build")
                self.vector_store = None
                return False

            # Split text into chunks
            chunk_size = _get_env_int("LLAMA_EMBEDDING_CHUNK_SIZE", 2000)
            chunk_overlap = _get_env_int("LLAMA_EMBEDDING_CHUNK_OVERLAP", 200)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            texts = text_splitter.split_text(api_text)

            if not texts:
                logger.warning("No text chunks generated; skipping RAG index build")
                self.vector_store = None
                return False

            # Create FAISS index
            try:
                self.vector_store = FAISS.from_texts(
                    texts=texts,
                    embedding=self.embeddings
                )
                logger.info(f"Successfully built RAG index with {len(texts)} text chunks")
                return True
            except Exception as e:
                logger.error(f"Error creating FAISS index: {str(e)}")
                raise ValueError(f"Failed to create vector store: {str(e)}")

        except Exception as e:
            logger.error(f"Error building RAG index: {str(e)}")
            raise ValueError(f"Error building RAG index: {str(e)}")
    
    def query_api(self, query: str, k: int = 3) -> Tuple[List[str], List[float]]:
        """Query the API specifications using RAG and return relevant information with similarity scores."""
        if not self.vector_store:
            raise ValueError("RAG index not built. Call build_rag_index first.")
        
        try:
            # Get relevant documents
            docs = self.vector_store.similarity_search_with_score(query, k=k)
            
            # Extract text and scores
            texts = [doc[0].page_content for doc in docs]
            scores = [doc[1] for doc in docs]
            
            return texts, scores
            
        except Exception as e:
            logger.error(f"Error querying API: {str(e)}")
            raise ValueError(f"Error querying API: {str(e)}")
    
    def get_detailed_api_analysis(self, query: str = "get all endpoints", context: str = "api", format_type: str = "json") -> str:
        """Get a detailed analysis of the API based on the query."""
        if not self.vector_store:
            raise ValueError("RAG index not built. Call build_rag_index first.")
        
        try:
            # load in stack variables
            query = query
            context = context
            format_type = format_type
            # create prompt template
            prompt_template = (
                """
            Based on the following API specification, context, and query, provide a detailed answer to the analysis in output format, """
                + format_type
                + """ :
            
            Query: """
                + query
                + """
            
            Context: {context}
            
            Please execute the following comprehensive analysis including:
            1. API endpoint structure and relationships
            2. Request/response formats and data types
            3. Authentication and authorization requirements
            4. API usage patterns and best practices
            5. Potential integration issues
            6. Example API calls in """
                + format_type
                + """ format with proper request structure.
            
            In the end of the 6 steps, show for all the detailed answered analysis:
            """
            )
            
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context"]
            )
            
            # Create QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(),
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": prompt,
                    "document_variable_name": "context",
                }
            )
            
            # Get response using invoke with proper input format
            response = qa_chain.invoke({
                "query": query,
            })["result"]
            logger.info(f"Response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error getting API analysis: {str(e)}")
            raise ValueError(f"Error getting API analysis: {str(e)}")

    def get_detailed_api_call_in_context(self, query: str = "get all endpoints", context: str = "api and endpoints", format_type: str = "json") -> str:
        """Get a detailed API call example based on the query."""
        if not self.vector_store:
            raise ValueError("RAG index not built. Call build_rag_index first.")
        
        try:
            # load in stack variables
            query = query
            context = context
            format_type = format_type
            # create prompt template
            prompt_template = (
                """
            Based on the following API specification, context, and query, provide a detailed answer to the analysis in output format, """
                + format_type
                + """ :
            
            Query: """
                + query
                + """
            
            Context: {context}
            
            Please execute internally the following comprehensive analysis including:
            1. API endpoint structure and relationships
            2. Request/response formats and data types
            3. Authentication and authorization requirements
            4. API usage patterns and best practices
            5. Potential integration issues
            6. Example API calls in """
                + format_type
                + """ format with proper request structure.
            
            In the end of the 6 steps, answer only in API call format, following the notation of """
                + format_type
                + """ , remove extra text and comments:
            """
            )
            
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context"]
            )
            
            # Create QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(),
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": prompt,
                    "document_variable_name": "context",
                }
            )
            
            # Get response using invoke with proper input format
            response = qa_chain.invoke({
                "query": query,
            })["result"]
            logger.info(f"Response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error getting API call: {str(e)}")
            raise ValueError(f"Error getting API call: {str(e)}")

    def get_endpoint_spec(self, endpoint_path: str) -> Dict[str, Any]:
        """Get detailed specification information for a specific endpoint."""
        try:
            if endpoint_path not in self.api_cache:
                raise ValueError(f"Endpoint {endpoint_path} not found in cache")
            
            return self.api_cache[endpoint_path]
            
        except Exception as e:
            logger.error(f"Error getting endpoint spec: {str(e)}")
            raise ValueError(f"Error getting endpoint spec: {str(e)}")
    
    def get_parameter_info(self, endpoint_path: str, parameter_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific parameter in an endpoint."""
        try:
            endpoint_spec = self.get_endpoint_spec(endpoint_path)
            if not endpoint_spec:
                raise ValueError(f"Endpoint {endpoint_path} not found")
            
            # Find the parameter
            parameters = endpoint_spec.get('parameters', [])
            for param in parameters:
                if param['name'] == parameter_name:
                    return param
            
            raise ValueError(f"Parameter {parameter_name} not found in endpoint {endpoint_path}")
            
        except Exception as e:
            logger.error(f"Error getting parameter info: {str(e)}")
            raise ValueError(f"Error getting parameter info: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear the APISwaggerDataSource cache."""
        self.api_data_source.clear_cache()

