# Metadata Harmonization API

CSV metadata validation API with schema alignment, background processing, and MCP server integration.

## Base URL

- Local: `http://localhost:8080`
- Production: `https://your-domain.com`

## Authentication

Optional OIDC Bearer token authentication. When enabled (`API_ENABLE_AUTH=true`):

```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### Health Check

**GET** `/api/health` or `/api/v1/health`

Basic health status check.

**Response:**
```json
{"status": "OK"}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | API is healthy |

**Example:**
```bash
curl -X GET "http://localhost:8080/api/v1/health"
```

### Create Validation Job

**POST** `/api/v1/metadata/validate`

Upload CSV file and create validation job.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | CSV file (max 50MB) |
| core_schema_id | String | Yes | Core schema identifier |
| program_schema_id | String | Yes | Program schema identifier |

**Response:**
```json
{"jobId": "550e8400-e29b-41d4-a716-446655440000"}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 201 | Job created successfully |
| 400 | Invalid file format or schema IDs |
| 413 | File exceeds size limit |
| 500 | Server error |

**Example:**
```bash
curl -X POST "http://localhost:8080/api/v1/metadata/validate" \
  -H "Authorization: Bearer <token>" \
  -F "file=@metadata.csv" \
  -F "core_schema_id=cyclospora_core_v1" \
  -F "program_schema_id=cyclospora_program_v1"
```

### Update Validation Job

**POST** `/api/v1/metadata/validate/{metadata_id}`

Update existing job with new CSV file. Preserves schema IDs and increments version.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| metadata_id | UUID | Yes | Job ID from original validation |

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | Updated CSV file (max 50MB) |

**Response:**
```json
{"jobId": "550e8400-e29b-41d4-a716-446655440000"}
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Job updated successfully |
| 400 | Invalid file format |
| 404 | Job not found |
| 413 | File exceeds size limit |
| 500 | Server error |

**Example:**
```bash
curl -X POST "http://localhost:8080/api/v1/metadata/validate/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>" \
  -F "file=@updated_metadata.csv"
```

### Get Validation Status

**GET** `/api/v1/metadata/validate/{metadata_id}`

Retrieve validation job status and results. Poll this endpoint to track progress.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| metadata_id | UUID | Yes | Job ID to retrieve |

**Response:**
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "user123",
  "coreSchemaId": "cyclospora_core_v1",
  "programSchemaId": "cyclospora_program_v1",
  "status": "completed",
  "createdAt": "2024-01-15T10:30:00Z",
  "completedAt": "2024-01-15T10:35:00Z",
  "currentVersion": 1,
  "latestResults": {
    "validationResults": {
      "summary": {"totalRows": 100, "totalErrors": 5},
      "errors": [{"row": 5, "column": "sample_id", "errorType": "REQUIRED_VALUE"}]
    },
    "schemaAlignmentResults": {
      "originalDataCsv": "id,name\n1,John",
      "alignedDataCsv": "sample_id,participant_name\n1,John",
      "columnMappings": {"id": "sample_id"}
    }
  }
}
```

**Job Status Values:**

| Status | Description |
|--------|-------------|
| pending | Job created, waiting to start |
| processing | Job is currently being processed |
| completed | Job completed successfully, no errors |
| completed_with_errors | Job completed, validation errors found |
| failed | Job failed due to system error |

**Polling Recommendations:**

| Parameter | Value |
|-----------|-------|
| Poll Interval | 2 seconds |
| Maximum Duration | 5 minutes |
| Terminal States | completed, completed_with_errors, failed |

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Status retrieved successfully |
| 404 | Job not found |
| 500 | Server error |

**Example:**
```bash
curl -X GET "http://localhost:8080/api/v1/metadata/validate/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <token>"
```

### List Available Schemas

**GET** `/api/v1/metadata/schema`

Retrieve all available validation schemas.

**Response:**
```json
[
  {
    "coreSchemaId": "cyclospora_core_v1",
    "name": "Cyclospora Core Schema v1.0",
    "programSchemas": [
      {
        "programName": "Cyclospora Program v1.0",
        "programSchemaId": "cyclospora_program_v1"
      }
    ]
  }
]
```

**Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Schemas retrieved successfully |
| 500 | Server error |

**Example:**
```bash
curl -X GET "http://localhost:8080/api/v1/metadata/schema" \
  -H "Authorization: Bearer <token>"
```

## MCP Server Integration

Model Context Protocol server for AI agent integration. Enabled by default at `/mcp`.

**Configuration:**

| Variable | Default | Description |
|----------|---------|-------------|
| MCP_ENABLED | true | Enable/disable MCP server |
| MCP_MOUNT_PATH | /mcp | MCP server mount path |

**Available Tools:**

| Tool | Parameters | Returns |
|------|------------|---------|
| submit_metadata_validation | csv_data, core_schema_id, program_schema_id | Validation results with errors and recommendations |
| list_schemas | None | Array of available schemas |
| get_schema_details | schema_id | Detailed schema information and validation rules |

**MCP Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | /mcp | Main MCP protocol endpoint |
| GET | /mcp/health | MCP server health check |
| GET | /mcp/tools | List available tools (debug) |

## Data Models

### ValidationStatusResponse

| Property | Type | Description |
|----------|------|-------------|
| jobId | string | Job identifier (UUID) |
| userId | string | User identifier |
| coreSchemaId | string | Core schema identifier |
| programSchemaId | string | Program schema identifier |
| status | string | Job status (pending, processing, completed, completed_with_errors, failed) |
| createdAt | string | ISO 8601 timestamp |
| completedAt | string \| null | ISO 8601 timestamp or null |
| currentVersion | number | Job version number |
| latestResults | object \| null | Combined validation and alignment results |

### ValidationResults

**Summary:**

| Property | Type | Description |
|----------|------|-------------|
| totalRows | number | Total rows in CSV |
| totalErrors | number | Total validation errors |
| errorsByType | object | Error counts by type |

**Error Object:**

| Property | Type | Description |
|----------|------|-------------|
| row | number | Row number (1-based indexing) |
| column | string | Column name |
| errorType | string | Error type (REQUIRED_VALUE, INVALID_OPTION, INVALID_PATTERN) |
| currentValue | any | Current invalid value |
| validOptions | array \| null | Valid options for enum fields |
| recommendedValue | any \| null | AI-recommended correction |
| confidenceScore | number | Confidence score (0.0-1.0) |
| confidenceLevel | string | Confidence level (High, Medium, Low) |
| errorMessage | string \| null | Custom error message from schema |
| schemaFieldName | string \| null | Schema field name |

**Confidence Levels:**

| Level | Score Range | Description |
|-------|-------------|-------------|
| High | >= 0.8 | Highly reliable recommendation |
| Medium | 0.5 - 0.79 | Moderately reliable recommendation |
| Low | < 0.5 | Low reliability, manual review recommended |

### SchemaAlignmentResults

| Property | Type | Description |
|----------|------|-------------|
| originalDataCsv | string | Original uploaded CSV data |
| alignedDataCsv | string | Schema-aligned CSV data |
| columnMappings | object | Original to aligned column name mappings |
| transformationSummary | object | Detailed transformation statistics |

**Transformation Summary:**

| Property | Type | Description |
|----------|------|-------------|
| columns_renamed | number | Columns renamed during alignment |
| columns_added | number | Columns added to match schema |
| columns_removed | number | Extra columns removed |
| rows_original | number | Original row count |
| rows_aligned | number | Aligned row count |
| column_mappings | object | Column name mapping dictionary |
| added_columns | array | List of added column names |
| removed_columns | array | List of removed column names |
| original_column_count | number | Original column count |
| aligned_column_count | number | Final column count |
| data_shape_changed | boolean | Whether DataFrame shape changed |
| transformation_timestamp | string | ISO 8601 timestamp |

### SchemaInfo

| Property | Type | Description |
|----------|------|-------------|
| coreSchemaId | string | Core schema identifier |
| name | string | Schema display name |
| coreSchemaPath | string | Path to core schema JSON |
| coreSchemaS3Bucket | string | S3 bucket name |
| programSchemas | array | Array of program schema objects |

**Program Schema Object:**

| Property | Type | Description |
|----------|------|-------------|
| programName | string | Program schema display name |
| s3Location | string | S3 path to schema JSON |
| s3Bucket | string | S3 bucket name |
| programSchemaId | string | Program schema identifier |

## Error Handling

**Error Response Format:**
```json
{
  "detail": "Human-readable error message",
  "errorCode": "VALIDATION_ERROR",
  "requestId": "req-550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Codes:**

| Code | Description |
|------|-------------|
| INVALID_FILE_FORMAT | File is not a valid CSV |
| FILE_TOO_LARGE | File exceeds 50MB limit |
| INVALID_SCHEMA_COMBINATION | Invalid schema IDs provided |
| JOB_NOT_FOUND | Validation job does not exist |
| PROCESSING_ERROR | Error during background processing |
| GRAPH_EXECUTION_FAILED | Processing graph execution failed |
| VALIDATION_RESULTS_MISSING | Processing completed but no results generated |

## File Upload Constraints

| Constraint | Value |
|------------|-------|
| Maximum File Size | 50MB |
| Allowed MIME Types | text/csv, application/csv |
| Required Extension | .csv |
| Recommended Encoding | UTF-8 |

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| File Uploads | 10 requests/minute/user |
| Status Queries | 100 requests/minute/user |
| Schema Queries | 50 requests/minute/user |

## OpenAPI Documentation

| Format | Path |
|--------|------|
| Swagger UI | /api/docs |
| ReDoc | /api/redoc |
| OpenAPI JSON | /api/openapi.json |
