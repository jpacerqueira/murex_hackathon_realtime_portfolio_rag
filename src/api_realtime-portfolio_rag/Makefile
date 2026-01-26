.PHONY: build run_streamlit run_api dev clean test lint help


# Variables
VENV = venv
GCP_ENV_FILE = gcp/gcp_env_vars
DOCKER_TAG = latest


# Streamlit app
PORT_STREAMLIT = 8501
DOCKER_FILE_STREAMLIT = streamlit_app.Dockerfile
DOCKER_IMAGE_STREAMLIT = gemini-datamap-rag-streamlit
DOCKER_CONTAINER_STREAMLIT = gemini-datamap-rag-streamlit-container


# API app
PORT_API = 8000
DOCKER_FILE_API = gemini_datamap_api.Dockerfile
DOCKER_IMAGE_API = gemini-datamap-rag-api
DOCKER_CONTAINER_API = gemini-datamap-rag-api-container



help:
	@echo "Available commands:"
	@echo "  make load_data_files - Load data files"
	@echo "  make build         - Build the Docker image"
	@echo "  make run_all       - Run the Docker containers for the Streamlit app and the API"
	@echo "  make run_streamlit - Run the Docker container for the Streamlit app"
	@echo "  make run_api       - Run the Docker container for the API"
	@echo "  make dev           - Set up development environment"
	@echo "  make clean         - Clean up Docker resources"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linting"
	@echo "  make help          - Show this help message"

load_data_files:
	@echo "Loading data files..."
	cat ~/Desktop/hackathon/API.txt > ./datamap/API_SAMPLE.txt
	cat ~/Desktop/hackathon/SWAGGER.json > ./datamap/SWAGGER_SAMPLE.json
	@echo "Data files loaded successfully."
	@echo "Load private GCP project and GEMINI_API_KEY"
	cat ~/Desktop/hackathon/gcp_env_vars > ./gcp/gcp_env_vars
	@echo "GCP credentials loaded successfully."

build:
	@echo "Building Docker image..."
	docker build -t $(DOCKER_IMAGE_STREAMLIT):$(DOCKER_TAG) -f $(DOCKER_FILE_STREAMLIT) .
	docker build -t $(DOCKER_IMAGE_API):$(DOCKER_TAG) -f $(DOCKER_FILE_API) .

# Load GCP credentials from file
GEMINI_API_KEY := $(shell grep GEMINI_API_KEY $(GCP_ENV_FILE) | cut -d'"' -f2)

run_all:
	@echo "Running all Docker containers..."
	@if [ ! -f "$(GCP_ENV_FILE)" ]; then \
		echo "Error: $(GCP_ENV_FILE) not found"; \
		exit 1; \
	fi
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
		echo "Error: Gemini API key not found in $(GCP_ENV_FILE)"; \
		exit 1; \
	fi
	echo "GEMINI_API_KEY: $(GEMINI_API_KEY)"
	echo "GEMINI_INFERENCE_MODEL: $(GEMINI_INFERENCE_MODEL)"
	echo "GEMINI_EMBEDDING_MODEL: $(GEMINI_EMBEDDING_MODEL)"
	echo "GCP_PROJECT: $(GCP_PROJECT)"
	mkdir -p ./shared
	cp -rf ../shared/streamlit_theme.css ./shared/streamlit_theme.css
	docker compose -f docker-compose.yml down 2>/dev/null || true
	docker compose -f docker-compose.yml up --build || true
	@echo "All Docker containers have been started successfully."

run_streamlit:
	@echo "Running Docker container with GCP credentials..."
	@if [ ! -f "$(GCP_ENV_FILE)" ]; then \
		echo "Error: $(GCP_ENV_FILE) not found"; \
		exit 1; \
	fi
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
		echo "Error: Gemini API key not found in $(GCP_ENV_FILE)"; \
		exit 1; \
	fi
	docker compose -f docker-compose-rag.yml down 2>/dev/null || true
	docker compose -f docker-compose-rag.yml up --build || true
	@echo "All RAG Streamlit Docker containers have been started successfully."

run_api:
	@echo "Running Docker container with GCP credentials..."
	@if [ ! -f "$(GCP_ENV_FILE)" ]; then \
		echo "Error: $(GCP_ENV_FILE) not found"; \
		exit 1; \
	fi
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
		echo "Error: Gemini API key not found in $(GCP_ENV_FILE)"; \
		exit 1; \
	fi
	docker compose -f docker-compose-api.yml down 2>/dev/null || true
	docker compose -f docker-compose-api.yml up --build || true
	@echo "All API Docker containers have been started successfully."

dev:
	@echo "Setting up development environment..."
	python -m venv $(VENV)
	. $(VENV)/bin/activate && pip install -r requirements.txt
	. $(VENV)/bin/activate && pip install -r requirements-dev.txt

clean:
	@echo "Cleaning up Docker resources..."
	docker stop $$(docker ps -q --filter ancestor=$(DOCKER_IMAGE_STREAMLIT):$(DOCKER_TAG)) 2>/dev/null || true
	docker rm $$(docker ps -a -q --filter ancestor=$(DOCKER_IMAGE_STREAMLIT):$(DOCKER_TAG)) 2>/dev/null || true
	docker rmi $(DOCKER_IMAGE_STREAMLIT):$(DOCKER_TAG) 2>/dev/null || true

test:
	@echo "Running tests..."
	. $(VENV)/bin/activate && python -m pytest tests/

lint:
	@echo "Running linting..."
	. $(VENV)/bin/activate && flake8 .

