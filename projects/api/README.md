# API - Metadata Validation Backend

FastAPI backend service providing HTTP and MCP interfaces for metadata validation, schema management, and job tracking across data systems.

## Quick Start

Prerequisites: Python 3.12+, AWS CLI configured

```bash
# Install and run locally
cd projects/api
make install
make run-local
```

**Local Development**: http://localhost:8080
**API Documentation**: http://localhost:8080/docs

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_REGION` | Cloud only | AWS region for DynamoDB and S3 (default: us-east-1) |
| `METADATA_SCHEMAS_TABLE` | Cloud only | DynamoDB table for schema metadata |
| `METADATA_UPLOAD_JOB_TABLE` | Cloud only | DynamoDB table for job tracking |
| `VALIDATION_RESULTS_BUCKET` | Cloud only | S3 bucket for validation results |
| `SCHEMA_STORAGE_BUCKET` | Cloud only | S3 bucket for schema files |
| `AUTHORITY` | Cloud only | Cognito authority URL for authentication |
| `CLIENT_ID` | Cloud only | Cognito client ID |
| `API_ENABLE_AUTH` | Cloud only | Enable authentication (true/false) |
| `PROCESSOR_ENVIRONMENT` | Optional | Environment mode: local/cloud (default: local) |
| `PROCESSOR_ENABLE_REDIS_CACHE` | Optional | Enable Redis caching (default: false) |
| `PROCESSOR_REDIS_ENDPOINT` | Optional | Redis server hostname (default: localhost) |
| `PROCESSOR_REDIS_PORT` | Optional | Redis server port (default: 6379) |
| `LOG_LEVEL` | Optional | Logging level (default: INFO) |
| `MCP_ENABLED` | Optional | Enable MCP server (default: true) |
| `MCP_MOUNT_PATH` | Optional | MCP server mount path (default: /agent) |
| `CONFIG_PATH` | Optional | Custom path to config.yaml file |

### Configuration File

The API uses `config.yaml` for detailed configuration. The file is searched in these locations:

1. `/usr/local/lib/python3.12/config.yaml` (Docker container)
2. `projects/api/config.yaml` (local development)
3. `./config.yaml` (current directory)
4. Path specified by `CONFIG_PATH` environment variable

Minimal local development configuration:
```yaml
api:
  max_file_size_mb: 50
  allowed_file_types: ["text/csv", "application/csv"]
  validation_timeout_seconds: 300
  enable_auth: false
  mcp_enabled: true
  mcp_mount_path: "/agent"

processor:
  # Local storage paths
  job_status_saver_type: "local"
  job_status_storage_dir: "./datastore/job_status"
  result_saver_type: "local"
  results_local_dir: "./datastore/validation-results"
  session_saver_type: "file"
  file_session_directory: "./datastore/sessions"
  schema_directory: "./data/schema"

  # AI features (in-memory cache for local)
  enable_redis_cache: false
  enable_memory_cache: true
  embedding_provider: "bedrock"
  bedrock_model_id: "amazon.titan-embed-text-v2:0"
  cosine_similarity_threshold: 0.5
```

See `config.yaml` in the project root for full configuration options.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Basic API health check |
| GET | `/api/v1/health` | Versioned health check (ALB health probe) |
| POST | `/api/v1/metadata/validate` | Create new validation job with CSV upload |
| POST | `/api/v1/metadata/validate/{metadata_id}` | Update existing job with new CSV file |
| GET | `/api/v1/metadata/validate/{metadata_id}` | Get validation job status and results |
| GET | `/api/v1/metadata/schema` | List all available schemas |

### Request/Response Models

- **ValidationCreateRequest**: Core and program schema IDs for job creation
- **ValidationJobResponse**: Returns `jobId` for tracking
- **ValidationStatusResponse**: Complete job status including validation results and post-schema alignment data
- **SchemaInfo**: Available schemas with core and program schema information
- **ErrorResponse**: Standardized error responses with detail messages

See `/api/docs` for complete API documentation and interactive examples.

## MCP Server

The API includes a Model Context Protocol (MCP) server for AI agent integration. When enabled (default), the server exposes metadata validation and schema management tools at the `/agent` endpoint. The MCP server shares the same service instances as the REST API, ensuring consistency and resource efficiency. Tools include: `submit_metadata_validation`, `get_validation_status`, `list_available_schemas`, and `get_schema_details`. Configure via `MCP_ENABLED` environment variable or `api.mcp_enabled` in config.yaml.

## Architecture

The API uses a dual interface architecture: HTTP REST endpoints for web applications and MCP server for AI agent integration. Both interfaces share identical service instances through a centralized dependency injection system, ensuring resource efficiency and consistency. Core components include MetadataValidationHandler (validation workflows), SchemaHandler (schema management), ProcessorManager (processor lifecycle and session management), ChangeDetectionService (automatic change tracking), and SchemaCollector (schema loading). The system integrates with the metadata-harmonization-processor package for validation logic and supports both local file storage (development) and AWS services (production: DynamoDB, S3, ECS Fargate).

## Development

### Installation

```bash
cd projects/api
make install
```

### Running the API

```bash
# Local development mode (file storage, no auth, in-memory cache)
make run-local

# Cloud mode (DynamoDB, S3, authentication)
make run-cloud

# Production mode (multiple workers, optimized)
make run-prod
```

### Environment Modes

- **Local Mode** (`make run-local`): Uses local file storage, no authentication, in-memory caching. Best for development.
- **Cloud Mode** (`make run-cloud`): Uses AWS services (DynamoDB, S3), authentication enabled, Redis optional.
- **Production Mode** (`make run-prod`): Production configuration with multiple workers, Redis recommended.

Set `PROCESSOR_ENVIRONMENT=local` or `cloud` to override mode detection.

### Testing

```bash
# Run all tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Tests with coverage
make test-cov
```

### Development Setup

```bash
# Initialize development environment
make dev-setup

# Optional: Enable Redis for production-like caching
docker run -d -p 6379:6379 redis:latest

# Update config.yaml
processor:
  enable_redis_cache: true
  redis_endpoint: "localhost"
  redis_port: 6379
```

## Troubleshooting

### Configuration File Not Found
**Symptoms**: "Configuration file not found" warnings, API using defaults.
**Solution**: Ensure `config.yaml` exists in one of the expected locations (see Configuration section). Use `CONFIG_PATH` environment variable to specify custom location.

### AWS Credentials or Permissions Issues
**Symptoms**: 403 Forbidden errors, "Unable to locate credentials" errors.
**Solution**: Configure AWS CLI (`aws configure`) or set environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`). Verify IAM permissions for DynamoDB tables and S3 buckets.

### ProcessorManager Initialization Fails
**Symptoms**: API fails to start, "ProcessorManager initialization failed" errors.
**Solution**: Check `PROCESSOR_ENVIRONMENT` variable is set correctly (local/cloud). Verify processor configuration in config.yaml. For local mode, ensure storage directories exist. For cloud mode, verify AWS service access.

### MCP Server Connection Issues
**Symptoms**: Agent cannot connect to MCP server, 404 errors on `/agent` endpoint.
**Solution**: Verify `MCP_ENABLED=true` in environment or config.yaml. Check API is running and accessible at specified port. Ensure MCP mount path matches agent configuration (default: `/agent`).

### Validation Job Stuck in "Processing" Status
**Symptoms**: Jobs never complete, no results returned.
**Solution**: Check application logs for processor errors. Verify schema files exist in configured `schema_directory`. For cloud mode, check S3 bucket access. Ensure validation timeout is sufficient (`validation_timeout_seconds` in config.yaml).

### Redis Connection Failed (Optional Feature)
**Symptoms**: Redis connection errors, cache not working.
**Solution**: Redis is optional - the API uses in-memory caching by default. If Redis is desired, verify server is running (`redis-cli ping`), check `PROCESSOR_REDIS_ENDPOINT` and `PROCESSOR_REDIS_PORT` settings, and ensure `PROCESSOR_ENABLE_REDIS_CACHE=true`.

## Additional Resources

- **[Complete API Documentation](docs/API.md)** - Detailed endpoint documentation with examples
- **Interactive Documentation** - Available at `/api/docs` when running
- **OpenAPI Specification** - Available at `/api/openapi.json`
- **Processor Package** - See `projects/processor/README.md` for processor details
