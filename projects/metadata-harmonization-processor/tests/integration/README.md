# Integration Tests

This directory contains comprehensive integration tests for the metadata harmonization processor.

## Test Files

### test_end_to_end_pipeline.py
Tests the complete metadata processing workflow including:
- File session management with AWS Strands FileSessionManager
- S3 session management with AWS Strands S3SessionManager
- Redis-enabled caching configuration
- Redis-disabled with in-memory cache configuration
- No-caching configuration
- Error scenarios and recovery mechanisms
- Job status tracking throughout processing
- State management and recovery
- Concurrent processing sessions
- Large dataset processing performance

### test_aws_services.py
Tests AWS service integrations including:
- DynamoDB integration for job status persistence
- S3 integration for session management
- Redis integration for caching (using fakeredis)
- Amazon Bedrock integration for embeddings
- SageMaker integration for embeddings
- Integrated AWS services workflow
- AWS service failure recovery
- AWS credentials and permissions handling
- AWS service timeouts and retries

## Running the Tests

### Prerequisites

Install the test dependencies:

```bash
pip install -e ".[test]"
```

Or install individual dependencies:

```bash
pip install pytest pytest-asyncio pytest-mock moto[s3,dynamodb] fakeredis
```

### Running All Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ --cov=metadata_harmonization_processor --cov-report=html

# Run only integration marked tests
pytest -m integration tests/integration/ -v
```

### Running Specific Test Files

```bash
# Run end-to-end pipeline tests
pytest tests/integration/test_end_to_end_pipeline.py -v

# Run AWS services tests
pytest tests/integration/test_aws_services.py -v
```

### Running Specific Test Cases

```bash
# Run a specific test method
pytest tests/integration/test_end_to_end_pipeline.py::TestEndToEndPipeline::test_complete_processing_workflow_file_session -v

# Run tests matching a pattern
pytest tests/integration/ -k "redis" -v
```

## Test Configuration

The integration tests use:
- **moto** for mocking AWS services (DynamoDB, S3, Bedrock)
- **fakeredis** for mocking Redis operations
- **pytest-asyncio** for async test support
- **pytest-mock** for advanced mocking capabilities
- **tempfile** (built-in) for temporary file and directory handling in tests

## Test Data

Tests create temporary:
- Schema directories with JSON schema files
- Configuration files (YAML)
- Sample metadata DataFrames
- Mock AWS resources (DynamoDB tables, S3 buckets)

All test data is cleaned up automatically after test completion.

## Test Markers

Tests are marked with:
- `@pytest.mark.integration` - Integration test marker
- `@pytest.mark.asyncio` - Async test marker
- `@mock_aws` - AWS service mocking decorator

## Performance Considerations

Some tests (like large dataset processing) may take longer to run. Use pytest's `-x` flag to stop on first failure during development:

```bash
pytest tests/integration/ -x -v
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure:
1. The package is installed in development mode: `pip install -e .`
2. Test dependencies are installed: `pip install -e ".[test]"`
3. You're running from the project root directory

### AWS Service Errors
Integration tests use mocked AWS services. If you see AWS-related errors:
1. Ensure `moto` is installed with the correct extras: `pip install "moto[s3,dynamodb]"`
2. Check that `@mock_aws` decorators are properly applied
3. Verify mock AWS resources are created in test fixtures

### Redis Errors
Redis tests use `fakeredis`. If you encounter Redis errors:
1. Ensure `fakeredis` is installed: `pip install fakeredis`
2. Check that Redis mocking is properly configured in test setup
