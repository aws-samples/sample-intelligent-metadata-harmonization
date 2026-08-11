# API Documentation

This document provides comprehensive documentation for all public APIs and interfaces in the MetadataHarmonizationProcessor package.

## Package Integration

The MetadataHarmonizationProcessor package provides shared data models and interfaces that are used across the platform:

- **API Integration**: The FastAPI-based metadata validation service imports all job models (`MetadataUploadJob`, `ProgramSchema`, `JobResults`) and validation models (`ValidationResults`, `ValidationErrorDetail`, etc.) directly from this package to ensure consistency in data structures across the platform.
- **Interface Integration**: The API uses processor package interfaces directly (`JobStatusSaver`, `SchemaCollector`) instead of custom API interfaces, ensuring consistent data access patterns across different deployment scenarios.
- **ProcessorManager Integration**: The API uses a `ProcessorManager` class to manage processor instances with lifecycle management, session handling, and dynamic configuration for local vs cloud environments.
- **Complete Integration**: All tests have been updated to use processor package interfaces, eliminating code duplication and maintaining architectural coherence between the API and processor components.

## Table of Contents

- [Core Classes](#core-classes)
- [Interfaces](#interfaces)
- [Models](#models)
- [Processing Nodes](#processing-nodes)
- [Implementations](#implementations)
- [Logging Components](#logging-components)
- [Configuration](#configuration)
- [Exceptions](#exceptions)

## Core Classes

### MetadataHarmonizationProcessor

The main orchestration class that coordinates the complete metadata processing pipeline.

```python
from metadata_harmonization_processor import MetadataHarmonizationProcessor
```

#### Constructor

```python
def __init__(
    self,
    config: ProcessorConfig,
    job_status_saver: JobStatusSaver,
    schema_collector: SchemaCollector,
    session_id: str,
    session_config: Optional[Dict[str, Any]] = None
) -> None
```

**Parameters:**
- `config`: Validated ProcessorConfig instance (loaded via load_processor_settings)
- `job_status_saver`: Implementation of JobStatusSaver interface for persisting job status
- `schema_collector`: Implementation of SchemaCollector interface for retrieving schemas
- `session_id`: Unique session identifier for AWS Strands session management
- `session_config`: Optional configuration for session manager (bucket, storage_dir, etc.)

**Raises:**
- `ConfigurationError`: If configuration loading or validation fails
- `ValueError`: If required components are not provided

#### Methods

##### process

```python
async def process(self, metadata_df: pd.DataFrame) -> ValidationResults
```

Process metadata through the complete pipeline (schema alignment, validation, and predictions).

**Parameters:**
- `metadata_df`: Input metadata DataFrame to process

**Returns:**
- `ValidationResults`: Validation results with error details and AI-powered recommendations

**Raises:**
- `ProcessingError`: If processing fails at any stage
- `SchemaError`: If schema retrieval or validation fails
- `ExternalServiceError`: If AWS services are unavailable

##### process

```python
async def process(self, metadata_df: pd.DataFrame, program_id: str, core_id: str, job_id: Optional[str] = None) -> ValidationResults
```

Process metadata through the complete pipeline with schema alignment, validation, and AI-powered predictions.

**Parameters:**
- `metadata_df`: Input metadata DataFrame to process
- `program_id`: Schema program identifier
- `core_id`: Schema core identifier
- `job_id`: Optional job identifier. If not provided, session_id will be used for consistency

**Returns:**
- `ValidationResults`: Validation results with error details and recommendations

**Raises:**
- `ProcessingError`: If processing fails at any stage
- `ValueError`: If input data is invalid

##### set_schema_ids

```python
def set_schema_ids(self, program_id: str, core_id: str) -> None
```

Set schema IDs in processor state for current processing session.

**Note:** This method is optional when using the `process()` method, as schema IDs can be passed directly to `process()`.

**Parameters:**
- `program_id`: Schema program identifier
- `core_id`: Schema core identifier

##### get_current_state

```python
def get_current_state(self) -> Optional[ProcessorState]
```

Get the current processor state with processing metadata.

**Returns:**
- `ProcessorState`: Current state or None if not initialized

##### reset_state

```python
def reset_state(self) -> None
```

Reset the processor state for a new processing session.

##### cleanup

```python
async def cleanup(self) -> None
```

Clean up processor resources (Redis connections, AWS clients, etc.).

## Interfaces

### JobStatusSaver

Abstract interface for persisting job status and progress tracking.

```python
from metadata_harmonization_processor.interfaces import JobStatusSaver
```

#### Methods

##### save_status

```python
async def save_status(self, job_id: str, status: str, metadata: Dict[str, Any]) -> None
```

Save job status with metadata.

**Parameters:**
- `job_id`: Unique job identifier
- `status`: Current job status (e.g., "processing", "completed", "completed_with_errors", "failed")
- `metadata`: Additional metadata dictionary

##### get_status

```python
async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]
```

Retrieve job status and metadata.

**Parameters:**
- `job_id`: Unique job identifier

**Returns:**
- `Dict[str, Any]`: Job status data or None if not found

##### update_progress

```python
async def update_progress(self, job_id: str, stage: str, progress: float) -> None
```

Update job progress for a specific stage.

**Parameters:**
- `job_id`: Unique job identifier
- `stage`: Processing stage name
- `progress`: Progress value between 0.0 and 1.0

### ResultSaver

Abstract interface for storing combined ValidationResults and SchemaAlignmentResults to different storage backends.

```python
from metadata_harmonization_processor.interfaces import ResultSaver
```

#### Methods

##### save_results

```python
async def save_results(
    self,
    job_id: str,
    version: int,
    validation_results: ValidationResults,
    schema_alignment_results: Optional[SchemaAlignmentResults] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> JobResults
```

Save combined ValidationResults and optional SchemaAlignmentResults.

**Parameters:**
- `job_id`: Unique identifier for the processing job
- `version`: Version number for this result set
- `validation_results`: ValidationResults to save
- `schema_alignment_results`: Optional SchemaAlignmentResults to save
- `metadata`: Optional metadata about the processing

**Returns:**
- `JobResults`: Storage location information for retrieval

**Raises:**
- `Exception`: If results cannot be saved

##### get_results

```python
async def get_results(self, job_results: JobResults) -> Tuple[Optional[ValidationResults], Optional[SchemaAlignmentResults]]
```

Retrieve combined ValidationResults and SchemaAlignmentResults from storage.

**Parameters:**
- `job_results`: JobResults with storage location information

**Returns:**
- `Tuple[Optional[ValidationResults], Optional[SchemaAlignmentResults]]`: Tuple of results where either can be None if not found

**Raises:**
- `Exception`: If results cannot be retrieved

##### list_results

```python
async def list_results(self, job_id: str) -> List[JobResults]
```

List all available result versions for a job.

**Parameters:**
- `job_id`: Job identifier to list results for

**Returns:**
- `List[JobResults]`: List of available result versions

### SchemaCollector

Abstract interface for collecting schema information from various sources.

```python
from metadata_harmonization_processor.interfaces import SchemaCollector, SchemaInfo
```

#### Methods

##### get_available_schemas

```python
async def get_available_schemas(self) -> List[SchemaInfo]
```

Get list of available schemas for API responses.

**Returns:**
- `List[SchemaInfo]`: List of available schema combinations

##### get_schema

```python
async def get_schema(self, program_id: str, core_id: str) -> Dict[str, Any]
```

Retrieve combined schema definition by program and core IDs.

**Parameters:**
- `program_id`: Schema program identifier
- `core_id`: Schema core identifier

**Returns:**
- `Dict[str, Any]`: Combined schema definition (JSON Schema format)

**Raises:**
- `SchemaError`: If schema not found or invalid

##### get_schema_columns

```python
async def get_schema_columns(self, program_id: str, core_id: str) -> List[str]
```

Get list of expected columns for schema.

**Parameters:**
- `program_id`: Schema program identifier
- `core_id`: Schema core identifier

**Returns:**
- `List[str]`: List of expected column names

##### get_validation_rules

```python
async def get_validation_rules(self, program_id: str, core_id: str) -> Dict[str, Any]
```

Get validation rules for schema fields.

**Parameters:**
- `program_id`: Schema program identifier
- `core_id`: Schema core identifier

**Returns:**
- `Dict[str, Any]`: Validation rules by field name

## Models

### ValidationErrorType

Enumeration of validation error types.

```python
from metadata_harmonization_processor.models.validation import ValidationErrorType

class ValidationErrorType(str, Enum):
    REQUIRED_VALUE = "REQUIRED_VALUE"
    INVALID_OPTION = "INVALID_OPTION"
    INVALID_PATTERN = "INVALID_PATTERN"
```

### ValidationErrorDetail

Detailed information about a single validation error.

```python
from metadata_harmonization_processor.models.validation import ValidationErrorDetail

class ValidationErrorDetail(BaseModel):
    row: int
    column: str
    current_value: str
    valid_options: Optional[List[str]]
    recommended_value: Optional[str]
    error_type: ValidationErrorType
```

**Fields:**
- `row`: Row number where the error occurred (0-based)
- `column`: Column name where the error occurred
- `current_value`: The current value that caused the error
- `valid_options`: List of valid options for this field (None for free-form fields)
- `recommended_value`: AI-powered recommended replacement value (None when unavailable)
- `error_type`: Type of validation error

### ValidationResultsSummary

Summary statistics for validation results.

```python
from metadata_harmonization_processor.models.validation import ValidationResultsSummary

class ValidationResultsSummary(BaseModel):
    total_rows: int
    total_errors: int
    error_types: Dict[ValidationErrorType, int]
```

**Fields:**
- `total_rows`: Total number of rows processed
- `total_errors`: Total number of validation errors found
- `error_types`: Count of errors by type

### ValidationResults

Complete validation results structure.

```python
from metadata_harmonization_processor.models.validation import ValidationResults

class ValidationResults(BaseModel):
    validation_results: List[ValidationErrorDetail]
    summary: ValidationResultsSummary
```

**Fields:**
- `validation_results`: List of all validation errors found
- `summary`: Summary statistics for the validation

### ProcessorState

State object that tracks processing progress and intermediate results. Supports dual result instances for unified storage approach with both validation and schema alignment results.

```python
from metadata_harmonization_processor.models.state import ProcessorState

class ProcessorState(BaseModel):
    # Input data
    metadata_df: Optional[pd.DataFrame]
    program_id: Optional[str]
    core_id: Optional[str]

    # Intermediate results
    aligned_df: Optional[pd.DataFrame]
    schema_definition: Optional[Dict[str, Any]]

    # Final results (dual result instances)
    validation_results: Optional[ValidationResults]
    schema_alignment_results: Optional[SchemaAlignmentResults]

    # Processing metadata
    job_id: str
    current_stage: str
    processing_start_time: Optional[datetime]

    # Processing metadata for schema alignment (temporary for processing)
    column_mappings: Optional[Dict[str, str]]
    transformation_summary: Optional[Dict[str, Any]]
```

#### Methods

##### set_current_stage

```python
def set_current_stage(self, stage: str) -> None
```

Update the current processing stage.

**Parameters:**
- `stage`: Name of the current processing stage

##### has_metadata

```python
def has_metadata(self) -> bool
```

Check if the state contains input metadata.

**Returns:**
- `bool`: True if metadata_df is not None and not empty

##### has_schema_ids

```python
def has_schema_ids(self) -> bool
```

Check if the state contains both required schema identifiers.

**Returns:**
- `bool`: True if both program_id and core_id are set

##### has_aligned_data

```python
def has_aligned_data(self) -> bool
```

Check if the state contains aligned DataFrame.

**Returns:**
- `bool`: True if aligned_df is not None and not empty

##### has_validation_results

```python
def has_validation_results(self) -> bool
```

Check if the state contains validation results.

**Returns:**
- `bool`: True if validation_results is not None

##### has_schema_alignment_results

```python
def has_schema_alignment_results(self) -> bool
```

Check if the state contains schema alignment results.

**Returns:**
- `bool`: True if schema_alignment_results is not None

##### get_combined_results

```python
def get_combined_results(self) -> tuple[Optional[ValidationResults], Optional[SchemaAlignmentResults]]
```

Get both result instances for unified storage.

**Returns:**
- `tuple`: Tuple of (ValidationResults, SchemaAlignmentResults) instances

##### get_processing_duration

```python
def get_processing_duration(self) -> Optional[float]
```

Calculate processing duration in seconds.

**Returns:**
- `Optional[float]`: Duration in seconds if processing_start_time is set, None otherwise

### SchemaAlignmentResults

Model for schema alignment results data that contains the results of schema alignment processing.

```python
from metadata_harmonization_processor.models.schema_alignment_results import SchemaAlignmentResults

class SchemaAlignmentResults(BaseModel):
    job_id: str
    version: int
    timestamp: datetime
    original_data_csv: str
    aligned_data_csv: str
    column_mappings: Dict[str, str]
    transformation_summary: Dict[str, Any]
```

**Fields:**
- `job_id`: Job identifier for tracking processing sessions
- `version`: Version number for result versioning
- `timestamp`: When results were created (UTC datetime)
- `original_data_csv`: Original CSV data before schema alignment
- `aligned_data_csv`: Schema-aligned CSV data after processing
- `column_mappings`: Dictionary mapping original column names to aligned column names
- `transformation_summary`: Detailed statistics about the alignment process

#### Methods

##### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert to dictionary for storage serialization.

**Returns:**
- `Dict[str, Any]`: Dictionary representation with ISO formatted timestamp

##### from_dict

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "SchemaAlignmentResults"
```

Create from dictionary loaded from storage.

**Parameters:**
- `data`: Dictionary with schema alignment results data

**Returns:**
- `SchemaAlignmentResults`: New instance with parsed datetime

**Features:**
- **Data Preservation**: Preserves both original and transformed CSV data for frontend consumption
- **Transformation Tracking**: Captures detailed column mappings and transformation summaries
- **Storage Serialization**: Provides methods for converting to/from dictionary format for storage
- **JSON Encoding**: Includes proper JSON encoders for datetime handling
- **Version Management**: Supports versioning for tracking changes over time

### SchemaInfo

Schema information for API responses.

```python
from metadata_harmonization_processor.interfaces import SchemaInfo

class SchemaInfo(BaseModel):
    core_uuid: str
    core_name: str
    core_path: str
    program_uuid: str
    program_name: str
    program_path: str
```

**Fields:**
- `core_uuid`: Unique identifier for core schema
- `core_name`: Human-readable name for core schema
- `core_path`: File path to core schema
- `program_uuid`: Unique identifier for program schema
- `program_name`: Human-readable name for program schema
- `program_path`: File path to program schema

## Processing Nodes

### SchemaAlignmentNode

Handles DataFrame column mapping and alignment to target schema structure. Inherits from AWS Strands MultiAgentBase.

```python
from metadata_harmonization_processor.nodes.schema_alignment import SchemaAlignmentNode
from strands.multiagent.base import MultiAgentBase, MultiAgentResult

class SchemaAlignmentNode(MultiAgentBase):
    def __init__(self, schema_collector: SchemaCollector) -> None

    async def invoke_async(
        self,
        task: str | list[ContentBlock],
        invocation_state: dict[str, Any] | None = None,
        **kwargs
    ) -> MultiAgentResult
```

**Note**: This node uses the new AWS Strands MultiAgentBase signature where ProcessorState is passed via `invocation_state` parameter.

**Features:**
- Intelligent case-insensitive column name matching
- Handles missing and extra columns
- Column reordering to match schema
- MultiAgentBase integration with standardized result handling
- Session management and state persistence

### ValidationNode

Performs comprehensive validation of aligned metadata against schema rules. Inherits from AWS Strands MultiAgentBase.

```python
from metadata_harmonization_processor.nodes.validation import ValidationNode
from strands.multiagent.base import MultiAgentBase, MultiAgentResult

class ValidationNode(MultiAgentBase):
    def __init__(self, schema_collector: SchemaCollector) -> None

    async def invoke_async(
        self,
        task: str | list[ContentBlock],
        invocation_state: dict[str, Any] | None = None,
        **kwargs
    ) -> MultiAgentResult
```

**Breaking Change**: The ValidationNode has been updated to use the new AWS Strands MultiAgentBase signature. The `ProcessorState` is now passed via the `invocation_state` parameter with the key `'processor_state'` instead of directly as the `task` parameter.

**Migration Guide:**
```python
# Old usage (deprecated)
result = await validation_node.invoke_async(processor_state)

# New usage
result = await validation_node.invoke_async(
    task="validation_task",  # Task description (unused in current implementation)
    invocation_state={"processor_state": processor_state}
)
```

**Parameters:**
- `task`: Task description string or list of ContentBlock (unused in current implementation)
- `invocation_state`: Dictionary containing the ProcessorState under the key `'processor_state'`
- `**kwargs`: Additional keyword arguments (unused)

**Returns:**
- `MultiAgentResult`: Result object with validation status and updated ProcessorState

**Validation Types:**
- Required field validation
- Valid options validation (enum)
- Pattern validation (regex)

**Features:**
- Updated AWS Strands MultiAgentBase integration with new signature
- Detailed error reporting with row and column information
- Error categorization and summary statistics
- Robust error handling for missing or invalid invocation state

### PatternBasedPredictionNode

Handles intelligent pattern-based corrections for common data quality issues. Inherits from AWS Strands MultiAgentBase.

```python
from metadata_harmonization_processor.nodes.pattern_prediction import PatternBasedPredictionNode
from strands.multiagent.base import MultiAgentBase, MultiAgentResult

class PatternBasedPredictionNode(MultiAgentBase):
    def __init__(self) -> None

    async def invoke_async(
        self,
        task: str | list[ContentBlock],
        invocation_state: dict[str, Any] | None = None,
        **kwargs
    ) -> MultiAgentResult
```

**Note**: This node uses the updated AWS Strands MultiAgentBase signature with `invocation_state` parameter, matching the ValidationNode and SchemaAlignmentNode pattern.

**Supported Patterns:**
- Date format corrections
- Numeric value cleaning
- Email normalization
- Phone number formatting
- URL protocol addition
- Name case corrections

### SemanticSearchPredictionNode

Provides AI-powered semantic search recommendations using embeddings. Inherits from AWS Strands MultiAgentBase.

```python
from metadata_harmonization_processor.nodes.semantic_prediction import SemanticSearchPredictionNode
from strands.multiagent.base import MultiAgentBase, MultiAgentResult

class SemanticSearchPredictionNode(MultiAgentBase):
    def __init__(self, config: ProcessorConfig) -> None

    async def invoke_async(self, task: ProcessorState, **kwargs) -> MultiAgentResult

    async def close(self) -> None
```

**Note**: This node still uses the legacy AWS Strands MultiAgentBase signature. It will be updated in a future release to match the ValidationNode and PatternBasedPredictionNode pattern.

**Features:**
- Amazon Bedrock and SageMaker support
- Hierarchical caching (Redis → In-memory → No cache)
- Cosine similarity matching
- Configurable similarity threshold
- MultiAgentBase integration with standardized result handling
- Session management and state persistence

#### Methods

##### close

```python
async def close(self) -> None
```

Clean up resources (Redis connections, AWS clients).

## Implementations

### DynamodbJobStatusSaver

DynamoDB implementation of JobStatusSaver interface.

```python
from metadata_harmonization_processor.implementations import DynamodbJobStatusSaver

class DynamodbJobStatusSaver(JobStatusSaver):
    def __init__(self, table_name: str, region: str = "us-east-1") -> None
```

**Parameters:**
- `table_name`: DynamoDB table name for job status storage
- `region`: AWS region for DynamoDB table

**Required DynamoDB Table Schema:**
```json
{
  "TableName": "job-status-table",
  "KeySchema": [
    {"AttributeName": "job_id", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "job_id", "AttributeType": "S"}
  ]
}
```

### S3ResultSaver

S3 implementation of ResultSaver for production environments with unified storage for combined ValidationResults and SchemaAlignmentResults.

```python
from metadata_harmonization_processor.implementations import S3ResultSaver

class S3ResultSaver(ResultSaver):
    def __init__(
        self,
        bucket_name: str,
        key_prefix: str = "validation-results/",
        region: str = "us-east-1",
        multipart_threshold: int = 100 * 1024 * 1024  # 100MB
    ) -> None
```

**Parameters:**
- `bucket_name`: S3 bucket name for storing results (required, cannot be empty)
- `key_prefix`: S3 key prefix for organization (automatically adds trailing slash if missing)
- `region`: AWS region for S3 operations
- `multipart_threshold`: Size threshold in bytes for multipart uploads (default: 100MB)

**Key Features:**
- **Unified Storage**: Stores both ValidationResults and SchemaAlignmentResults in the same S3 directory
- **Multipart Upload Support**: Automatically uses multipart uploads for files larger than the threshold
- **Robust Error Handling**: Comprehensive AWS error handling with proper ClientError management
- **Credential Validation**: Tests AWS credentials during initialization with minimal S3 operation
- **Adaptive Retry**: Built-in retry logic with adaptive retry mode for transient failures
- **Automatic Cleanup**: Cleans up failed multipart uploads automatically
- **Optimized Part Size**: Intelligent part size calculation for multipart uploads (minimum 5MB per S3 requirements)

**S3 Key Structure:**
Results are stored with the following unified directory structure:
```
{key_prefix}{job_id}/v{version}/
├── results.json                    # ValidationResults
├── original_data.csv              # Original CSV data (if SchemaAlignmentResults present)
├── aligned_data.csv               # Aligned CSV data (if SchemaAlignmentResults present)
├── column_mappings.json           # Column mappings (if SchemaAlignmentResults present)
└── transformation_summary.json    # Transformation summary (if SchemaAlignmentResults present)
```

Example: `validation-results/job-123/v1/results.json`

**Required S3 Bucket Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "arn:aws:s3:::bucket-name",
        "arn:aws:s3:::bucket-name/*"
      ]
    }
  ]
}
```

**Error Handling:**
- `ValueError`: Raised for invalid parameters (empty bucket_name, invalid version numbers)
- `ClientError`: AWS S3 service errors (NoSuchKey, AccessDenied, etc.)
- `NoCredentialsError`: Raised during initialization if AWS credentials are not available

### LocalResultSaver

Local file implementation of ResultSaver for development environments with unified storage for combined ValidationResults and SchemaAlignmentResults.

```python
from metadata_harmonization_processor.implementations import LocalResultSaver

class LocalResultSaver(ResultSaver):
    def __init__(self, storage_dir: str = "./validation-results") -> None
```

**Parameters:**
- `storage_dir`: Local directory for storing result files (supports both absolute and relative paths, defaults to "./validation-results")

**Key Features:**
- **Unified Storage**: Stores both ValidationResults and SchemaAlignmentResults in the same local directory
- **Organized Directory Structure**: Results stored with clear version tracking and artifact separation
- **Automatic Directory Creation**: Creates storage directory and job subdirectories automatically
- **Path Flexibility**: Supports both absolute and relative paths with proper path resolution
- **UTF-8 Encoding**: Proper encoding support for international characters in validation results
- **Version Management**: Clear version tracking with sorted listing by version number
- **Human-Readable Format**: Stores results as formatted JSON with metadata for easy debugging
- **No AWS Dependencies**: Works completely offline without AWS credentials or services
- **Robust Error Handling**: Comprehensive error handling for file system operations with detailed logging

**Local Directory Structure:**
Results are stored with the following unified directory pattern:
```
{storage_dir}/
├── job-123/
│   ├── v1/
│   │   ├── results.json                    # ValidationResults
│   │   ├── original_data.csv              # Original CSV data (if SchemaAlignmentResults present)
│   │   ├── aligned_data.csv               # Aligned CSV data (if SchemaAlignmentResults present)
│   │   ├── column_mappings.json           # Column mappings (if SchemaAlignmentResults present)
│   │   └── transformation_summary.json    # Transformation summary (if SchemaAlignmentResults present)
│   ├── v2/
│   │   └── results.json
│   └── v3/
│       └── results.json
└── job-456/
    └── v1/
        └── results.json
```

**Storage Format:**
Each results.json file contains:
```json
{
  "job_id": "job-123",
  "version": 1,
  "timestamp": "2024-01-15T10:30:00.000Z",
  "results": {
    "validation_results": [...],
    "summary": {...}
  },
  "metadata": {
    "processing_time": 45.2,
    "rows_processed": 100
  }
}
```

**Error Handling:**
- `ValueError`: Raised for invalid parameters (empty storage_dir, empty job_id, invalid version numbers)
- `OSError`: File system errors (permission denied, disk full, etc.)
- `json.JSONDecodeError`: Raised when reading corrupted JSON files

**Usage Example:**
```python
# Initialize with custom directory
result_saver = LocalResultSaver(storage_dir="/path/to/results")

# Save combined results with metadata
job_results = await result_saver.save_results(
    job_id="job-123",
    version=1,
    validation_results=validation_results,
    schema_alignment_results=schema_alignment_results,  # Optional
    metadata={"processing_time": 45.2, "rows_processed": 100}
)

# Retrieve combined results
validation_results, schema_alignment_results = await result_saver.get_results(job_results)

# List all versions for a job
all_versions = await result_saver.list_results("job-123")
```

## Logging Components

The package includes comprehensive logging and error handling components for detailed diagnostic information and troubleshooting. All logging components are available through the `logging` package:

```python
from metadata_harmonization_processor.logging import (
    ProcessorLogger,
    NodeExecutionTracker,
    ErrorContextBuilder,
    JobStatusLogger
)
```

### ProcessorLogger

Provides structured logging with context management and session persistence for debugging.

```python
from metadata_harmonization_processor.logging import ProcessorLogger

class ProcessorLogger:
    def __init__(self, logger_name: str, session_manager: SessionManager) -> None
```

**Parameters:**
- `logger_name`: Name for the logger instance (typically includes session ID)
- `session_manager`: AWS Strands session manager for persistent logging

#### Methods

##### log_with_context

```python
async def log_with_context(
    self,
    level: str,
    message: str,
    context: Dict[str, Any] = None,
    save_to_session: bool = False
) -> None
```

Log a message with structured context information.

**Parameters:**
- `level`: Log level ("DEBUG", "INFO", "WARNING", "ERROR")
- `message`: Log message
- `context`: Additional context dictionary
- `save_to_session`: Whether to save to session storage for debugging

##### log_processing_stage

```python
async def log_processing_stage(self, stage: str, data_info: Dict[str, Any]) -> None
```

Log processing stage information with data characteristics.

**Parameters:**
- `stage`: Processing stage name
- `data_info`: Information about data being processed

##### log_error_with_state

```python
async def log_error_with_state(
    self,
    error: Exception,
    state: ProcessorState,
    context: Dict[str, Any] = None
) -> None
```

Log an error with complete processor state context.

**Parameters:**
- `error`: Exception that occurred
- `state`: Current processor state
- `context`: Additional error context

##### log_performance_metrics

```python
async def log_performance_metrics(
    self,
    operation: str,
    duration: float,
    metrics: Dict[str, Any] = None
) -> None
```

Log performance metrics for operations.

**Parameters:**
- `operation`: Operation name
- `duration`: Duration in seconds
- `metrics`: Additional performance metrics

##### save_debug_state

```python
async def save_debug_state(self, key: str, state_data: Dict[str, Any]) -> None
```

Save debug state to session storage for post-mortem analysis.

**Parameters:**
- `key`: Storage key for the debug state
- `state_data`: Debug state data to save

### NodeExecutionTracker

Monitors AWS Strands node execution with performance tracking and progress logging.

```python
from metadata_harmonization_processor.logging import NodeExecutionTracker

class NodeExecutionTracker:
    def __init__(self, node_name: str, processor_logger: ProcessorLogger) -> None
```

**Parameters:**
- `node_name`: Name of the AWS Strands node being tracked
- `processor_logger`: ProcessorLogger instance for structured logging

#### Methods

##### start_execution

```python
async def start_execution(self, input_data_info: Dict[str, Any]) -> None
```

Start tracking node execution with input data information.

**Parameters:**
- `input_data_info`: Information about input data (shape, columns, etc.)

##### log_progress

```python
async def log_progress(
    self,
    step: str,
    progress: float,
    details: Dict[str, Any] = None
) -> None
```

Log progress during node execution.

**Parameters:**
- `step`: Current processing step
- `progress`: Progress value (0.0 to 1.0)
- `details`: Additional step details

##### log_intermediate_result

```python
async def log_intermediate_result(self, step: str, result_info: Dict[str, Any]) -> None
```

Log intermediate results during processing.

**Parameters:**
- `step`: Processing step name
- `result_info`: Information about intermediate results

##### complete_execution

```python
async def complete_execution(
    self,
    success: bool,
    result_info: Dict[str, Any] = None
) -> None
```

Complete node execution tracking.

**Parameters:**
- `success`: Whether execution completed successfully
- `result_info`: Final result information

##### handle_execution_error

```python
async def handle_execution_error(
    self,
    error: Exception,
    context: Dict[str, Any] = None
) -> None
```

Handle and log execution errors.

**Parameters:**
- `error`: Exception that occurred
- `context`: Additional error context

### ErrorContextBuilder

Builds comprehensive error context for different failure types to aid in debugging.

```python
from metadata_harmonization_processor.logging import ErrorContextBuilder

class ErrorContextBuilder:
    # Static methods for building different types of error context
```

#### Methods

##### build_schema_alignment_context

```python
@staticmethod
def build_schema_alignment_context(
    state: ProcessorState,
    error: Exception,
    additional_context: Dict[str, Any] = None
) -> Dict[str, Any]
```

Build error context for schema alignment failures.

**Parameters:**
- `state`: Current processor state
- `error`: Schema alignment error
- `additional_context`: Additional context information

**Returns:**
- `Dict[str, Any]`: Comprehensive error context with alignment diagnostics

##### build_validation_context

```python
@staticmethod
def build_validation_context(
    state: ProcessorState,
    error: Exception,
    additional_context: Dict[str, Any] = None
) -> Dict[str, Any]
```

Build error context for validation failures.

**Parameters:**
- `state`: Current processor state
- `error`: Validation error
- `additional_context`: Additional context information

**Returns:**
- `Dict[str, Any]`: Comprehensive error context with validation diagnostics

##### build_prediction_context

```python
@staticmethod
def build_prediction_context(
    state: ProcessorState,
    error: Exception,
    prediction_type: str,
    additional_context: Dict[str, Any] = None
) -> Dict[str, Any]
```

Build error context for prediction failures.

**Parameters:**
- `state`: Current processor state
- `error`: Prediction error
- `prediction_type`: Type of prediction ("semantic" or "pattern")
- `additional_context`: Additional context information

**Returns:**
- `Dict[str, Any]`: Comprehensive error context with prediction diagnostics

##### build_job_status_context

```python
@staticmethod
def build_job_status_context(
    job: Optional[MetadataUploadJob],
    error: Exception,
    status: str,
    additional_context: Dict[str, Any] = None
) -> Dict[str, Any]
```

Build error context for job status failures.

**Parameters:**
- `job`: Job object (may be None if job creation failed)
- `error`: Job status error
- `status`: Current job status
- `additional_context`: Additional context information

**Returns:**
- `Dict[str, Any]`: Comprehensive error context with job lifecycle information

### JobStatusLogger

Provides detailed job lifecycle tracking and status management with comprehensive logging.

```python
from metadata_harmonization_processor.logging import JobStatusLogger

class JobStatusLogger:
    def __init__(self, processor_logger: ProcessorLogger) -> None
```

**Parameters:**
- `processor_logger`: ProcessorLogger instance for structured logging

#### Methods

##### log_job_creation

```python
async def log_job_creation(self, job: MetadataUploadJob) -> None
```

Log job creation with complete job details.

**Parameters:**
- `job`: Created job object

##### log_status_transition

```python
async def log_status_transition(
    self,
    job_id: str,
    from_status: Optional[str],
    to_status: str,
    reason: str
) -> None
```

Log job status transitions with reasons.

**Parameters:**
- `job_id`: Job identifier
- `from_status`: Previous status (None for initial status)
- `to_status`: New status
- `reason`: Reason for status change

##### log_completion_with_results

```python
async def log_completion_with_results(
    self,
    job_id: str,
    results: ValidationResults,
    metadata: Dict[str, Any]
) -> None
```

Log job completion with validation results and performance metrics.

**Parameters:**
- `job_id`: Job identifier
- `results`: Validation results
- `metadata`: Processing metadata (duration, performance metrics, etc.)

##### log_failure_with_context

```python
async def log_failure_with_context(
    self,
    job_id: str,
    error: Exception,
    context: Dict[str, Any]
) -> None
```

Log job failure with comprehensive error context.

**Parameters:**
- `job_id`: Job identifier
- `error`: Exception that caused failure
- `context`: Error context from ErrorContextBuilder

##### log_results_save_operation

```python
async def log_results_save_operation(
    self,
    job_id: str,
    success: bool,
    details: Dict[str, Any]
) -> None
```

Log results save operations (S3, local file, etc.).

**Parameters:**
- `job_id`: Job identifier
- `success`: Whether save operation succeeded
- `details`: Save operation details (storage type, location, etc.)

### Usage Example

```python
import asyncio
from metadata_harmonization_processor.logging import (
    ProcessorLogger,
    NodeExecutionTracker,
    JobStatusLogger
)

async def example_logging_usage():
    # Initialize logging components
    processor_logger = ProcessorLogger(
        logger_name="example_processor",
        session_manager=session_manager
    )

    job_logger = JobStatusLogger(processor_logger)
    node_tracker = NodeExecutionTracker("validation", processor_logger)

    # Log structured information
    await processor_logger.log_with_context(
        "INFO",
        "Starting metadata processing",
        {
            "job_id": "job-123",
            "input_data": {"rows": 100, "columns": 15},
            "schemas": {"core": "core_v1", "program": "flu_v1"}
        }
    )

    # Track node execution
    await node_tracker.start_execution({"input_shape": [100, 15]})
    await node_tracker.log_progress("validation_rules", 0.5, {"rules_applied": 10})
    await node_tracker.complete_execution(True, {"errors_found": 5})

    # Log job status changes
    await job_logger.log_status_transition(
        "job-123", "pending", "processing", "Starting validation pipeline"
    )

    # Save debug state
    await processor_logger.save_debug_state(
        "processing_state",
        {
            "current_stage": "validation",
            "progress": 0.5,
            "intermediate_results": {"errors_found": 5}
        }
    )

# Run the example
asyncio.run(example_logging_usage())
```

### FileBasedSchemaCollector

File-based implementation using catalog.json and schema directory.

```python
from metadata_harmonization_processor.implementations import FileBasedSchemaCollector

class FileBasedSchemaCollector(SchemaCollector):
    def __init__(self, schema_directory: str) -> None
```

**Parameters:**
- `schema_directory`: Path to directory containing catalog.json and schema files

**Required Directory Structure:**
```
schema_directory/
├── catalog.json
├── core_schema_v1.json
├── program_schema_v1.json
└── ...
```

**Catalog.json Format:**
```json
[
  {
    "core_uuid": "core-001",
    "core_name": "Patient Core Schema",
    "core_path": "core_schema_v1.json",
    "program": [
      {
        "program_uuid": "prog-001",
        "program_name": "Flu Surveillance",
        "program_path": "flu_program_v1.json"
      }
    ]
  }
]
```

## Configuration

### ProcessorConfig

Pydantic settings class for processor configuration.

```python
from metadata_harmonization_processor.config import ProcessorConfig, load_processor_settings

class ProcessorConfig(BaseSettings):
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None

    # Session Management
    session_saver_type: Literal["file", "s3"] = "s3"

    # Local Development Mode Configuration
    local_development_mode: bool = False

    # Job Status Saver Configuration
    job_status_saver: Optional[Dict[str, Any]] = None

    # Redis Configuration
    enable_redis_cache: bool = True
    redis_endpoint: Optional[str] = None
    redis_port: int = 6379

    # In-Memory Cache Configuration
    enable_memory_cache: bool = True
    memory_cache_max_size: int = 10000

    # AI Model Configuration
    embedding_provider: Literal["bedrock", "sagemaker"] = "bedrock"
    bedrock_model_id: Optional[str] = "amazon.titan-embed-text-v1"
    sagemaker_endpoint_name: Optional[str] = None

    # Processing Configuration
    max_retries: int = 3
    timeout_seconds: int = 300
    cosine_similarity_threshold: float = 0.8

    # Schema Configuration
    schema_directory: str

    # Schema Alignment Configuration
    schema_alignment: SchemaAlignmentConfig = SchemaAlignmentConfig()
```

### SchemaAlignmentConfig

Configuration class for LLM-enhanced schema alignment processing.

```python
from metadata_harmonization_processor.config import SchemaAlignmentConfig

class SchemaAlignmentConfig(BaseSettings):
    # LLM Configuration
    use_llm: bool = True
    model_id: str = "amazon.nova-pro-v1:0"
    aws_region: str = "us-east-1"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 800
    llm_timeout_seconds: int = 30
    fallback_on_llm_failure: bool = True

    # Rule-based Configuration
    similarity_threshold: float = 0.7

    # Change Tracking Configuration
    enable_change_tracking: bool = True
```

**Configuration Fields:**

- **LLM Configuration**:
  - `use_llm`: Enable/disable LLM matching for semantic column alignment
  - `model_id`: Bedrock model ID for semantic matching (e.g., "amazon.nova-pro-v1:0")
  - `aws_region`: AWS region for Bedrock client
  - `llm_temperature`: Temperature for LLM inference (0.0-1.0)
  - `llm_max_tokens`: Maximum tokens for LLM response
  - `llm_timeout_seconds`: Timeout for LLM requests
  - `fallback_on_llm_failure`: Automatically fallback to rule-based matching on LLM failure

- **Rule-based Configuration**:
  - `similarity_threshold`: Threshold for rule-based string similarity matching (0.0-1.0)

- **Change Tracking Configuration**:
  - `enable_change_tracking`: Enable detailed change detection and tracking

**Environment Variables:**
All settings can be overridden using environment variables with the `SCHEMA_ALIGNMENT_` prefix:

```bash
export SCHEMA_ALIGNMENT_USE_LLM=false
export SCHEMA_ALIGNMENT_MODEL_ID="amazon.nova-lite-v1:0"
export SCHEMA_ALIGNMENT_SIMILARITY_THRESHOLD=0.8
```

**New Configuration Fields:**

- `local_development_mode`: Boolean flag to enable local development mode without requiring cloud services. When enabled, the processor can work with local implementations like `LocalJobStatusSaver` without AWS credentials.

- `job_status_saver`: Optional dictionary containing job status saver configuration. This allows configuration-driven selection between different JobStatusSaver implementations:
  ```yaml
  job_status_saver:
    type: "local"  # or "dynamodb"
    storage_type: "file"  # for local type: "memory" or "file"
    storage_dir: "./job_status"  # for local file storage
    table_name: "metadata-jobs"  # for dynamodb type
  ```

### load_processor_settings

```python
def load_processor_settings(
    config_path: Optional[Path] = None,
    override: Dict[str, Any] = {}
) -> ProcessorConfig
```

Load hierarchical processor settings from YAML file with overrides.

**Parameters:**
- `config_path`: Optional path to configuration YAML file
- `override`: Optional dictionary of settings to override

**Returns:**
- `ProcessorConfig`: Loaded processor settings with path resolution

## Exceptions

### ProcessorError

Base exception for all processor-related errors.

```python
from metadata_harmonization_processor.exceptions import ProcessorError

class ProcessorError(Exception):
    """Base exception for processor errors."""
    pass
```

### ConfigurationError

Configuration-related errors (invalid YAML, missing required fields).

```python
from metadata_harmonization_processor.exceptions import ConfigurationError

class ConfigurationError(ProcessorError):
    """Configuration-related errors."""
    pass
```

### SchemaError

Schema collection and validation errors.

```python
from metadata_harmonization_processor.exceptions import SchemaError

class SchemaError(ProcessorError):
    """Schema collection and validation errors."""
    pass
```

### ProcessingError

Data processing errors during pipeline execution.

```python
from metadata_harmonization_processor.exceptions import ProcessingError

class ProcessingError(ProcessorError):
    """Data processing errors."""
    pass
```

### ExternalServiceError

External service communication errors (AWS services, Redis, etc.).

```python
from metadata_harmonization_processor.exceptions import ExternalServiceError

class ExternalServiceError(ProcessorError):
    """External service communication errors."""
    pass
```

## Usage Patterns

### Basic Usage

For a complete working example with real Cyclospora metadata and comprehensive error handling, see [`examples/basic_usage.py`](../examples/basic_usage.py).

```python
import asyncio
import pandas as pd
from pathlib import Path
from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import load_processor_settings
from metadata_harmonization_processor.implementations import (
    DynamodbJobStatusSaver, FileBasedSchemaCollector
)

async def basic_usage():
    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"basic-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,  # Contains DynamoDB and schema collector configuration
        session_id=session_id
    )

    results = await processor.process(metadata_df, program_id="program-id", core_id="core-id")
    await processor.cleanup()
```

### Custom Implementation

```python
class CustomJobStatusSaver(JobStatusSaver):
    async def save_status(self, job_id: str, status: str, metadata: dict) -> None:
        # Custom implementation
        pass

    async def get_status(self, job_id: str) -> Optional[dict]:
        # Custom implementation
        pass

    async def update_progress(self, job_id: str, stage: str, progress: float) -> None:
        # Custom implementation
        pass

# Use with processor
config = load_processor_settings(config_path=Path("config.yaml"))
# Note: Custom implementations now require configuration-based setup
# The processor creates components from configuration automatically
processor = MetadataHarmonizationProcessor(
    config=config,  # Contains custom component configurations
    session_id=session_id
)
```

### Error Handling

```python
from metadata_harmonization_processor.exceptions import (
    ConfigurationError, SchemaError, ProcessingError
)

try:
    results = await processor.process(metadata_df)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except SchemaError as e:
    print(f"Schema error: {e}")
except ProcessingError as e:
    print(f"Processing error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    await processor.cleanup()
```
