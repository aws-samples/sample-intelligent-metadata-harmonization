# Installation Guide

This guide provides detailed instructions for installing and setting up the MetadataHarmonizationProcessor package in various environments.

## Table of Contents

- [System Requirements](#system-requirements)
- [Basic Installation](#basic-installation)
- [Development Installation](#development-installation)
- [AWS Services Setup](#aws-services-setup)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Python Version
- **Python 3.9 or higher** (recommended: Python 3.11+)
- **pip 21.0 or higher**

### Operating Systems
- **Linux** (Ubuntu 20.04+, CentOS 8+, Amazon Linux 2)
- **macOS** (10.15+)
- **Windows** (10+, with WSL recommended for development)

### Hardware Requirements
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large datasets)
- **Storage**: 1GB free space for package and dependencies
- **Network**: Internet access for AWS services and package downloads

## Basic Installation

### 1. Install from Source (Recommended)

```bash
# Clone or navigate to the package directory
cd projects/metadata-harmonization-processor

# Install the package
pip install -e .
```

### 2. Install with Specific Dependency Groups

```bash
# Install with all dependencies (recommended for development)
pip install -e .[dev]

# Install with only test dependencies
pip install -e .[test]

# Install with documentation dependencies
pip install -e .[docs]
```

### 3. Virtual Environment Installation (Recommended)

```bash
# Create virtual environment
python -m venv metadata-processor-env

# Activate virtual environment
# On Linux/macOS:
source metadata-processor-env/bin/activate
# On Windows:
metadata-processor-env\Scripts\activate

# Install package
pip install -e .
```

## Development Installation

### 1. Full Development Setup

```bash
# Clone the repository (if not already done)
cd projects/metadata-harmonization-processor

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel

# Install with development dependencies
pip install -e .[dev]

# Install pre-commit hooks (optional)
pre-commit install
```

### 2. Verify Development Installation

```bash
# Run tests to verify installation
pytest

# Check code formatting
black --check src tests

# Run type checking
mypy src

# Run linting
flake8 src tests
```

### 3. Development Dependencies

The development installation includes:

- **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`, `tempfile-pytest`
- **Code Quality**: `black`, `isort`, `flake8`, `mypy`
- **Development Tools**: `pre-commit`, `ipython`
- **Documentation**: `sphinx`, `sphinx-rtd-theme` (if using docs extra)

## AWS Services Setup

### 1. AWS Credentials Configuration

#### Option A: AWS CLI Configuration
```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region
```

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

#### Option C: IAM Roles (Recommended for Production)
```bash
# No configuration needed - IAM role will be used automatically
# Ensure your EC2 instance or container has the appropriate IAM role attached
```

### 2. Required AWS Services

#### DynamoDB Table for Job Status
```bash
# Create DynamoDB table
aws dynamodb create-table \
    --table-name metadata-processor-jobs \
    --attribute-definitions AttributeName=job_id,AttributeType=S \
    --key-schema AttributeName=job_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

#### ElastiCache Redis Cluster (Optional)
```bash
# Create Redis cluster (replace subnet-group and security-group)
aws elasticache create-cache-cluster \
    --cache-cluster-id metadata-processor-cache \
    --engine redis \
    --cache-node-type cache.t3.micro \
    --num-cache-nodes 1 \
    --cache-subnet-group-name your-subnet-group \
    --security-group-ids sg-your-security-group \
    --region us-east-1
```

#### S3 Bucket for Session Management
```bash
# Create S3 bucket for session storage
aws s3 mb s3://your-metadata-processor-sessions --region us-east-1

# Enable versioning (optional)
aws s3api put-bucket-versioning \
    --bucket your-metadata-processor-sessions \
    --versioning-configuration Status=Enabled
```

### 3. IAM Permissions

Create an IAM policy with the following permissions:

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
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/metadata-processor-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-metadata-processor-sessions",
                "arn:aws:s3:::your-metadata-processor-sessions/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:InvokeEndpoint"
            ],
            "Resource": "arn:aws:sagemaker:*:*:endpoint/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "elasticache:DescribeCacheClusters"
            ],
            "Resource": "*"
        }
    ]
}
```

## Configuration

### 1. Create Configuration Directory

```bash
# Create configuration directory
mkdir -p ~/.metadata-processor

# Or use project-specific configuration
mkdir -p ./config
```

### 2. Basic Configuration File

Create `config.yaml`:

```yaml
# Basic configuration
aws_region: "us-east-1"
schema_directory: "./data/schema"

# Session management
session_saver_type: "file"  # Use "s3" for production

# Caching (optional)
enable_redis_cache: false
enable_memory_cache: true
memory_cache_max_size: 1000

# AI configuration
embedding_provider: "bedrock"
bedrock_model_id: "amazon.titan-embed-text-v1"
cosine_similarity_threshold: 0.7
```

### 3. Schema Directory Setup

```bash
# Create schema directory structure
mkdir -p data/schema

# Create catalog.json (example)
cat > data/schema/catalog.json << 'EOF'
[
  {
    "core_uuid": "core-001",
    "core_name": "Patient Core Schema",
    "core_path": "patient_core_v1.json",
    "program": [
      {
        "program_uuid": "prog-001",
        "program_name": "Flu Surveillance",
        "program_path": "flu_program_v1.json"
      }
    ]
  }
]
EOF

# Create example schema files
cat > data/schema/patient_core_v1.json << 'EOF'
{
  "type": "object",
  "properties": {
    "patient_id": {
      "type": "string",
      "amd_required": true
    },
    "age": {
      "type": "integer",
      "minimum": 0,
      "maximum": 150,
      "amd_required": true
    }
  }
}
EOF

cat > data/schema/flu_program_v1.json << 'EOF'
{
  "type": "object",
  "properties": {
    "test_result": {
      "type": "string",
      "enum": ["positive", "negative", "pending"],
      "amd_required": true
    },
    "test_date": {
      "type": "string",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
      "amd_required": false
    }
  }
}
EOF
```

## Verification

### 1. Basic Package Import Test

```python
# Test basic import
python -c "
import metadata_harmonization_processor
print('✓ Package imported successfully')
print(f'Version: {metadata_harmonization_processor.__version__}')
"
```

### 2. Configuration Test

```python
# Test configuration loading
python -c "
from metadata_harmonization_processor.config import load_processor_settings
try:
    config = load_processor_settings('config.yaml')
    print('✓ Configuration loaded successfully')
    print(f'AWS Region: {config.aws_region}')
    print(f'Schema Directory: {config.schema_directory}')
except Exception as e:
    print(f'✗ Configuration error: {e}')
"
```

### 3. AWS Services Test

```python
# Test AWS connectivity
python -c "
import boto3
from botocore.exceptions import NoCredentialsError

try:
    # Test AWS credentials
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    print(f'✓ AWS credentials valid: {identity[\"Arn\"]}')

    # Test DynamoDB access
    dynamodb = boto3.client('dynamodb')
    tables = dynamodb.list_tables()
    print(f'✓ DynamoDB accessible: {len(tables[\"TableNames\"])} tables')

    # Test S3 access
    s3 = boto3.client('s3')
    buckets = s3.list_buckets()
    print(f'✓ S3 accessible: {len(buckets[\"Buckets\"])} buckets')

except NoCredentialsError:
    print('✗ AWS credentials not configured')
except Exception as e:
    print(f'⚠ AWS services partially accessible: {e}')
"
```

### 4. Full Integration Test

```python
# Run basic integration test
python -c "
import asyncio
import pandas as pd
from pathlib import Path
from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import load_processor_settings
from metadata_harmonization_processor.implementations import (
    DynamodbJobStatusSaver, FileBasedSchemaCollector
)

async def test():
    try:
        # Create test components
        job_saver = DynamodbJobStatusSaver('metadata-processor-jobs')
        schema_collector = FileBasedSchemaCollector('./data/schema')

        # Load configuration first
        config = load_processor_settings(config_path=Path('config.yaml'))

        # Initialize processor with configuration-driven approach
        processor = MetadataHarmonizationProcessor(
            config=config,
            session_id="test-session"
        )

        print('✓ Processor initialized successfully')

        # Test schema loading
        schemas = await schema_collector.get_available_schemas()
        print(f'✓ Found {len(schemas)} schema combinations')

        await processor.cleanup()
        print('✓ Integration test passed')

    except Exception as e:
        print(f'✗ Integration test failed: {e}')

asyncio.run(test())
"
```

## Troubleshooting

### Common Installation Issues

#### 1. Python Version Issues
```bash
# Check Python version
python --version

# If using older Python, install specific version
# On Ubuntu:
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# Use specific Python version
python3.11 -m pip install -e .
```

#### 2. Permission Issues
```bash
# Use user installation
pip install --user -e .

# Or fix permissions
sudo chown -R $USER:$USER ~/.local/lib/python*/site-packages/
```

#### 3. Dependency Conflicts
```bash
# Create clean virtual environment
python -m venv clean-env
source clean-env/bin/activate
pip install --upgrade pip
pip install -e .
```

#### 4. AWS Credentials Issues
```bash
# Verify credentials
aws sts get-caller-identity

# Check credential files
ls -la ~/.aws/
cat ~/.aws/credentials
cat ~/.aws/config
```

### Performance Optimization

#### 1. Memory Usage
```yaml
# Reduce memory usage in config.yaml
memory_cache_max_size: 500
enable_redis_cache: true  # Use Redis instead of memory
```

#### 2. Network Optimization
```yaml
# Increase timeouts for slow networks
timeout_seconds: 600
max_retries: 5
```

#### 3. Parallel Processing
```python
# Process data in chunks for large datasets
chunk_size = 1000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    results = await processor.process(chunk)
```

### Getting Help

If installation issues persist:

1. **Check system requirements** and ensure compatibility
2. **Review error messages** carefully for specific issues
3. **Test individual components** to isolate problems
4. **Check AWS service status** if using cloud services
5. **Create minimal reproduction case** for debugging

For additional support:
- Review the [Troubleshooting Guide](TROUBLESHOOTING.md)
- Check the [API Documentation](API.md)
- Examine the [Examples](../examples/) for working configurations
