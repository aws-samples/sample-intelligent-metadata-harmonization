# Configuration Guide

This guide provides detailed information about configuring the Metadata Harmonization Platform for different environments and use cases.

## Configuration File Structure

The platform uses a YAML configuration file (`config.yaml`) to define deployment settings and runtime behavior. The configuration is environment-specific, allowing different settings for development, staging, and production.

## Configuration File Location

The API automatically searches for `config.yaml` in multiple locations to support different deployment scenarios:

1. **Docker Container**: `/usr/local/lib/python3.12/config.yaml` (for containerized deployments)
2. **API Project Root**: `projects/api/config.yaml` (for local development)
3. **Current Working Directory**: `./config.yaml` (fallback location)
4. **Environment Variable**: Path specified by `CONFIG_PATH` environment variable

### Custom Configuration Path

You can override the automatic search by setting the `CONFIG_PATH` environment variable:

```bash
export CONFIG_PATH=/path/to/your/config.yaml
```

This is particularly useful for Docker deployments where the configuration file may be mounted at a specific location.

### Basic Structure

```yaml
# Application name
appName: "metadata-harmonization-app"

# Current environment
env: "dev"  # or "staging", "prod"

# Environment-specific configurations
dev:
  # Development environment settings
staging:
  # Staging environment settings
prod:
  # Production environment settings
```

## Core Configuration Sections

### AWS Configuration

```yaml
dev:
  # AWS Configuration
  profile: "your-aws-profile"              # AWS CLI profile to use
  deploymentName: "metadata-harmonization-dev"  # Unique deployment identifier
  accountNumber: "123456789012"            # Your 12-digit AWS account number
  region: "us-east-1"                      # AWS region for deployment
  deploymentStage: "dev"                   # Stage identifier (dev/staging/prod)
  removalPolicy: "destroy"                 # Resource cleanup policy
```

**Configuration Options:**
- `profile`: AWS CLI profile name (optional if using default credentials)
- `deploymentName`: Must be unique across your AWS account
- `accountNumber`: Required for CDK bootstrap and cross-account access
- `region`: AWS region where resources will be deployed
- `deploymentStage`: Used in resource naming and tagging
- `removalPolicy`: "destroy" for dev/staging, "retain" for production

### Application Configuration

```yaml
dev:
  # Application Configuration
  logLevel: "INFO"                         # Logging level
  targetPlatform: "linux/amd64"           # Container platform
  runCdkNag: false                         # Enable CDK security checks
```

**Log Levels:**
- `DEBUG`: Detailed debugging information
- `INFO`: General information messages
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

### Metadata Configuration

```yaml
dev:
  metadataConfig:
    metadataConfigDir: "./data/schema"    # Directory containing schema files (relative path for portability)
    defaultSchemaVersion: "1.0"           # Default schema version
    enableSchemaValidation: true          # Enable schema validation
    maxFileSize: "100MB"                  # Maximum upload file size
```

**Schema Directory Configuration:**
- Use relative paths (e.g., `./data/schema`) for better portability across environments
- The path is resolved relative to the configuration file location
- For containerized deployments, ensure the schema directory is properly mounted

### Authentication Configuration

```yaml
dev:
  cognitoAuthConfig:
    userPoolName: "metadata-harmonization-users"     # Cognito user pool name
    userPoolDomainName: "metadata-harmonization-auth" # Cognito domain name
    userPoolId: "us-east-1_XXXXXXXXX"                # Existing user pool ID (optional)
    clientId: "your-client-id"                       # Existing client ID (optional)
    enableSignUp: true                               # Allow user registration
    passwordPolicy:
      minimumLength: 8
      requireUppercase: true
      requireLowercase: true
      requireNumbers: true
      requireSymbols: false
```

### API Configuration

```yaml
dev:
  restApiConfig:
    containerConfig:
      cpuLimit: 1024                       # CPU units (1024 = 1 vCPU)
      memoryLimit: 2048                    # Memory in MB
      port: 8080                           # Container port
      healthCheckPath: "/api/health"       # Health check endpoint

    autoScalingConfig:
      minCapacity: 1                       # Minimum number of tasks
      maxCapacity: 5                       # Maximum number of tasks
      targetCpuUtilization: 70             # CPU utilization target
      targetRequestCount: 100              # Requests per target

    domainConfig:
      domainName: "api.yourdomain.com"     # Custom domain (optional)
      certificateArn: "arn:aws:acm:..."    # SSL certificate ARN
```

### Storage Configuration

```yaml
dev:
  storageConfig:
    validationResultsBucket:
      lifecyclePolicy:
        deleteAfterDays: 90                # Auto-delete old results
        transitionToIA: 30                 # Move to Infrequent Access

    schemaStorageBucket:
      versioningEnabled: true              # Enable versioning
      publicReadAccess: false              # Block public access
```

### Monitoring and Alerting

```yaml
dev:
  alarmConfig:
    enable: false                          # Enable CloudWatch alarms
    emailAddresses:                        # Alert recipients
      - "admin@yourdomain.com"

    thresholds:
      apiErrorRate: 5                      # Error rate percentage
      apiResponseTime: 5000                # Response time in ms
      dynamodbThrottling: 10               # Throttled requests
```

## Complete Configuration Example

Below is a complete example for a development environment. For staging and production:
- **Staging**: Use higher resources (cpuLimit: 1024, memoryLimit: 2048), enable alarms, enable CDK Nag
- **Production**: Use production resources (cpuLimit: 2048+, memoryLimit: 4096+), set removalPolicy to "retain", lower alarm thresholds, enable CDK Nag

```yaml
appName: "metadata-harmonization-app"
env: "dev"

dev:
  profile: "dev-profile"
  deploymentName: "metadata-harmonization-dev"
  accountNumber: "123456789012"
  region: "us-east-1"
  deploymentStage: "dev"
  removalPolicy: "destroy"
  logLevel: "DEBUG"
  targetPlatform: "linux/amd64"
  runCdkNag: false

  metadataConfig:
    metadataConfigDir: "./data/schema"
    defaultSchemaVersion: "1.0"
    enableSchemaValidation: true
    maxFileSize: "100MB"

  cognitoAuthConfig:
    userPoolName: "metadata-harmonization-users"
    userPoolDomainName: "metadata-harmonization-auth"
    enableSignUp: true
    passwordPolicy:
      minimumLength: 8
      requireUppercase: true
      requireLowercase: true
      requireNumbers: true
      requireSymbols: false

  restApiConfig:
    containerConfig:
      cpuLimit: 512
      memoryLimit: 1024
      port: 8080
      healthCheckPath: "/api/health"
    autoScalingConfig:
      minCapacity: 1
      maxCapacity: 3
      targetCpuUtilization: 70
      targetRequestCount: 100

  alarmConfig:
    enable: false

  storageConfig:
    validationResultsBucket:
      lifecyclePolicy:
        deleteAfterDays: 30
    schemaStorageBucket:
      versioningEnabled: true
      publicReadAccess: false
```

## Configuration Validation

### Validate Configuration File

```bash
# Validate configuration syntax and required fields
make validateConfig
```

### Common Validation Errors

1. **Missing Required Fields**:
   ```
   ERROR: No 'region' specified in config.yaml
   ```
   Solution: Add the required field to your environment configuration.

2. **Invalid AWS Account Number**:
   ```
   ERROR: accountNumber must be a 12-digit string
   ```
   Solution: Ensure account number is exactly 12 digits.

3. **Invalid Region**:
   ```
   ERROR: Invalid AWS region specified
   ```
   Solution: Use a valid AWS region code (e.g., us-east-1, eu-west-1).

## Environment Variables

The deployment process generates environment variables for the application:

### Generated Variables

```bash
# DynamoDB Tables
METADATA_SCHEMAS_TABLE=your-schemas-table-name
METADATA_UPLOAD_JOB_TABLE=your-jobs-table-name

# S3 Buckets
VALIDATION_RESULTS_BUCKET=your-results-bucket-name
SCHEMA_STORAGE_BUCKET=your-schemas-bucket-name

# Authentication
AUTHORITY=https://cognito-idp.region.amazonaws.com/user-pool-id
CLIENT_ID=your-cognito-client-id

# API Configuration
API_BASE_URL=https://your-api-domain.com
```

### Local Development Variables

For local development, create a `.env` file:

```bash
# Generate .env file from deployed resources
make createLocalDotEnvFile
```

## Related Documentation

- [Deployment Guide](deployment-guide.md) - Step-by-step deployment instructions
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [Architecture Overview](../getting-started/architecture-overview.md) - System architecture
