# Copyright © Amazon.com and Affiliates: This deliverable is considered Developed Content as defined in the AWS Service
# Terms and the SOW between the parties dated 2025.

# Makefile for metadata harmonization API

.PHONY: help test test-unit test-integration test-cov clean lint format install run-local run-cloud run-prod

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync

test:  ## Run all tests
	pytest

test-unit:  ## Run unit tests only
	pytest tests/unit/ -m "not slow"

test-integration:  ## Run integration tests only
	pytest tests/integration/ -m "not slow"

test-cov:  ## Run tests with coverage report
	pytest --cov=metadata_harmonization_api --cov-report=term-missing --cov-report=html

test-fast:  ## Run fast tests only (exclude slow tests)
	pytest -m "not slow"

test-slow:  ## Run slow tests only
	pytest -m "slow"

test-aws:  ## Run AWS-dependent tests
	pytest -m "aws"

test-watch:  ## Run tests in watch mode
	pytest --looponfail

clean:  ## Clean up test artifacts
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:  ## Run linting
	ruff check .

format:  ## Format code
	ruff format .

check:  ## Run all checks (lint + test)
	make lint
	make test-fast

# Environment-specific run targets

run-local:  ## Run API in local development mode
	@echo "Starting API in local development mode..."
	@echo "Using local storage backends (file system, local job status)"
	export PROCESSOR_ENVIRONMENT=local && \
	export API_ENABLE_AUTH=false && \
	export PROCESSOR_JOB_STATUS_SAVER_TYPE=local && \
	export PROCESSOR_RESULT_SAVER_TYPE=local && \
	export PROCESSOR_SESSION_TYPE=file && \
	export PROCESSOR_LOCAL_DEVELOPMENT_MODE=true && \
	export PROCESSOR_ENABLE_REDIS_CACHE=false && \
	export PROCESSOR_ENABLE_MEMORY_CACHE=true && \
	uvicorn metadata_harmonization_api.api.main:app --reload --host 0.0.0.0 --port 8080

run-cloud:  ## Run API in cloud development mode (with AWS services)
	@echo "Starting API in cloud development mode..."
	@echo "Using AWS services (DynamoDB, S3, Redis)"
	export PROCESSOR_ENVIRONMENT=cloud && \
	export API_ENABLE_AUTH=true && \
	export PROCESSOR_JOB_STATUS_SAVER_TYPE=dynamodb && \
	export PROCESSOR_JOB_STATUS_TABLE_NAME=metadata-upload-jobs && \
	export PROCESSOR_RESULT_SAVER_TYPE=s3 && \
	export PROCESSOR_RESULTS_S3_BUCKET=metadata-validation-results && \
	export PROCESSOR_RESULTS_S3_PREFIX=results/ && \
	export PROCESSOR_SESSION_TYPE=s3 && \
	export PROCESSOR_S3_BUCKET=metadata-processor-sessions && \
	export PROCESSOR_S3_PREFIX=sessions/ && \
	export PROCESSOR_LOCAL_DEVELOPMENT_MODE=false && \
	export PROCESSOR_ENABLE_REDIS_CACHE=true && \
	export PROCESSOR_ENABLE_MEMORY_CACHE=false && \
	uvicorn metadata_harmonization_api.api.main:app --reload --host 0.0.0.0 --port 8080

run-prod:  ## Run API in production mode
	@echo "Starting API in production mode..."
	@echo "Using production configuration with authentication enabled"
	export PROCESSOR_ENVIRONMENT=cloud && \
	export API_ENABLE_AUTH=true && \
	export PROCESSOR_JOB_STATUS_SAVER_TYPE=dynamodb && \
	export PROCESSOR_RESULT_SAVER_TYPE=s3 && \
	export PROCESSOR_SESSION_TYPE=s3 && \
	export PROCESSOR_LOCAL_DEVELOPMENT_MODE=false && \
	export PROCESSOR_ENABLE_REDIS_CACHE=true && \
	uvicorn metadata_harmonization_api.api.main:app --host 0.0.0.0 --port 8080 --workers 4

# Configuration helpers

show-config:  ## Show current configuration (local mode)
	@echo "Current configuration (local mode):"
	@echo "PROCESSOR_ENVIRONMENT=local"
	@echo "API_ENABLE_AUTH=false"
	@echo "PROCESSOR_JOB_STATUS_SAVER_TYPE=local"
	@echo "PROCESSOR_RESULT_SAVER_TYPE=local"
	@echo "PROCESSOR_SESSION_TYPE=file"

show-config-cloud:  ## Show current configuration (cloud mode)
	@echo "Current configuration (cloud mode):"
	@echo "PROCESSOR_ENVIRONMENT=cloud"
	@echo "API_ENABLE_AUTH=true"
	@echo "PROCESSOR_JOB_STATUS_SAVER_TYPE=dynamodb"
	@echo "PROCESSOR_RESULT_SAVER_TYPE=s3"
	@echo "PROCESSOR_SESSION_TYPE=s3"

# Development helpers

dev-setup:  ## Set up development environment
	@echo "Setting up development environment..."
	make install
	@echo "Creating local directories..."
	mkdir -p job_status
	mkdir -p validation-results
	mkdir -p sessions
	@echo "Development environment ready!"
	@echo "Run 'make run-local' to start the API in local mode"

dev-clean:  ## Clean development artifacts
	@echo "Cleaning development artifacts..."
	rm -rf job_status/
	rm -rf validation-results/
	rm -rf sessions/
	make clean
	@echo "Development environment cleaned!"
