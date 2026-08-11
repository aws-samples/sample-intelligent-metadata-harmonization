# Usage Guide

This guide provides comprehensive instructions for using the MetadataHarmonizationProcessor package in various scenarios, from basic usage to advanced production deployments.

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Usage Patterns](#basic-usage-patterns)
- [Advanced Features](#advanced-features)
- [Production Deployment](#production-deployment)
- [Custom Implementations](#custom-implementations)
- [Performance Optimization](#performance-optimization)
- [Best Practices](#best-practices)

## Quick Start

### 1. Basic Setup

For a complete working example, see [`examples/basic_usage.py`](../examples/basic_usage.py) which demonstrates the full pipeline with real Cyclospora metadata.

```python
import asyncio
import pandas as pd
from pathlib import Path
from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import load_processor_settings

async def quick_start():
    # Load configuration first (contains all component settings)
    config = load_processor_settings(config_path=Path("config.yaml"))

    # Create processor with configuration-driven approach
    # All components (JobStatusSaver, ResultSaver, SchemaCollector) created from config
    session_id = f"quick-start-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        # Load CSV with schema-aware dtype mapping (recommended)
        # This preserves datatypes like "FALSE"/"TRUE" as strings
        df = await processor.load_csv(
            "../../data/Realistic Cyclospora Metadata 1.csv",
            program_id="program-id",
            core_id="core-id"
        )

        # Process the data
        results = await processor.process(df, program_id="program-id", core_id="core-id")

        # Use results
        print(f"Found {results.summary.total_errors} validation errors")

    finally:
        await processor.cleanup()

# Run the example
asyncio.run(quick_start())
```

### 2. Minimal Configuration

Create `config.yaml`:

```yaml
aws_region: "us-east-1"
schema_directory: "./data/schema"
session_saver_type: "file"
enable_redis_cache: false
enable_memory_cache: true
embedding_provider: "bedrock"
bedrock_model_id: "amazon.titan-embed-text-v1"

# Data Storage Configuration
job_status_saver_type: "local"
job_status_storage_dir: "./job_status"
result_saver_type: "local"
results_local_dir: "./validation-results"
```

## Basic Usage Patterns

### 1. Processing Single DataFrame

```python
async def process_single_dataframe():
    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"single-df-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        # Load and process data
        # Recommended: Use schema-aware loading
        df = await processor.load_csv("patient_data.csv", program_id, core_id)

        # Alternative: Load manually (may cause type conversion issues)
        # df = pd.read_csv("patient_data.csv")
        results = await processor.process(df, program_id="flu-program", core_id="patient-core")

        # Handle results
        if results.summary.total_errors > 0:
            print("Validation errors found:")
            for error in results.validation_results:
                print(f"  Row {error.row}, Column '{error.column}': {error.error_type}")
                if error.recommended_value:
                    print(f"    Recommended: '{error.recommended_value}'")
        else:
            print("No validation errors found!")

    finally:
        await processor.cleanup()
```

### 2. Batch Processing Multiple Files

```python
async def process_multiple_files():
    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"multi-files-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        files = ["data1.csv", "data2.csv", "data3.csv"]
        all_results = []

        for file_path in files:
            print(f"Processing {file_path}...")

            # Reset state for each file
            processor.reset_state()

            # Process file
            df = pd.read_csv(file_path)
            results = await processor.process(df, program_id="program-id", core_id="core-id")
            all_results.append(results)

            print(f"  Errors: {results.summary.total_errors}")

        # Aggregate results
        total_errors = sum(r.summary.total_errors for r in all_results)
        total_rows = sum(r.summary.total_rows for r in all_results)

        print(f"Batch processing complete:")
        print(f"  Files processed: {len(files)}")
        print(f"  Total rows: {total_rows}")
        print(f"  Total errors: {total_errors}")

    finally:
        await processor.cleanup()
```

### 3. Processing Large Datasets in Chunks

```python
async def process_large_dataset():
    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"large-dataset-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        chunk_size = 1000
        all_results = []

        # Process file in chunks
        for chunk_df in pd.read_csv("large_dataset.csv", chunksize=chunk_size):
            print(f"Processing chunk of {len(chunk_df)} rows...")

            # Reset state for each chunk
            processor.reset_state()

            # Process chunk
            results = await processor.process(chunk_df, program_id="program-id", core_id="core-id")
            all_results.append(results)

            # Optional: Save intermediate results
            with open(f"results_chunk_{len(all_results)}.json", "w") as f:
                json.dump(results.model_dump(), f, indent=2)

        print(f"Processed {len(all_results)} chunks")

    finally:
        await processor.cleanup()
```

## Advanced Features

### 1. Configuration Overrides

```python
# Override configuration at runtime
config_overrides = {
    "enable_redis_cache": False,
    "cosine_similarity_threshold": 0.9,
    "max_retries": 5,
    "timeout_seconds": 600
}

# Load configuration with overrides
config = load_processor_settings(
    config_path=Path("config.yaml"),
    override=config_overrides
)

session_id = f"config-override-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
processor = MetadataHarmonizationProcessor(
    config=config,
    session_id=session_id
)
```

### 2. Progress Monitoring

```python
async def monitor_processing():
    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"monitoring-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        # Start processing
        df = pd.read_csv("data.csv")

        # Monitor progress (in a separate task if needed)
        async def monitor():
            while True:
                state = processor.get_current_state()
                if state:
                    duration = state.get_processing_duration()
                    print(f"Job ID: {state.job_id}, Duration: {duration:.2f}s")

                await asyncio.sleep(1)

                # Break when processing is complete
                if state and hasattr(state, 'current_stage') and state.current_stage == "completed":
                    break

        # Run processing and monitoring concurrently
        results, _ = await asyncio.gather(
            processor.process(df, program_id="program-id", core_id="core-id"),
            monitor()
        )

        print(f"Processing completed with {results.summary.total_errors} errors")

    finally:
        await processor.cleanup()
```

### 3. Error Handling and Recovery

```python
async def robust_processing():
    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"robust-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        df = pd.read_csv("data.csv")

        # Attempt processing with retry logic
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                results = await processor.process(df, program_id="program-id", core_id="core-id")
                print("Processing successful!")
                break

            except ExternalServiceError as e:
                print(f"Attempt {attempt + 1} failed due to external service: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    processor.reset_state()  # Reset for retry
                else:
                    print("All attempts failed")
                    raise

            except ProcessingError as e:
                print(f"Processing error (not retryable): {e}")
                break

    finally:
        await processor.cleanup()
```

### 4. Custom Validation Logic

```python
async def custom_validation_workflow():
    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"custom-validation-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        df = pd.read_csv("data.csv")

        # Pre-processing validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        if len(df) > 10000:
            print("Large dataset detected, consider chunking")

        # Process with the pipeline
        results = await processor.process(df, program_id="program-id", core_id="core-id")

        # Post-processing analysis
        error_rate = results.summary.total_errors / results.summary.total_rows

        if error_rate > 0.5:
            print(f"High error rate detected: {error_rate:.1%}")
            print("Consider reviewing data quality or schema definitions")

        # Filter high-confidence recommendations
        high_confidence_recommendations = [
            error for error in results.validation_results
            if error.recommended_value and error.error_type == "INVALID_OPTION"
        ]

        print(f"High-confidence recommendations: {len(high_confidence_recommendations)}")

    finally:
        await processor.cleanup()
```

## Production Deployment

### 1. Production Configuration

```yaml
# production-config.yaml
aws_region: "us-west-2"
session_saver_type: "s3"

# Production mode (disable local development features)
local_development_mode: false

# Data Saver Configuration
# Job Status Saver - DynamoDB for production
job_status_saver_type: "dynamodb"
job_status_table_name: "metadata-harmonization-jobs-prod"

# Result Saver - S3 for production
result_saver_type: "s3"
results_s3_bucket: "metadata-results-prod"
results_s3_prefix: "validation-results/"

# Redis configuration for production
enable_redis_cache: true
redis_endpoint: "metadata-cache.abc123.cache.amazonaws.com"
redis_port: 6379

# Memory cache as fallback
enable_memory_cache: true
memory_cache_max_size: 5000

# AI configuration
embedding_provider: "bedrock"
bedrock_model_id: "amazon.titan-embed-text-v1"
cosine_similarity_threshold: 0.8

# Production timeouts and retries
max_retries: 5
timeout_seconds: 900

# Schema configuration
schema_directory: "/opt/metadata-processor/schemas"
```

### 2. Production Deployment Pattern

```python
import logging
import os
from pathlib import Path

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/metadata-processor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ProductionMetadataProcessor:
    """Production-ready wrapper for MetadataHarmonizationProcessor."""

    def __init__(self):
        self.processor = None
        self.config_path = os.getenv('METADATA_PROCESSOR_CONFIG', '/etc/metadata-processor/config.yaml')

    async def initialize(self):
        """Initialize processor with production settings."""
        logger.info("Initializing production metadata processor...")

        # Load configuration first
        config = load_processor_settings(config_path=Path(self.config_path))

        # Create processor with configuration-driven approach
        session_id = f"production-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
        self.processor = MetadataHarmonizationProcessor(
            config=config,
            session_id=session_id
        )

        logger.info("Production processor initialized successfully")

    async def process_with_monitoring(self, df, program_id, core_id):
        """Process with comprehensive monitoring and error handling."""
        start_time = time.time()

        try:
            logger.info(f"Starting processing: {len(df)} rows, program={program_id}, core={core_id}")

            results = await self.processor.process(df, program_id=program_id, core_id=core_id)

            # Log metrics
            duration = time.time() - start_time
            error_rate = results.summary.total_errors / results.summary.total_rows

            logger.info(f"Processing completed in {duration:.2f}s")
            logger.info(f"Error rate: {error_rate:.1%} ({results.summary.total_errors}/{results.summary.total_rows})")

            # Alert on high error rates
            if error_rate > 0.3:
                logger.warning(f"High error rate detected: {error_rate:.1%}")

            return results

        except Exception as e:
            logger.error(f"Processing failed after {time.time() - start_time:.2f}s: {e}")
            raise

    async def cleanup(self):
        """Clean up resources."""
        if self.processor:
            await self.processor.cleanup()
            logger.info("Production processor cleaned up")

# Usage in production
async def production_main():
    prod_processor = ProductionMetadataProcessor()

    try:
        await prod_processor.initialize()

        # Process data
        df = pd.read_csv(sys.argv[1])  # Input file from command line
        program_id = sys.argv[2]
        core_id = sys.argv[3]

        results = await prod_processor.process_with_monitoring(df, program_id, core_id)

        # Save results
        output_file = sys.argv[4] if len(sys.argv) > 4 else "results.json"
        with open(output_file, 'w') as f:
            json.dump(results.model_dump(), f, indent=2)

        logger.info(f"Results saved to {output_file}")

    finally:
        await prod_processor.cleanup()

if __name__ == "__main__":
    asyncio.run(production_main())
```

### 3. Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY pyproject.toml ./
RUN pip install -e .

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY schemas/ ./schemas/

# Create non-root user
RUN useradd -m -u 1000 processor
USER processor

# Set environment variables
ENV PYTHONPATH=/app/src
ENV METADATA_PROCESSOR_CONFIG=/app/config/production.yaml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import metadata_harmonization_processor; print('OK')"

# Run application
CMD ["python", "-m", "metadata_harmonization_processor.cli"]
```

## Custom Implementations

### 1. Configuration-Driven Component Creation

The processor now creates all components from configuration, eliminating manual setup:

```python
# Local development with configuration-driven approach
async def local_development_example():
    # Load configuration with local development settings
    config = load_processor_settings(config_path=Path("config-local.yaml"))

    # Processor creates LocalJobStatusSaver and LocalResultSaver from config
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        # Process data - all components created automatically from config
        results = await processor.process(df, program_id="program-id", core_id="core-id")

        # Job status and results are automatically saved locally
        print(f"Job completed with {results.summary.total_errors} errors")

    finally:
        await processor.cleanup()
```

**Local Development Configuration:**
```yaml
# config-local.yaml
job_status_saver_type: "local"
job_status_storage_dir: "./job_status"  # File-based persistence
result_saver_type: "local"
results_local_dir: "./validation-results"
schema_directory: "./data/schema"
session_saver_type: "file"
enable_redis_cache: false
```

### 2. Production Configuration

The processor creates production-ready components from configuration:

```python
# Production configuration automatically creates DynamoDB and S3 savers

# Use with processor (configured via ProcessorConfig)
async def local_development_with_results():
    # Configuration includes LocalResultSaver settings
    config = load_processor_settings(config_path=Path("config-local.yaml"))

    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        # Process data - results are automatically saved locally
        results = await processor.process(df, program_id="program-id", core_id="core-id")

        # Results are saved to: ./validation-results/{job_id}/v{version}/results.json
        print(f"Results saved locally with {results.summary.total_errors} errors")

        # Manually save additional results if needed (with dual result instances)
        job_results = await result_saver.save_results(
            job_id="manual-job-123",
            version=1,
            validation_results=results,
            schema_alignment_results=processor.get_current_state().schema_alignment_results,  # Optional
            metadata={"custom_field": "value"}
        )

        # Retrieve combined results later
        validation_results, schema_alignment_results = await result_saver.get_results(job_results)

        # List all versions for a job
        all_versions = await result_saver.list_results("manual-job-123")
        print(f"Found {len(all_versions)} result versions")

    finally:
        await processor.cleanup()
```

**Local Development Configuration:**
```yaml
# config-local.yaml
result_saver_type: "local"
results_local_dir: "./validation-results"  # Organized as {job_id}/v{version}/results.json
```

### 3. Custom JobStatusSaver Implementation

For advanced use cases, you can create custom implementations:

```python
import aiofiles
import json
from pathlib import Path
from typing import Dict, Any, Optional

class CustomFileJobStatusSaver(JobStatusSaver):
    """Custom file-based JobStatusSaver with additional features."""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save_status(self, job_id: str, status: str, metadata: Dict[str, Any]) -> None:
        """Save job status to JSON file."""
        status_data = {
            "job_id": job_id,
            "status": status,
            "metadata": metadata,
            "updated_at": datetime.now().isoformat()
        }

        file_path = self.storage_dir / f"{job_id}.json"
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(json.dumps(status_data, indent=2))

    async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job status from JSON file."""
        file_path = self.storage_dir / f"{job_id}.json"

        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            return json.loads(content)

    async def update_progress(self, job_id: str, stage: str, progress: float) -> None:
        """Update job progress in metadata."""
        status_data = await self.get_status(job_id)
        if status_data:
            if "progress" not in status_data["metadata"]:
                status_data["metadata"]["progress"] = {}

            status_data["metadata"]["progress"][stage] = progress
            status_data["updated_at"] = datetime.now().isoformat()

            await self.save_status(job_id, status_data["status"], status_data["metadata"])
```

### 3. Custom SchemaCollector

```python
import httpx
from typing import List, Dict, Any

class APISchemaCollector(SchemaCollector):
    """API-based SchemaCollector for remote schema services."""

    def __init__(self, api_base_url: str, api_key: Optional[str] = None):
        self.api_base_url = api_base_url.rstrip('/')
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        self._client = None

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(headers=self.headers)
        return self._client

    async def get_available_schemas(self) -> List[SchemaInfo]:
        """Get available schemas from API."""
        client = await self._get_client()

        response = await client.get(f"{self.api_base_url}/schemas")
        response.raise_for_status()

        schemas_data = response.json()
        return [SchemaInfo(**schema) for schema in schemas_data]

    async def get_schema(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """Get combined schema from API."""
        client = await self._get_client()

        # Fetch core and program schemas
        core_response = await client.get(f"{self.api_base_url}/schemas/core/{core_id}")
        program_response = await client.get(f"{self.api_base_url}/schemas/program/{program_id}")

        core_response.raise_for_status()
        program_response.raise_for_status()

        core_schema = core_response.json()
        program_schema = program_response.json()

        # Combine schemas
        combined_schema = {
            "type": "object",
            "properties": {
                **core_schema.get("properties", {}),
                **program_schema.get("properties", {})
            }
        }

        return combined_schema

    async def cleanup(self):
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
```

## Performance Optimization

### 1. Caching Strategies

```python
# Optimize caching configuration
config_overrides = {
    # Use Redis for production
    "enable_redis_cache": True,
    "redis_endpoint": "your-redis-endpoint",

    # Tune memory cache for your workload
    "enable_memory_cache": True,
    "memory_cache_max_size": 10000,  # Adjust based on available memory

    # Optimize similarity threshold
    "cosine_similarity_threshold": 0.8,  # Higher = fewer but better recommendations
}
```

### 2. Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def parallel_processing():
    """Process multiple datasets in parallel."""

    # Create multiple processor instances
    processors = []
    for i in range(3):  # Adjust based on resources
        # Load configuration first
        config = load_processor_settings(config_path=Path("config.yaml"))

        session_id = f"parallel-{i}-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
        processor = MetadataHarmonizationProcessor(
            config=config,
            session_id=session_id
        )
        processors.append(processor)

    try:
        # Prepare datasets
        datasets = [
            pd.read_csv(f"data_{i}.csv")
            for i in range(len(processors))
        ]

        # Process in parallel
        tasks = []
        for processor, df in zip(processors, datasets):
            tasks.append(processor.process(df, program_id="program-id", core_id="core-id"))

        results = await asyncio.gather(*tasks)

        print(f"Processed {len(results)} datasets in parallel")

    finally:
        # Clean up all processors
        await asyncio.gather(*[p.cleanup() for p in processors])
```

### 3. Memory Management

```python
async def memory_efficient_processing():
    """Process large datasets with memory management."""

    # Load configuration first
    config = load_processor_settings(config_path=Path("config.yaml"))

    session_id = f"memory-efficient-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
    processor = MetadataHarmonizationProcessor(
        config=config,
        session_id=session_id
    )

    try:
        # Process file in chunks to manage memory
        chunk_size = 1000
        results_summary = {
            "total_rows": 0,
            "total_errors": 0,
            "error_types": {}
        }

        for chunk_df in pd.read_csv("large_file.csv", chunksize=chunk_size):
            # Reset processor state for each chunk
            processor.reset_state()

            # Process chunk
            results = await processor.process(chunk_df, program_id="program-id", core_id="core-id")

            # Aggregate results
            results_summary["total_rows"] += results.summary.total_rows
            results_summary["total_errors"] += results.summary.total_errors

            for error_type, count in results.summary.error_types.items():
                results_summary["error_types"][error_type] = (
                    results_summary["error_types"].get(error_type, 0) + count
                )

            # Force garbage collection for large datasets
            import gc
            gc.collect()

        print(f"Memory-efficient processing complete: {results_summary}")

    finally:
        await processor.cleanup()
```

## Best Practices

### 1. Configuration Management

```python
# Use environment-specific configurations
def get_config_path():
    env = os.getenv('ENVIRONMENT', 'development')
    return Path(f"config-{env}.yaml")

# Load configuration with validation
def load_validated_config():
    config_path = get_config_path()

    try:
        config = load_processor_settings(config_path=config_path)

        # Validate critical settings
        if not config.schema_directory:
            raise ValueError("schema_directory is required")

        if config.enable_redis_cache and not config.redis_endpoint:
            raise ValueError("redis_endpoint required when Redis caching is enabled")

        # Validate data saver configuration
        if config.job_status_saver_type == "dynamodb" and not config.job_status_table_name:
            raise ValueError("job_status_table_name required when job_status_saver_type is 'dynamodb'")
        elif config.job_status_saver_type == "local" and not config.job_status_storage_dir:
            raise ValueError("job_status_storage_dir required when job_status_saver_type is 'local'")

        if config.result_saver_type == "s3" and not config.results_s3_bucket:
            raise ValueError("results_s3_bucket required when result_saver_type is 's3'")
        elif config.result_saver_type == "local" and not config.results_local_dir:
            raise ValueError("results_local_dir required when result_saver_type is 'local'")

        return config

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
```

### 2. Error Handling

```python
from metadata_harmonization_processor.exceptions import (
    ConfigurationError, SchemaError, ProcessingError, ExternalServiceError
)

async def robust_error_handling():
    try:
        results = await processor.process(df, program_id="program-id", core_id="core-id")

    except ConfigurationError as e:
        logger.error(f"Configuration issue: {e}")
        # Fix configuration and retry

    except SchemaError as e:
        logger.error(f"Schema issue: {e}")
        # Check schema files and IDs

    except ProcessingError as e:
        logger.error(f"Processing issue: {e}")
        # Check data format and content

    except ExternalServiceError as e:
        logger.warning(f"External service issue: {e}")
        # Graceful degradation - some features may not work

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # General error handling
```

### 3. Monitoring and Logging

```python
import time
import psutil

async def monitored_processing():
    # Set up monitoring
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024

    logger.info(f"Starting processing: {len(df)} rows")

    try:
        results = await processor.process(df, program_id="program-id", core_id="core-id")

        # Log success metrics
        duration = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_used = end_memory - start_memory

        logger.info(f"Processing successful:")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info(f"  Memory used: {memory_used:.1f}MB")
        logger.info(f"  Rows/second: {len(df)/duration:.1f}")
        logger.info(f"  Error rate: {results.summary.total_errors/results.summary.total_rows:.1%}")

        return results

    except Exception as e:
        # Log failure metrics
        duration = time.time() - start_time
        logger.error(f"Processing failed after {duration:.2f}s: {e}")
        raise
```

### 4. Testing and Validation

```python
async def validate_processing_results(results: ValidationResults):
    """Validate processing results for quality assurance."""

    # Check result structure
    assert results.summary.total_rows > 0, "No rows processed"
    assert len(results.validation_results) == results.summary.total_errors, "Inconsistent error count"

    # Validate error types
    valid_error_types = {"REQUIRED_VALUE", "INVALID_OPTION", "INVALID_PATTERN"}
    for error in results.validation_results:
        assert error.error_type in valid_error_types, f"Invalid error type: {error.error_type}"
        assert error.row >= 0, "Invalid row number"
        assert error.column, "Missing column name"

    # Check recommendation quality
    recommendations = [e for e in results.validation_results if e.recommended_value]
    recommendation_rate = len(recommendations) / len(results.validation_results) if results.validation_results else 0

    logger.info(f"Recommendation rate: {recommendation_rate:.1%}")

    if recommendation_rate < 0.5:
        logger.warning("Low recommendation rate - check AI service configuration")

    return True
```

This comprehensive usage guide covers all major aspects of using the MetadataHarmonizationProcessor package, from basic usage to advanced production deployments. Users can refer to specific sections based on their needs and experience level.
