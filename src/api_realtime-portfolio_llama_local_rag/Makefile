.PHONY: build run_streamlit run_api dev clean test lint help


# Variables
VENV = venv
DOCKER_TAG = latest


# Streamlit app
PORT_STREAMLIT = 8501
DOCKER_FILE_STREAMLIT = streamlit_app.Dockerfile
DOCKER_IMAGE_STREAMLIT = llama-local-datamap-rag-streamlit
DOCKER_CONTAINER_STREAMLIT = llama-local-datamap-rag-streamlit-container


# API app
PORT_API = 8000
DOCKER_FILE_API = llama_local_datamap_api.Dockerfile
DOCKER_IMAGE_API = llama-local-datamap-rag-api
DOCKER_CONTAINER_API = llama-local-datamap-rag-api-container



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

build:
	@echo "Building Docker image..."
	docker build -t $(DOCKER_IMAGE_STREAMLIT):$(DOCKER_TAG) -f $(DOCKER_FILE_STREAMLIT) .
	docker build -t $(DOCKER_IMAGE_API):$(DOCKER_TAG) -f $(DOCKER_FILE_API) .

run_all:
	@echo "Running all Docker containers..."
	docker compose -f docker-compose.yml down 2>/dev/null || true
	docker compose -f docker-compose.yml up --build || true
	@echo "All Docker containers have been started successfully."

run_streamlit:
	@echo "Running Docker container for Streamlit..."
	docker compose -f docker-compose-rag.yml down 2>/dev/null || true
	docker compose -f docker-compose-rag.yml up --build || true
	@echo "All RAG Streamlit Docker containers have been started successfully."

run_api:
	@echo "Running Docker container for API..."
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

