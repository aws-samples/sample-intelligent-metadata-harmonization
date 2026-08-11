# Metadata API Configuration

This document describes the configuration options for the Metadata Validation API.

## Configuration File Location

The API automatically searches for `config.yaml` in multiple locations:

1. **Docker Container**: `/usr/local/lib/python3.12/config.yaml` (for containerized deployments)
2. **API Project Root**: `projects/api/config.yaml` (for local development)
3. **Current Working Directory**: `./config.yaml` (fallback location)
4. **Environment Variable**: Path specified by `CONFIG_PATH` environment variable

### Custom Configuration Path

You can override the default configuration file search by setting the `CONFIG_PATH` environment variable:

```bash
export CONFIG_PATH=/path/to/your/config.yaml
```

This is particularly useful for:
- Docker deployments with mounted configuration files
- Custom deployment scenarios
- Testing with different configuration files

## Environment Variables

### File Upload Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE_MB` | `50` | Maximum CSV file size in megabytes |
| `VALIDATION_TIMEOUT_SECONDS` | `300` | Maximum time allowed for validation processing |
| `SCHEMA_DIRECTORY` | `data/schemas` | Directory containing validation schema files |

### AWS S3 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RESULTS_S3_BUCKET` | `metadata-validation-results` | S3 bucket for storing validation results |
| `SCHEMAS_S3_BUCKET` | `metadata-schemas` | S3 bucket for storing validation schemas |

### DynamoDB Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `METADATA_SCHEMAS_TABLE_NAME` | `METADATA_SCHEMAS_TABLE` | DynamoDB table name for metadata schemas |
| `METADATA_UPLOAD_JOB_TABLE_NAME` | `METADATA_UPLOAD_JOB` | DynamoDB table name for metadata upload jobs |

### AWS General Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region where services are deployed |
| `AWS_PROFILE` | `None` | AWS credential profile to use for authentication |
| `CONFIG_PATH` | `None` | Custom path to configuration file (overrides automatic search) |

### Processing Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENCY` | `10` | Maximum number of concurrent processing tasks |
| `API_ENABLE_AUTH` | `False` | Enable or disable API authentication |

### Retry Configuration

The API includes built-in retry logic with the following default settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_MAX_RETRIES` | `3` | Maximum number of retry attempts for failed operations |
| `DEFAULT_MAX_RETRY_TIMEOUT` | `300.0` | Maximum timeout in seconds for retry cycles |
| `DEFAULT_BASE_DELAY` | `2.0` | Base delay in seconds for exponential backoff |
| `DEFAULT_MAX_DELAY` | `60.0` | Maximum delay in seconds between retry attempts |

**Note**: These retry settings are hardcoded constants in the API utilities and apply to database operations, external service calls, and processor interactions. They are not configurable via environment variables.

## ProcessorManager Configuration

The API uses a `ProcessorManager` to integrate with the metadata-harmonization-processor package. Configuration is managed through `config.yaml` with environment-specific overrides.

### Environment Variables for ProcessorManager

| Variable | Default | Description |
|----------|---------|-------------|
| `PROCESSOR_ENVIRONMENT` | `local` | Environment mode: `local` or `cloud` (controls automatic configuration selection) |
| `PROCESSOR_JOB_STATUS_SAVER_TYPE` | `local` | Job status storage: `local` or `dynamodb` |
| `PROCESSOR_JOB_STATUS_TABLE_NAME` | `metadata-upload-jobs` | DynamoDB table for job status (cloud mode) |
| `PROCESSOR_RESULT_SAVER_TYPE` | `local` | Result storage: `local` or `s3` |
| `PROCESSOR_RESULTS_S3_BUCKET` | `metadata-validation-results` | S3 bucket for results (cloud mode) |
| `PROCESSOR_RESULTS_S3_PREFIX` | `results/` | S3 prefix for results (cloud mode) |
| `PROCESSOR_SESSION_TYPE` | `file` | Session storage: `file` or `s3` |
| `PROCESSOR_S3_BUCKET` | `metadata-processor-sessions` | S3 bucket for sessions (cloud mode) |
| `PROCESSOR_S3_PREFIX` | `sessions/` | S3 prefix for sessions (cloud mode) |
| `PROCESSOR_ENABLE_REDIS_CACHE` | `false` | Enable Redis caching (cloud mode) |
| `PROCESSOR_REDIS_ENDPOINT` | `null` | Redis endpoint URL (cloud mode) |
| `PROCESSOR_REDIS_PORT` | `6379` | Redis port (cloud mode) |
| `PROCESSOR_LOCAL_DEVELOPMENT_MODE` | `true` | Enable local development features |

### Configuration Loading

The ProcessorManager loads configuration using:

```python
from metadata_harmonization_api.services.processor_manager import (
    create_processor_manager_from_config,
    detect_environment_overrides
)

# Automatic environment detection and configuration
overrides = detect_environment_overrides()
processor_manager = create_processor_manager_from_config(
    config_path=Path("config.yaml"),
    environment_overrides=overrides
)
```

## Configuration Validation

The API includes configuration validation to ensure all required settings are present and valid. You can check configuration status through the configuration service:

```python
from metadata_harmonization_api.services.config_service import metadata_config_service

# Get configuration summary
config_summary = metadata_config_service.get_configuration_summary()

# Validate configuration
validation_results = metadata_config_service.validate_configuration()
```

## Example .env File

```bash
# File Upload Settings
MAX_FILE_SIZE_MB=100
VALIDATION_TIMEOUT_SECONDS=600

# AWS Configuration
AWS_REGION=us-west-2
RESULTS_S3_BUCKET=my-metadata-results
SCHEMAS_S3_BUCKET=my-metadata-schemas

# DynamoDB Tables
METADATA_SCHEMAS_TABLE_NAME=MetadataSchemas
METADATA_UPLOAD_JOB_TABLE_NAME=MetadataUploadJobs

# Processing
MAX_CONCURRENCY=20
API_ENABLE_AUTH=true

# Note: Retry configuration is now handled by built-in constants:
# - DEFAULT_MAX_RETRIES=3
# - DEFAULT_MAX_RETRY_TIMEOUT=300.0
# - DEFAULT_BASE_DELAY=2.0
# - DEFAULT_MAX_DELAY=60.0

# ProcessorManager Configuration
# Environment detection (controls automatic backend selection)
PROCESSOR_ENVIRONMENT=cloud
PROCESSOR_JOB_STATUS_SAVER_TYPE=dynamodb
PROCESSOR_JOB_STATUS_TABLE_NAME=metadata-upload-jobs
PROCESSOR_RESULT_SAVER_TYPE=s3
PROCESSOR_RESULTS_S3_BUCKET=metadata-validation-results
PROCESSOR_RESULTS_S3_PREFIX=results/
PROCESSOR_SESSION_SAVER_TYPE=s3
PROCESSOR_SESSION_S3_BUCKET=metadata-processor-sessions
PROCESSOR_SESSION_S3_PREFIX=sessions/
PROCESSOR_ENABLE_REDIS_CACHE=true
PROCESSOR_REDIS_ENDPOINT=redis.example.com
PROCESSOR_LOCAL_DEVELOPMENT_MODE=false
```

## Schema Directory Structure

The schema directory should contain JSON schema files organized as follows:

```
data/schemas/
├── core/
│   ├── v1.0/
│   │   └── schema.json
│   └── v2.0/
│       └── schema.json
└── programs/
    ├── cancer/
    │   └── v1.0/
    │       └── schema.json
    └── birth_defects/
        └── v1.0/
            └── schema.json
```

## DynamoDB Table Schemas

### METADATA_SCHEMAS_TABLE

- **Partition Key**: `core_schema_id` (String)
- **Attributes**:
  - `name` (String)
  - `core_schema_path` (String)
  - `core_schema_s3_bucket` (String)
  - `program_schemas` (List)

**Note**: This table uses the `MetadataSchema` model imported from the `metadata_harmonization_processor` package for consistent schema storage across the platform.

### METADATA_UPLOAD_JOB

- **Partition Key**: `job_id` (String)
- **Global Secondary Index**: `user-id-index`
  - **Partition Key**: `user_id` (String)
  - **Sort Key**: `created_at` (String)
- **Attributes**:
  - `user_id` (String)
  - `core_schema_id` (String)
  - `program_schema_id` (String)
  - `status` (String)
  - `created_at` (String)
  - `completed_at` (String, nullable)
  - `current_version` (Number)
  - `results` (Map)

**Note**: This table uses the shared `MetadataUploadJob` model from the `metadata_harmonization_processor` package for consistency across the platform.

## S3 Bucket Permissions

Ensure the API has the following permissions on the configured S3 buckets:

### Results Bucket
- `s3:PutObject`
- `s3:GetObject`
- `s3:DeleteObject`

### Schemas Bucket
- `s3:GetObject`
- `s3:ListBucket`

## Security Considerations

1. **File Upload Security**: Files are validated for type and size before processing
2. **Temporary Storage**: Uploaded files are stored in temporary directories and cleaned up after processing
3. **Authentication**: OIDC authentication can be enabled/disabled via `API_ENABLE_AUTH`
4. **AWS Permissions**: Follow principle of least privilege for AWS resource access

## Integration Testing

The API package includes comprehensive integration tests that validate the complete workflow:

### Running API Integration Tests

```bash
# Run background task integration tests
pytest projects/api/tests/integration/test_background_tasks_integration.py -v

# Run worker service tests
pytest projects/api/tests/unit/workers/test_worker_service.py -v

# Run complete workflow tests
pytest projects/api/tests/integration/ -v
```

### Integration Test Coverage

**Background Task Processing:**
- Complete workflow from API endpoint to result storage
- Concurrent task processing and resource management
- Error handling and recovery mechanisms
- Job status tracking throughout processing lifecycle

**Worker Service Integration:**
- MetadataWorker and WorkerService coordination
- Result storage backend integration (S3 and local)
- Job resubmission and version management
- Performance testing with large datasets

**Storage Backend Testing:**
- S3ResultSaver integration with multipart uploads
- LocalResultSaver for development environments
- DataSaver coordination between job status and results
- Error recovery and graceful degradation

The integration tests ensure that the API works correctly with the metadata-harmonization-processor package and validates end-to-end functionality including result storage, job tracking, and error handling.
