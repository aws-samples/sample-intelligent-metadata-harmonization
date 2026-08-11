# Migration Guide

This document provides guidance for migrating between versions of the metadata-harmonization-processor package.

## Version 0.2.0 - Configuration Structure and Constructor Update

### Overview

The processor has been updated to use a unified configuration-driven architecture. The constructor now creates all components (JobStatusSaver, ResultSaver, SchemaCollector) from configuration automatically, eliminating the need for manual component instantiation. The configuration structure has also been updated to support the new data saver architecture with separate job status and result storage.

### What Changed

#### 1. Constructor Signature Update

The MetadataHarmonizationProcessor constructor has been simplified to use configuration-driven component creation:

**Before (Legacy):**
```python
# Manual component creation
job_saver = LocalJobStatusSaver(storage_type="file", storage_dir="./job_status")
schema_collector = FileBasedSchemaCollector("./data/schema")

processor = MetadataHarmonizationProcessor(
    config=config,
    job_status_saver=job_saver,
    schema_collector=schema_collector,
    session_id=session_id
)
```

**After (New):**
```python
# Configuration-driven component creation
processor = MetadataHarmonizationProcessor(
    config=config,  # Contains all component configurations
    session_id=session_id,
    session_config=session_config  # Optional session manager config
)
```

#### 2. Configuration Structure Update

The configuration structure has been updated from a nested object to flat typed fields:

**Before (Legacy):**
```yaml
job_status_saver:
  type: "local"
  storage_type: "file"
  storage_dir: "./job_status"
  # OR for DynamoDB
  type: "dynamodb"
  table_name: "metadata-jobs"
```

**After (New):**
```yaml
# Job Status Saver Configuration
job_status_saver_type: "local"  # or "dynamodb"
job_status_storage_dir: "./data/job_status"  # for local type
job_status_table_name: "metadata-jobs"  # for dynamodb type

# Result Saver Configuration (NEW)
result_saver_type: "local"  # or "s3"
results_local_dir: "./data/validation-results"  # for local type
results_s3_bucket: "my-results-bucket"  # for s3 type
results_s3_prefix: "validation-results/"
```

### Migration Steps

#### 1. Update Configuration Files

**Before:**
```yaml
# config.yaml (old structure)
job_status_saver:
  type: "local"
  storage_type: "file"
  storage_dir: "./job_status"
```

**After:**
```yaml
# config.yaml (new structure)
job_status_saver_type: "local"
job_status_storage_dir: "./data/job_status"
result_saver_type: "local"
results_local_dir: "./data/validation-results"
```

#### 2. Update Processor Instantiation

**Before:**
```python
# Manual component creation and injection
job_saver = LocalJobStatusSaver(storage_type="file", storage_dir="./job_status")
schema_collector = FileBasedSchemaCollector("./data/schema")

processor = MetadataHarmonizationProcessor(
    config=config,
    job_status_saver=job_saver,
    schema_collector=schema_collector,
    session_id=session_id
)
```

**After:**
```python
# Configuration-driven component creation
processor = MetadataHarmonizationProcessor(
    config=config,  # Contains all component configurations
    session_id=session_id
)
```

#### 3. Update Component Creation Logic (if using custom implementations)

**Before:**
```python
def create_job_status_saver(config: ProcessorConfig):
    if config.job_status_saver:
        saver_config = config.job_status_saver
        saver_type = saver_config.get("type", "local")

        if saver_type == "local":
            storage_type = saver_config.get("storage_type", "file")
            storage_dir = saver_config.get("storage_dir", "./job_status")
            return LocalJobStatusSaver(storage_type=storage_type, storage_dir=storage_dir)
```

**After:**
```python
# Component creation is now handled internally by the processor
# Custom implementations can be configured via the new typed fields
# No manual component creation needed
```

#### 3. Configuration Validation Changes

The new configuration includes automatic validation:

- `job_status_table_name` is required when `job_status_saver_type` is "dynamodb"
- `job_status_storage_dir` is required when `job_status_saver_type` is "local"
- `results_s3_bucket` is required when `result_saver_type` is "s3"

### New Features

#### Result Saver Configuration

The new configuration structure introduces result storage configuration:

```yaml
# Store ValidationResults in S3 (production)
result_saver_type: "s3"
results_s3_bucket: "my-validation-results"
results_s3_prefix: "results/"

# Store ValidationResults locally (development)
result_saver_type: "local"
results_local_dir: "./data/validation-results"
```

#### S3ResultSaver Implementation

The S3ResultSaver is now fully implemented with production-ready features:

- **Multipart Upload Support**: Automatically handles large files (>100MB) with multipart uploads
- **Robust Error Handling**: Comprehensive AWS error handling with proper retry logic
- **Credential Validation**: Tests AWS credentials during initialization
- **Automatic Cleanup**: Cleans up failed multipart uploads automatically
- **Optimized Performance**: Intelligent part size calculation and adaptive retry settings

**Configuration Example:**
```yaml
result_saver_type: "s3"
results_s3_bucket: "my-validation-results"
results_s3_prefix: "validation-results/"
aws_region: "us-east-1"
```

#### Path Resolution

The new configuration automatically resolves relative paths for:
- `schema_directory`
- `file_session_directory`
- `job_status_storage_dir`
- `results_local_dir`

### Backward Compatibility

This is a breaking change with no backward compatibility. The old constructor signature and nested `job_status_saver` configuration are no longer supported. However, migration is straightforward:

1. **Constructor Calls**: Update all MetadataHarmonizationProcessor instantiation to use the new signature
2. **Configuration Files**: Update YAML files to use the new flat structure
3. **Component Creation**: Remove manual component creation code - the processor handles this automatically
4. **Validation**: The new structure provides better validation and clearer error messages

### Example Migration

**Complete Before/After Example:**

```yaml
# BEFORE (config-old.yaml)
aws_region: "us-east-1"
session_saver_type: "file"
file_session_directory: "./sessions"
schema_directory: "./schemas"

job_status_saver:
  type: "local"
  storage_type: "file"
  storage_dir: "./job_status"

enable_redis_cache: false
```

```yaml
# AFTER (config-new.yaml)
aws_region: "us-east-1"
session_saver_type: "file"
file_session_directory: "./sessions"
schema_directory: "./schemas"

# Data Saver Configuration
job_status_saver_type: "local"
job_status_storage_dir: "./data/job_status"
result_saver_type: "local"
results_local_dir: "./data/validation-results"

enable_redis_cache: false
```

### Getting Help

If you encounter issues during migration:

1. Check the [Configuration Examples](../examples/) for updated templates
2. Review the [API Documentation](API.md) for new configuration fields
3. Consult the [troubleshooting guide](TROUBLESHOOTING.md) for common configuration issues
4. Create an issue in the project repository with your configuration file

### Summary

- **Breaking Change**: Constructor signature updated to configuration-driven approach
- **Breaking Change**: Configuration structure updated from nested to flat typed fields
- **Impact**: All MetadataHarmonizationProcessor instantiation and configuration files
- **Action Required**: Update constructor calls and YAML files to use new structure
- **New Feature**: Unified data saver architecture with automatic component creation
- **New Feature**: Result saver configuration for storing ValidationResults
- **Timeline**: Effective immediately in version 0.2.0

## Version 0.1.0 - Processing Nodes API Update

### Overview

The `SchemaAlignmentNode` and `ValidationNode` classes have been updated to use the new AWS Strands MultiAgentBase signature pattern. This change aligns these nodes with the latest AWS Strands architecture but introduces a breaking change for direct usage of these nodes.

### What Changed

The `invoke_async` method signature has been updated:

**Before (Legacy):**
```python
async def invoke_async(self, task: ProcessorState, **kwargs) -> MultiAgentResult
```

**After (New):**
```python
async def invoke_async(
    self,
    task: str | list[ContentBlock],
    invocation_state: dict[str, Any] | None = None,
    **kwargs
) -> MultiAgentResult
```

### Migration Steps

#### 1. Direct ValidationNode Usage

If you're using ValidationNode directly, update your code:

**Before:**
```python
from metadata_harmonization_processor.nodes.schema_alignment import SchemaAlignmentNode
from metadata_harmonization_processor.nodes.validation import ValidationNode
from metadata_harmonization_processor.models.state import ProcessorState

# Create nodes
schema_alignment_node = SchemaAlignmentNode(schema_collector)
validation_node = ValidationNode(schema_collector)

# Old usage
result = await schema_alignment_node.invoke_async(processor_state)
result = await validation_node.invoke_async(processor_state)
```

**After:**
```python
from metadata_harmonization_processor.nodes.schema_alignment import SchemaAlignmentNode
from metadata_harmonization_processor.nodes.validation import ValidationNode
from metadata_harmonization_processor.models.state import ProcessorState

# Create nodes
schema_alignment_node = SchemaAlignmentNode(schema_collector)
validation_node = ValidationNode(schema_collector)

# New usage
result = await schema_alignment_node.invoke_async(
    task="schema_alignment_task",  # Task description (can be any string)
    invocation_state={"processor_state": processor_state}
)
result = await validation_node.invoke_async(
    task="validation_task",  # Task description (can be any string)
    invocation_state={"processor_state": processor_state}
)
```

#### 2. High-Level API Usage (No Changes Required)

If you're using the `MetadataHarmonizationProcessor` class, no changes are required:

```python
# This code continues to work without changes
processor = MetadataHarmonizationProcessor(
    config=config,
    job_status_saver=job_saver,
    schema_collector=schema_collector,
    session_id=session_id
)

results = await processor.process(metadata_df, program_id="flu", core_id="core_v1")
```

### Error Handling Updates

The new ValidationNode provides enhanced error handling for missing or invalid invocation state:

```python
# The node now validates the invocation_state parameter
result = await validation_node.invoke_async(
    task="validation_task",
    invocation_state={}  # Missing 'processor_state' key
)

# This will return a failed MultiAgentResult with a descriptive error message
if result.status == Status.FAILED:
    error_msg = result.results["validation"].result
    print(f"Validation failed: {error_msg}")
    # Output: "Validation failed: invocation_state must contain 'processor_state'"
```

### Testing Updates

If you have unit tests that directly test ValidationNode, update them:

**Before:**
```python
@pytest.mark.asyncio
async def test_validation_node():
    validation_node = ValidationNode(mock_schema_collector)
    result = await validation_node.invoke_async(processor_state)
    assert result.status == Status.COMPLETED
```

**After:**
```python
@pytest.mark.asyncio
async def test_validation_node():
    validation_node = ValidationNode(mock_schema_collector)
    result = await validation_node.invoke_async(
        task="test_validation",
        invocation_state={"processor_state": processor_state}
    )
    assert result.status == Status.COMPLETED
```

### Future Changes

Other processing nodes will be updated in future releases to maintain consistency:

- `SemanticSearchPredictionNode` - Will be updated to use the new signature
- `PatternBasedPredictionNode` - ✅ Updated to use the new signature

### Backward Compatibility

This is a breaking change with no backward compatibility. The old signature is no longer supported. However, the impact is minimal since:

1. Most users interact with the high-level `MetadataHarmonizationProcessor` API
2. Direct node usage is primarily for advanced use cases and custom implementations
3. The change aligns with AWS Strands best practices for better integration

### Getting Help

If you encounter issues during migration:

1. Check the [API Documentation](API.md) for updated method signatures
2. Review the [examples](../examples/) for current usage patterns
3. Consult the [troubleshooting guide](TROUBLESHOOTING.md) for common issues
4. Create an issue in the project repository with detailed error messages

### Summary

- **Breaking Change**: SchemaAlignmentNode and ValidationNode invoke_async() signatures updated
- **Impact**: Direct node usage only
- **Action Required**: Update direct node calls to use new signature with invocation_state
- **High-Level API**: No changes required for MetadataHarmonizationProcessor usage
- **Timeline**: SemanticSearchPredictionNode will be updated in a future release for consistency
