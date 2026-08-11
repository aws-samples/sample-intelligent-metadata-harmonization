.PHONY: help install install-dev test test-unit test-integration coverage lint format type-check clean build

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package
	pip install -e .

install-dev:  ## Install package with development dependencies
	pip install -e .[dev]

test:  ## Run all tests
	pytest

test-unit:  ## Run unit tests only
	pytest tests/unit

test-integration:  ## Run integration tests only
	pytest tests/integration

coverage:  ## Run tests with coverage report
	pytest --cov=metadata_harmonization_processor --cov-report=html --cov-report=term

lint:  ## Run linting
	flake8 src tests

format:  ## Format code with ruff and isort
	ruff format src tests
	isort src tests

type-check:  ## Run type checking with mypy
	mypy src

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build package
	python -m build

check: lint type-check test  ## Run all checks (lint, type-check, test)

dev-setup: install-dev  ## Set up development environment
	pre-commit install
