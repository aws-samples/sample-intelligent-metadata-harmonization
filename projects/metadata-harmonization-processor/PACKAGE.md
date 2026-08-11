# Package Configuration

This document describes the package configuration for the metadata-harmonization-processor.

**Development Note**: The `strands-agents` dependency is configured in `pyproject.toml` as a required dependency. The core `MetadataHarmonizationProcessor` class is fully implemented with complete pipeline orchestration using AWS Strands MultiAgentBase architecture for workflow orchestration and session management.

## Package Structure

The package follows Python packaging best practices with:

- **setuptools** build system
- **src-layout** for better isolation
- **pyproject.toml** for modern configuration
- **pytest** for testing with asyncio support
- **Pluggable architecture** with abstract interfaces for extensibility

### Key Components

- **Processor**: Main `MetadataHarmonizationProcessor` orchestration class with complete pipeline management
- **Interfaces**: Abstract base classes for job status persistence (`JobStatusSaver`) and schema collection (`SchemaCollector`)
- **Models**: Pydantic data models for validation results, processor state, and configuration
- **Implementations**: Concrete implementations for AWS services (DynamoDB, S3, etc.)
- **Nodes**: Processing stages designed for AWS Strands integration, including semantic search prediction using AI embeddings and pattern-based prediction for data correction

## Dependencies

### Core Dependencies

- **pydantic**: Data validation and settings management (>=2.0.0)
- **pandas**: Data manipulation and analysis (>=1.5.0)
- **boto3/botocore**: AWS SDK for Python (>=1.26.0/1.29.0)
- **redis**: Redis client for caching (>=4.5.0)
- **PyYAML**: YAML configuration parsing (>=6.0)
- **scikit-learn**: Machine learning utilities (>=1.2.0)
- **numpy**: Numerical computing for embedding operations (>=1.21.0)
- **strands-agents**: AWS Strands workflow orchestration (>=0.1.0) - *Required dependency for MultiAgentBase architecture*

### Development Dependencies

- **pytest**: Testing framework with asyncio support
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **black**: Code formatting (88 character line length)
- **isort**: Import sorting
- **mypy**: Static type checking
- **flake8**: Linting
- **pre-commit**: Git hooks for code quality
- **moto**: AWS service mocking for tests
- **fakeredis**: Redis mocking for tests

## Installation Options

```bash
# Basic installation
pip install -e .

# With development tools
pip install -e .[dev]

# With testing tools only
pip install -e .[test]

# With documentation tools
pip install -e .[docs]
```

## Code Quality Configuration

### Black (Code Formatting)
- Line length: 88 characters
- Target Python version: 3.9+
- Excludes: build directories, .git, .venv, etc.

### isort (Import Sorting)
- Profile: black (compatible with Black)
- Multi-line output: 3
- Known first party: metadata_harmonization_processor

### mypy (Type Checking)
- Python version: 3.9
- Strict mode enabled for most checks
- Ignores missing imports for external libraries

### pytest (Testing)
- Asyncio mode: auto
- Test markers: unit, integration, slow
- Coverage source: src/metadata_harmonization_processor
- Excludes test files from coverage

## Build Configuration

- **Build system**: setuptools with wheel support
- **Package discovery**: Automatic from src/ directory
- **Python requirement**: >=3.9
- **Classifiers**: Development Status Alpha, Python 3.9-3.11 support

## Testing Configuration

The package supports multiple test categories:

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with coverage
pytest --cov=metadata_harmonization_processor --cov-report=html
```

## Development Workflow

1. Install with development dependencies: `pip install -e .[dev]`
2. Set up pre-commit hooks: `pre-commit install`
3. Make changes and run tests: `pytest`
4. Check code quality: `black src tests && isort src tests && mypy src`
5. Commit changes (pre-commit hooks will run automatically)

## Package Metadata

- **Name**: metadata-harmonization-processor
- **Version**: 0.1.0
- **Description**: A standalone Python package for metadata harmonization using AWS Strands
- **Author**: Data Harmonization Team
- **Keywords**: metadata, harmonization, aws, strands, validation
- **Python Support**: 3.9, 3.10, 3.11
