# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using the MetadataHarmonizationProcessor package.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [AWS Service Issues](#aws-service-issues)
- [Schema-Related Problems](#schema-related-problems)
- [Processing Errors](#processing-errors)
- [Performance Issues](#performance-issues)
- [Debugging Tips](#debugging-tips)

## Installation Issues

### Package Installation Fails

**Problem:** `pip install` fails with dependency conflicts or build errors.

**Solutions:**

1. **Update pip and setuptools:**
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

2. **Use virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```

3. **Install with specific Python version:**
   ```bash
   python3.9 -m pip install -e .
   ```

4. **Check Python version compatibility:**
   ```bash
   python --version  # Should be 3.9 or higher
   ```

### AWS Strands Import Errors

**Problem:** `ImportError: No module named 'strands'` or similar AWS Strands related errors.

**Solutions:**

1. **AWS Strands is required** - The package requires AWS Strands as a mandatory dependency:
   ```bash
   # Install the package with all dependencies
   pip install -e .
   ```

2. **Verify the correct package is installed:**
   - The package uses `strands-agents` from the specified Git repository
   - Ensure you have the correct package installed: `pip install strands-agents @ git+https://github.com/dbschmigelski/sdk-python.git@kwargs-multiagents`

3. **Contact your AWS representative:**
   - AWS Strands is an internal AWS package required for operation
   - Request access to the AWS Strands package for your development environment
   - The processor cannot function without Strands for MultiAgentBase workflow orchestration

4. **Verify installation:**
   ```python
   from strands.multiagent.base import MultiAgentBase
   print("✓ AWS Strands is available")
   ```

### Missing Optional Dependencies

**Problem:** `ModuleNotFoundError` for Redis, boto3, or other optional dependencies.

**Solutions:**

1. **Install with all dependencies:**
   ```bash
   pip install -e .[dev]  # Includes all optional dependencies
   ```

2. **Install specific extras:**
   ```bash
   pip install -e .[test]  # Test dependencies only
   pip install -e .[docs]  # Documentation dependencies only
   ```

3. **Manual dependency installation:**
   ```bash
   pip install redis boto3 scikit-learn
   ```

## Configuration Problems

### YAML Configuration Errors

**Problem:** `ConfigurationError: Invalid YAML configuration` or parsing errors.

**Solutions:**

1. **Validate YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

2. **Check indentation (use spaces, not tabs):**
   ```yaml
   # Correct
   aws_region: "us-east-1"
   redis_config:
     endpoint: "localhost"
     port: 6379

   # Incorrect (mixed tabs/spaces)
   aws_region: "us-east-1"
   	redis_config:
   	  endpoint: "localhost"
   ```

3. **Verify required fields:**
   ```yaml
   # Minimum required configuration
   schema_directory: "./data/schema"  # Required
   aws_region: "us-east-1"           # Required for AWS services
   ```

4. **Use configuration validation:**
   ```python
   from metadata_harmonization_processor.config import load_processor_settings

   try:
       config = load_processor_settings("config.yaml")
       print("Configuration valid!")
   except Exception as e:
       print(f"Configuration error: {e}")
   ```

### Path Resolution Issues

**Problem:** `FileNotFoundError` for schema directory or configuration files.

**Solutions:**

1. **Use absolute paths:**
   ```yaml
   schema_directory: "/full/path/to/schemas"
   ```

2. **Verify relative path resolution:**
   ```python
   from pathlib import Path
   config_path = Path("config.yaml")
   schema_dir = config_path.parent / "data" / "schema"
   print(f"Schema directory: {schema_dir.absolute()}")
   ```

3. **Check file permissions:**
   ```bash
   ls -la data/schema/
   # Ensure read permissions on catalog.json and schema files
   ```

### Environment Variable Issues

**Problem:** Configuration not loading from environment variables.

**Solutions:**

1. **Use correct environment variable names:**
   ```bash
   export AWS_REGION="us-west-2"
   export REDIS_ENDPOINT="my-redis.cache.amazonaws.com"
   export SCHEMA_DIRECTORY="/path/to/schemas"
   ```

2. **Check Pydantic Settings precedence:**
   ```python
   # Order: CLI args > env vars > config file > defaults
   config = ProcessorConfig(
       aws_region="us-east-1",  # This overrides env var
       _env_file=".env"         # Load from .env file
   )
   ```

## AWS Service Issues

### Authentication Problems

**Problem:** `NoCredentialsError` or `AccessDenied` when accessing AWS services.

**Solutions:**

1. **Configure AWS credentials:**
   ```bash
   aws configure
   # Or set environment variables:
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

2. **Use IAM roles (recommended for production):**
   ```yaml
   # Don't set aws_profile in production
   aws_region: "us-east-1"
   # IAM role will be used automatically
   ```

3. **Verify credentials:**
   ```bash
   aws sts get-caller-identity
   ```

4. **Check IAM permissions:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "dynamodb:GetItem",
           "dynamodb:PutItem",
           "dynamodb:UpdateItem",
           "s3:GetObject",
           "s3:PutObject",
           "bedrock:InvokeModel",
           "sagemaker:InvokeEndpoint",
           "elasticache:*"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

### DynamoDB Issues

**Problem:** `ResourceNotFoundException` or DynamoDB operation failures.

**Solutions:**

1. **Create DynamoDB table:**
   ```bash
   aws dynamodb create-table \
     --table-name metadata-processor-jobs \
     --attribute-definitions AttributeName=job_id,AttributeType=S \
     --key-schema AttributeName=job_id,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

2. **Verify table exists:**
   ```bash
   aws dynamodb describe-table --table-name metadata-processor-jobs
   ```

3. **Check table permissions:**
   ```python
   import boto3

   dynamodb = boto3.client('dynamodb')
   try:
       response = dynamodb.describe_table(TableName='metadata-processor-jobs')
       print("Table accessible")
   except Exception as e:
       print(f"Table access error: {e}")
   ```

### Redis Connection Issues

**Problem:** `ConnectionError` or Redis timeout errors.

**Solutions:**

1. **Verify Redis endpoint:**
   ```bash
   redis-cli -h your-redis-endpoint.cache.amazonaws.com -p 6379 ping
   ```

2. **Check security groups:**
   - Ensure port 6379 is open for your application
   - Verify VPC configuration for ElastiCache

3. **Test Redis connectivity:**
   ```python
   import redis

   try:
       r = redis.Redis(host='localhost', port=6379, decode_responses=True)
       r.ping()
       print("Redis connected")
   except Exception as e:
       print(f"Redis error: {e}")
   ```

4. **Disable Redis if unavailable:**
   ```yaml
   enable_redis_cache: false
   enable_memory_cache: true  # Use in-memory fallback
   ```

### Bedrock/SageMaker Issues

**Problem:** `ModelNotFoundError` or AI service invocation failures.

**Solutions:**

1. **Verify model availability:**
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

2. **Check model ID format:**
   ```yaml
   # Correct Bedrock model IDs
   bedrock_model_id: "amazon.titan-embed-text-v1"
   bedrock_model_id: "cohere.embed-english-v3"
   ```

3. **Test SageMaker endpoint:**
   ```bash
   aws sagemaker describe-endpoint --endpoint-name your-endpoint-name
   ```

4. **Handle service unavailability:**
   ```python
   # The processor gracefully handles AI service failures
   # Pattern-based predictions will still work
   try:
       results = await processor.process(df, program_id="program-id", core_id="core-id")
   except ExternalServiceError as e:
       print(f"AI services unavailable: {e}")
       # Results will contain pattern-based predictions only
   ```

## Schema-Related Problems

### Catalog.json Issues

**Problem:** `SchemaError: Invalid catalog.json format` or schema loading failures.

**Solutions:**

1. **Validate catalog.json format:**
   ```python
   import json

   with open('data/schema/catalog.json') as f:
       catalog = json.load(f)

   # Verify structure
   assert isinstance(catalog, list)
   assert all('core_uuid' in item for item in catalog)
   assert all('program' in item for item in catalog)
   ```

2. **Check required fields:**
   ```json
   [
     {
       "core_uuid": "required-string",
       "core_name": "required-string",
       "core_path": "required-string",
       "program": [
         {
           "program_uuid": "required-string",
           "program_name": "required-string",
           "program_path": "required-string"
         }
       ]
     }
   ]
   ```

3. **Verify file paths in catalog:**
   ```python
   from pathlib import Path

   schema_dir = Path("data/schema")
   catalog_path = schema_dir / "catalog.json"

   with open(catalog_path) as f:
       catalog = json.load(f)

   # Check all referenced files exist
   for core_entry in catalog:
       core_file = schema_dir / core_entry["core_path"]
       assert core_file.exists(), f"Missing core schema: {core_file}"

       for program_entry in core_entry["program"]:
           program_file = schema_dir / program_entry["program_path"]
           assert program_file.exists(), f"Missing program schema: {program_file}"
   ```

### Schema Validation Issues

**Problem:** Schema files contain invalid JSON Schema or missing validation rules.

**Solutions:**

1. **Validate JSON Schema format:**
   ```python
   import json
   import jsonschema

   with open('schema_file.json') as f:
       schema = json.load(f)

   # Validate against JSON Schema meta-schema
   jsonschema.Draft7Validator.check_schema(schema)
   ```

2. **Check required AMD validation attributes:**
   ```json
   {
     "type": "object",
     "properties": {
       "field_name": {
         "type": "string",
         "amd_required": true,        // Required for validation
         "enum": ["option1", "option2"], // For INVALID_OPTION validation
         "pattern": "^[A-Z]+$"       // For INVALID_PATTERN validation
       }
     }
   }
   ```

3. **Test schema loading:**
   ```python
   from metadata_harmonization_processor.implementations import FileBasedSchemaCollector

   collector = FileBasedSchemaCollector("./data/schema")

   try:
       schemas = await collector.get_available_schemas()
       print(f"Found {len(schemas)} schema combinations")

       # Test specific schema
       schema = await collector.get_schema("program-id", "core-id")
       rules = await collector.get_validation_rules("program-id", "core-id")
       print(f"Validation rules: {rules}")

   except Exception as e:
       print(f"Schema error: {e}")
   ```

## Processing Errors

### DataFrame Processing Issues

**Problem:** `ProcessingError` during schema alignment or validation.

**Solutions:**

1. **Check DataFrame format:**
   ```python
   import pandas as pd

   # Ensure proper DataFrame structure
   print(f"DataFrame shape: {df.shape}")
   print(f"Column names: {list(df.columns)}")
   print(f"Data types: {df.dtypes}")

   # Check for problematic values
   print(f"Null values: {df.isnull().sum()}")
   print(f"Empty strings: {(df == '').sum()}")
   ```

2. **Handle special characters in column names:**
   ```python
   # Clean column names before processing
   df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
   ```

3. **Debug schema alignment:**
   ```python
   from metadata_harmonization_processor.nodes.schema_alignment import SchemaAlignmentNode

   alignment_node = SchemaAlignmentNode(schema_collector)

   # Create test state
   state = ProcessorState(
       metadata_df=df,
       program_id="test-program",
       core_id="test-core"
   )

   try:
       result = await alignment_node.invoke_async(
           task="schema_alignment_task",
           invocation_state={"processor_state": state}
       )
       if result.status.name == 'COMPLETED':
           aligned_state = result.results["schema_alignment"].result
           print(f"Aligned columns: {list(aligned_state.aligned_df.columns)}")
       else:
           print(f"Alignment failed: {result.results['schema_alignment'].result}")
   except Exception as e:
       print(f"Alignment error: {e}")
   ```

### Validation Logic Issues

**Problem:** Unexpected validation results or missing error detection.

**Solutions:**

1. **Test validation rules:**
   ```python
   rules = await schema_collector.get_validation_rules("program-id", "core-id")

   for field, field_rules in rules.items():
       print(f"Field '{field}' rules: {field_rules}")

       # Test specific values
       test_value = "test_value"

       # Required field check
       if field_rules.get("required") and not test_value:
           print(f"  REQUIRED_VALUE error for empty value")

       # Valid options check
       if "valid_options" in field_rules:
           if test_value not in field_rules["valid_options"]:
               print(f"  INVALID_OPTION error for '{test_value}'")

       # Pattern check
       if "pattern" in field_rules:
           import re
           if not re.match(field_rules["pattern"], test_value):
               print(f"  INVALID_PATTERN error for '{test_value}'")
   ```

2. **Debug validation node:**
   ```python
   from metadata_harmonization_processor.nodes.validation import ValidationNode

   validation_node = ValidationNode(schema_collector)

   # Test with aligned DataFrame
   state = ProcessorState(
       aligned_df=aligned_df,
       program_id="test-program",
       core_id="test-core"
   )

   validated_state = await validation_node(state)
   results = validated_state.validation_results

   print(f"Validation errors: {len(results.validation_results)}")
   for error in results.validation_results:
       print(f"  Row {error.row}, Column '{error.column}': {error.error_type}")
   ```

### AWS Strands Graph Execution Errors

**Problem:** `ProcessingError: Graph execution failed` with node-specific error details.

**Solutions:**

1. **Check individual node failures:**
   ```python
   try:
       results = await processor.process(metadata_df, program_id, core_id)
   except ProcessingError as e:
       if "Graph execution failed" in str(e):
           print(f"Graph execution error: {e}")

           # Check processor state for debugging
           state = processor.get_current_state()
           if state:
               print(f"Current stage: {state.current_stage}")
               print(f"Has metadata: {state.has_metadata()}")
               print(f"Has aligned data: {state.has_aligned_data()}")
               print(f"Has validation results: {state.has_validation_results()}")
   ```

2. **Debug specific processing nodes:**
   ```python
   # Test schema alignment separately
   from metadata_harmonization_processor.nodes.schema_alignment import SchemaAlignmentNode

   alignment_node = SchemaAlignmentNode(schema_collector)
   test_state = ProcessorState(metadata_df=df, program_id=program_id, core_id=core_id)

   try:
       result = await alignment_node.invoke_async(
           task="schema_alignment_task",
           invocation_state={"processor_state": test_state}
       )
       print(f"Schema alignment status: {result.status}")
   except Exception as e:
       print(f"Schema alignment failed: {e}")
   ```

3. **Validate processing results:**
   ```python
   # Ensure validation results are generated
   if not processor.get_current_state().has_validation_results():
       print("ERROR: No validation results generated")
       # Check if validation node completed successfully
       # Review schema definitions and input data format
   ```

### Prediction Issues

**Problem:** AI predictions not working or returning poor recommendations.

**Solutions:**

1. **Check AI service configuration:**
   ```python
   # Test Bedrock connectivity
   import boto3

   bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

   try:
       response = bedrock.invoke_model(
           modelId='amazon.titan-embed-text-v1',
           body=json.dumps({'inputText': 'test'})
       )
       print("Bedrock accessible")
   except Exception as e:
       print(f"Bedrock error: {e}")
   ```

2. **Test semantic search node:**
   ```python
   from metadata_harmonization_processor.nodes.semantic_prediction import SemanticSearchPredictionNode

   config = ProcessorConfig(
       embedding_provider="bedrock",
       bedrock_model_id="amazon.titan-embed-text-v1",
       cosine_similarity_threshold=0.7
   )

   semantic_node = SemanticSearchPredictionNode(config)

   try:
       # Test with validation results containing INVALID_OPTION errors using MultiAgentBase framework
       result = await semantic_node.invoke_async(state_with_validation_results)

       if result.status.name == 'COMPLETED':
           enhanced_state = result.results["semantic_prediction"].result
           # Check for recommendations
           recommendations = [
               error for error in enhanced_state.validation_results.validation_results
               if error.recommended_value
           ]
           print(f"Generated {len(recommendations)} recommendations")

   finally:
       await semantic_node.close()
   ```

3. **Adjust similarity threshold:**
   ```yaml
   # Lower threshold for more recommendations (less strict)
   cosine_similarity_threshold: 0.6

   # Higher threshold for fewer, higher-quality recommendations
   cosine_similarity_threshold: 0.9
   ```

## Performance Issues

### Slow Processing

**Problem:** Processing takes too long or times out.

**Solutions:**

1. **Enable caching:**
   ```yaml
   enable_redis_cache: true
   redis_endpoint: "your-redis-endpoint"
   enable_memory_cache: true
   memory_cache_max_size: 10000
   ```

2. **Optimize DataFrame size:**
   ```python
   # Process in chunks for large datasets
   chunk_size = 1000

   for i in range(0, len(large_df), chunk_size):
       chunk = large_df.iloc[i:i+chunk_size]
       processor.reset_state()
       results = await processor.process(chunk)
       # Process results...
   ```

3. **Increase timeouts:**
   ```yaml
   timeout_seconds: 900  # 15 minutes
   max_retries: 5
   ```

4. **Monitor resource usage:**
   ```python
   import psutil
   import time

   start_time = time.time()
   start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

   results = await processor.process(df, program_id="program-id", core_id="core-id")

   end_time = time.time()
   end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

   print(f"Processing time: {end_time - start_time:.2f} seconds")
   print(f"Memory usage: {end_memory - start_memory:.2f} MB")
   ```

### Memory Issues

**Problem:** `MemoryError` or excessive memory usage.

**Solutions:**

1. **Reduce memory cache size:**
   ```yaml
   memory_cache_max_size: 1000  # Reduce from default 10000
   ```

2. **Use Redis instead of memory cache:**
   ```yaml
   enable_redis_cache: true
   enable_memory_cache: false
   ```

3. **Process smaller chunks:**
   ```python
   # Split large DataFrames
   def chunk_dataframe(df, chunk_size=500):
       for i in range(0, len(df), chunk_size):
           yield df.iloc[i:i+chunk_size]

   all_results = []
   for chunk in chunk_dataframe(large_df):
       processor.reset_state()
       results = await processor.process(chunk)
       all_results.append(results)
   ```

## Debugging Tips

### Enable Debug Logging

```python
import logging

# Enable debug logging for the processor
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
logging.getLogger('metadata_harmonization_processor').setLevel(logging.DEBUG)
logging.getLogger('boto3').setLevel(logging.INFO)  # Reduce AWS SDK noise
logging.getLogger('botocore').setLevel(logging.INFO)
```

### Inspect Processing State

```python
# Get detailed state information
state = processor.get_current_state()

if state:
    print(f"Job ID: {state.job_id}")
    print(f"Current stage: {state.current_stage}")
    print(f"Processing duration: {state.get_processing_duration():.2f}s")

    if state.metadata_df is not None:
        print(f"Input DataFrame shape: {state.metadata_df.shape}")

    if state.aligned_df is not None:
        print(f"Aligned DataFrame shape: {state.aligned_df.shape}")
        print(f"Aligned columns: {list(state.aligned_df.columns)}")

    if state.validation_results is not None:
        print(f"Validation errors: {state.validation_results.summary.total_errors}")
```

### Test Individual Components

```python
# Test schema collector independently
schema_collector = FileBasedSchemaCollector("./data/schema")

try:
    schemas = await schema_collector.get_available_schemas()
    print(f"Available schemas: {len(schemas)}")

    if schemas:
        first_schema = schemas[0]
        schema_def = await schema_collector.get_schema(
            first_schema.program_uuid,
            first_schema.core_uuid
        )
        print(f"Schema definition keys: {list(schema_def.keys())}")

except Exception as e:
    print(f"Schema collector error: {e}")
    import traceback
    traceback.print_exc()

# Test job status saver independently
job_saver = DynamodbJobStatusSaver("test-table")

try:
    await job_saver.save_status("test-job", "testing", {"test": True})
    status = await job_saver.get_status("test-job")
    print(f"Job status: {status}")

except Exception as e:
    print(f"Job saver error: {e}")
    import traceback
    traceback.print_exc()
```

### Common Error Patterns

1. **Configuration errors** usually occur during processor initialization
2. **Schema errors** occur during `set_schema_ids()` or early in processing
3. **AWS service errors** occur during processing stages that use external services
4. **Processing errors** occur during DataFrame manipulation or validation

### Getting Help

If you continue to experience issues:

1. **Check the logs** for detailed error messages and stack traces
2. **Verify your configuration** against the examples in this repository
3. **Test individual components** to isolate the problem
4. **Create a minimal reproduction case** with sample data
5. **Check AWS service status** if using cloud services

For additional support, please refer to the project documentation or create an issue with:
- Your configuration file (with sensitive data removed)
- Complete error messages and stack traces
- Sample data that reproduces the issue
- Environment information (Python version, OS, etc.)
