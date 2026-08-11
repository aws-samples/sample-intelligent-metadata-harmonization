# MetadataHarmonizationProcessor Examples

This directory contains example configurations, datasets, and usage scripts for the MetadataHarmonizationProcessor package.

## Files Overview

### Configuration Files
- **`config-basic.yaml`** - Local development configuration (no AWS dependencies)
- **`config-production.yaml`** - Production configuration with AWS services
- **`config-no-ai.yaml`** - Configuration with AI features disabled
- **`config-sagemaker.yaml`** - Configuration using SageMaker instead of Bedrock

### Usage Scripts
- **`basic_usage.py`** - Simple example demonstrating local development setup
- **`advanced_usage.py`** - Advanced example with custom implementations
- **`custom_implementations.py`** - Example of creating custom JobStatusSaver and SchemaCollector

### Example Data
- **`data/example_metadata.csv`** - Sample dataset with various validation errors
- **`data/schema/`** - Example schema files for testing

## Example Dataset

The `data/example_metadata.csv` file contains sample patient metadata designed to demonstrate various validation scenarios:

### Data Structure
```csv
patient_id,age,gender,diagnosis,collection_date
P001,25,M,Cyclospora,2023-01-15
P002,30,F,Cyclospora,2023-01-16
...
```

### Validation Scenarios Included

1. **Valid Records** - Properly formatted data that passes all validation
2. **REQUIRED_VALUE Errors** - Missing required fields (empty diagnosis, age)
3. **INVALID_OPTION Errors** - Values not in allowed enum lists
   - `gender`: "Male", "Female", "m", "f" instead of "M", "F", "Other"
   - `diagnosis`: "Unknown_Diagnosis" instead of "Cyclospora", "Other"
4. **INVALID_PATTERN Errors** - Values that don't match expected patterns
   - `patient_id`: "INVALID_ID" instead of "P###" format
   - `age`: "invalid_age" instead of numeric value, or out of range (200)
   - `collection_date`: "invalid_date" or wrong format "2023/01/22"

### AI-Powered Recommendations

When AI features are enabled, the processor will provide intelligent recommendations:
- **Semantic Search**: For INVALID_OPTION errors, finds closest valid options using embeddings
- **Pattern Matching**: For INVALID_PATTERN errors, suggests corrections based on patterns

## Running the Examples

### Local Development (No AWS Required)

```bash
# Run basic example with local development setup
cd projects/metadata-harmonization-processor
python examples/basic_usage.py
```

This will:
- Use LocalJobStatusSaver with file-based storage
- Load example schema and dataset
- Process metadata and show validation results
- Save job status to `./job_status/` directory
- Work without AWS credentials

### Production Setup

1. Update configuration:
```bash
cp examples/config-production.yaml examples/config-custom.yaml
# Edit config-custom.yaml with your AWS settings
```

2. Set up AWS resources:
- Create DynamoDB table for job status
- Create S3 bucket for session management
- Set up ElastiCache Redis (optional for enhanced caching)

3. Run with production config:
```python
config = load_processor_settings(config_path=Path("examples/config-custom.yaml"))
```

## Schema Files

The example schema files demonstrate the expected structure:

### Core Schema (`example_core_schema.json`)
- Defines basic patient information fields
- Includes validation rules (patterns, enums, ranges)

### Program Schema (`example_program_schema.json`)
- Defines program-specific fields
- Extends core schema with additional requirements

### Catalog (`catalog.json`)
- Maps schema UUIDs to file paths
- Defines available core/program combinations

## Customization

### Adding Your Own Data
1. Replace `data/example_metadata.csv` with your dataset
2. Update schema files to match your data structure
3. Update schema UUIDs in `basic_usage.py` to match your catalog

### Custom Implementations
See `custom_implementations.py` for examples of:
- Creating custom JobStatusSaver implementations
- Creating custom SchemaCollector implementations
- Extending the processor with additional functionality

## Troubleshooting

### Common Issues

1. **Schema not found**: Update `schema_directory` in config file
2. **Permission errors**: Check write permissions for job_status and sessions directories
3. **AWS errors**: Verify credentials and region settings for production mode
4. **Import errors**: Ensure the package is installed or PYTHONPATH includes src directory

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=src
export PROCESSOR_LOG_LEVEL=DEBUG
python examples/basic_usage.py
```
