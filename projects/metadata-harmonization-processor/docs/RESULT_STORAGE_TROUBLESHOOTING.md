# Result Storage Troubleshooting Guide

This guide helps resolve common issues with result storage configuration and operations in the MetadataHarmonizationProcessor.

## Configuration Issues

### LocalResultSaver Configuration

#### Problem: Results not being saved locally

**Symptoms:**
- No files created in `results_local_dir`
- Processing completes but no result files found
- Permission errors during file creation

**Solutions:**

1. **Check directory permissions:**
```bash
# Ensure the directory is writable
ls -la ./validation-results/
chmod 755 ./validation-results/
```

2. **Verify configuration:**
```yaml
# config-local.yaml
result_saver_type: "local"
results_local_dir: "./validation-results"  # Must be writable path
```

3. **Use absolute paths if relative paths fail:**
```yaml
results_local_dir: "/home/user/metadata-processor/results"
```

#### Problem: "Directory not found" errors

**Solution:**
LocalResultSaver automatically creates directories, but parent directories must exist:

```bash
# Create parent directory if needed
mkdir -p /path/to/parent/directory
```

### S3ResultSaver Configuration

#### Problem: S3 access denied errors

**Symptoms:**
- `ClientError: An error occurred (AccessDenied)`
- `NoCredentialsError: Unable to locate credentials`
- `BucketNotFound` errors

**Solutions:**

1. **Verify AWS credentials:**
```bash
# Check AWS CLI configuration
aws configure list
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://your-bucket-name/
```

2. **Check IAM permissions:**
Required S3 permissions for the processor:
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
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

3. **Verify bucket configuration:**
```yaml
# config-s3.yaml
result_saver_type: "s3"
results_s3_bucket: "existing-bucket-name"  # Must exist
results_s3_prefix: "validation-results/"   # Optional prefix
aws_region: "us-east-1"                    # Must match bucket region
```

#### Problem: Multipart upload failures

**Symptoms:**
- Large files fail to upload
- `UploadPartError` in logs
- Incomplete multipart uploads in S3

**Solutions:**

1. **Check file size and multipart settings:**
```yaml
# Adjust multipart thresholds in config
s3_multipart_threshold: 104857600  # 100MB (default)
s3_multipart_chunksize: 8388608    # 8MB chunks
s3_max_concurrency: 10             # Concurrent uploads
```

2. **Monitor S3 incomplete multipart uploads:**
```bash
# List incomplete uploads
aws s3api list-multipart-uploads --bucket your-bucket-name

# Clean up incomplete uploads if needed
aws s3api abort-multipart-upload --bucket your-bucket-name --key your-key --upload-id upload-id
```

## Runtime Issues

### Result Retrieval Problems

#### Problem: `list_results()` returns empty list

**Possible Causes:**
1. **Wrong job ID:** Verify the job ID is correct
2. **Storage backend mismatch:** Check if results were saved with different saver type
3. **Path/bucket issues:** Verify storage location exists

**Debugging Steps:**

1. **For LocalResultSaver:**
```bash
# Check if result files exist
ls -la ./validation-results/
find ./validation-results/ -name "*.json" -type f
```

2. **For S3ResultSaver:**
```bash
# List S3 objects with prefix
aws s3 ls s3://your-bucket/your-prefix/ --recursive
```

3. **Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed storage operations
```

#### Problem: `get_results()` returns None

**Possible Causes:**
1. **File corruption:** JSON file is malformed
2. **Permission issues:** Cannot read the file
3. **S3 object deleted:** Object no longer exists in S3

**Solutions:**

1. **Validate JSON files:**
```bash
# Check JSON syntax
python -m json.tool ./validation-results/job-123/v1/results.json
```

2. **Check file permissions:**
```bash
# Ensure files are readable
chmod 644 ./validation-results/job-123/v1/results.json
```

3. **Verify S3 object exists:**
```bash
aws s3 head-object --bucket your-bucket --key your-prefix/job-123/v1/results.json
```

### Performance Issues

#### Problem: Slow result saving/retrieval

**For LocalResultSaver:**
1. **Use SSD storage** for better I/O performance
2. **Avoid network-mounted directories** (NFS, SMB)
3. **Check disk space:** Ensure sufficient free space

**For S3ResultSaver:**
1. **Optimize multipart settings:**
```yaml
s3_multipart_threshold: 52428800   # 50MB for faster small files
s3_multipart_chunksize: 16777216   # 16MB chunks for better throughput
s3_max_concurrency: 20             # More concurrent uploads
```

2. **Use appropriate S3 storage class:**
```python
# Configure S3 storage class in processor config
s3_storage_class: "STANDARD"  # or "STANDARD_IA" for infrequent access
```

3. **Consider S3 Transfer Acceleration** for cross-region uploads

## Version Management Issues

#### Problem: Version conflicts or overwrites

**Symptoms:**
- Results being overwritten unexpectedly
- Version numbers not incrementing
- Missing result versions

**Solutions:**

1. **Check version tracking logic:**
```python
# Manually specify version if needed
job_results = await result_saver.save_results(
    job_id="job-123",
    version=2,  # Explicit version
    results=validation_results
)
```

2. **Verify job ID uniqueness:**
```python
# Use timestamp-based job IDs for uniqueness
import uuid
job_id = f"job-{uuid.uuid4()}"
```

## Configuration Validation

### Validate Configuration Before Use

```python
from metadata_harmonization_processor.config import load_processor_settings
from pathlib import Path

try:
    config = load_processor_settings(config_path=Path("config.yaml"))

    # Validate result saver configuration
    if config.result_saver_type == "s3":
        if not config.results_s3_bucket:
            raise ValueError("results_s3_bucket is required for S3 result saver")
    elif config.result_saver_type == "local":
        if not config.results_local_dir:
            raise ValueError("results_local_dir is required for local result saver")

    print("✓ Configuration is valid")

except Exception as e:
    print(f"✗ Configuration error: {e}")
```

### Test Storage Backend Connectivity

```python
async def test_storage_backend(processor):
    """Test if storage backend is accessible."""
    try:
        # Create test data
        test_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(
                total_rows=0,
                total_errors=0,
                error_types={}
            )
        )

        # Test save operation
        result_saver = processor.data_saver.result_saver
        job_results = await result_saver.save_results(
            job_id="test-connectivity",
            version=1,
            results=test_results
        )

        # Test retrieval
        retrieved = await result_saver.get_results(job_results)

        if retrieved:
            print("✓ Storage backend connectivity test passed")
            return True
        else:
            print("✗ Storage backend retrieval test failed")
            return False

    except Exception as e:
        print(f"✗ Storage backend connectivity test failed: {e}")
        return False
```

## Common Error Messages

### LocalResultSaver Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `PermissionError: [Errno 13] Permission denied` | Directory not writable | `chmod 755 directory` |
| `FileNotFoundError: [Errno 2] No such file or directory` | Parent directory missing | `mkdir -p parent/directory` |
| `JSONDecodeError: Expecting value` | Corrupted JSON file | Delete and regenerate results |
| `OSError: [Errno 28] No space left on device` | Disk full | Free up disk space |

### S3ResultSaver Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `NoCredentialsError` | AWS credentials not configured | Configure AWS CLI or IAM roles |
| `ClientError: AccessDenied` | Insufficient S3 permissions | Update IAM policy |
| `ClientError: NoSuchBucket` | S3 bucket doesn't exist | Create bucket or fix bucket name |
| `ClientError: InvalidBucketName` | Invalid bucket name format | Use valid S3 bucket naming |
| `EndpointConnectionError` | Network connectivity issues | Check internet connection and AWS region |

## Best Practices

### Local Development
1. **Use relative paths** for portability: `./validation-results`
2. **Include results directory in .gitignore** to avoid committing large files
3. **Regularly clean up old results** to save disk space
4. **Use descriptive job IDs** for easier debugging

### Production S3 Setup
1. **Use dedicated S3 buckets** for result storage
2. **Configure S3 lifecycle policies** to manage storage costs
3. **Enable S3 versioning** for additional data protection
4. **Use S3 bucket notifications** for downstream processing
5. **Monitor S3 costs** and optimize storage classes

### General
1. **Always handle storage errors gracefully** in your application
2. **Implement retry logic** for transient failures
3. **Log storage operations** for debugging
4. **Test storage backends** before production deployment
5. **Monitor storage usage** and performance metrics

## Integration Testing

The package includes comprehensive integration tests that validate result storage functionality:

### Running Storage Integration Tests

```bash
# Test S3ResultSaver integration
pytest tests/integration/test_end_to_end_pipeline.py::TestEndToEndPipeline::test_result_storage_s3_integration -v

# Test LocalResultSaver integration
pytest tests/integration/test_end_to_end_pipeline.py::TestEndToEndPipeline::test_result_storage_local_integration -v

# Test error scenarios and recovery
pytest tests/integration/test_end_to_end_pipeline.py::TestEndToEndPipeline::test_result_storage_error_scenarios -v

# Test version tracking
pytest tests/integration/test_end_to_end_pipeline.py::TestEndToEndPipeline::test_result_storage_version_tracking -v

# Test DataSaver coordination
pytest tests/integration/test_end_to_end_pipeline.py::TestEndToEndPipeline::test_data_saver_coordination -v
```

### What the Integration Tests Cover

**S3 Storage Testing:**
- Complete S3 workflow with bucket creation and object operations
- Multipart upload handling for large files
- Error scenarios including invalid buckets and permission failures
- Version tracking with proper S3 key structure
- Result retrieval and listing functionality

**Local Storage Testing:**
- File system operations with automatic directory creation
- Permission handling and error recovery
- Version tracking with organized directory structure
- Result persistence across process restarts
- UTF-8 encoding support for international characters

**Error Recovery Testing:**
- Storage backend failures during processing
- Network connectivity issues and retry logic
- Invalid configuration handling
- Processing continuation despite storage failures
- Proper error logging and status reporting

**DataSaver Coordination Testing:**
- Job status and result storage synchronization
- Transaction-like behavior for consistent state
- Version management across multiple submissions
- Metadata storage and retrieval
- Cross-backend compatibility testing

These integration tests provide confidence that result storage works correctly in real-world scenarios and help identify issues before production deployment.
