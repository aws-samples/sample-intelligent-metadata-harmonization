# Infrastructure - AWS Deployment Configuration

**Purpose**: AWS CDK infrastructure for deploying the complete metadata harmonization platform with auto-scaling, security, and monitoring.

**Key User-Modifiable Components**:
- `config.yaml` (project root) - Deployment configuration and AWS settings
- `lib/` - CDK stack definitions and resource configurations
- `bin/metadata-harmonization-app.ts` - Main deployment entry point

## Quick Start

**Prerequisites**: Node.js 18+, AWS CLI configured, Docker running

```bash
# Install and configure
cd projects/infra
npm install

# Deploy to AWS (requires configuration)
make deploy    # Uses project root config.yaml

# Local development (no AWS deployment needed)
make runLocal  # Runs API and UI locally
```

## Configuration

### Deployment Configuration (config.yaml)
```yaml
# Project root config.yaml
appName: "metadata-harmonization-app"
deploymentName: "your-deployment-name"
accountNumber: "123456789012"
region: "us-east-1"
deploymentStage: "dev"
```

### Metadata Configuration
```yaml
metadataConfig:
  metadataConfigDir: "./data"
  # Optional custom resource names
  validationResultsBucketName: "custom-validation-results"
  schemaStorageBucketName: "custom-schema-storage"
  metadataSchemasTableName: "custom-metadata-schemas"
  metadataUploadJobTableName: "custom-metadata-upload-job"
```

### Auto-scaling Configuration
```yaml
restApiConfig:
  containerConfig:
    cpuLimit: 1024
    memoryLimit: 2048
  autoScalingConfig:
    minCapacity: 1
    maxCapacity: 5
    metricConfig:
      albMetricName: "RequestCountPerTarget"
      targetValue: 100
```

## AWS Resources

| Resource | Purpose | Key Details |
|----------|---------|-------------|
| **ECS Fargate** | API containers | Auto-scaling, 1024 CPU, 2048 MB |
| **DynamoDB** | Schema and job storage | Pay-per-request, AWS encryption |
| **S3** | Validation results and schemas | SSE-S3 encryption |
| **Cognito** | User authentication | OIDC provider |
| **ALB + CloudFront** | Load balancing and CDN | SSL termination |
| **VPC** | Network isolation | Public/private subnets |

### DynamoDB Tables

| Table | Partition Key | GSI | Purpose |
|-------|---------------|-----|---------|
| METADATA_SCHEMAS_TABLE | core_schema_id (String) | None | Validation schemas and metadata |
| METADATA_UPLOAD_JOB | job_id (String) | user-id-index (user_id, created_at) | Job tracking and results |

### S3 Buckets

| Bucket | Purpose | Access |
|--------|---------|--------|
| Validation Results | Store validation JSON files | Read/write for API |
| Schema Storage | Store schema files | Read-only for API |

## Deployment

### Initial Setup

1. Install dependencies:
```bash
npm install
```

2. Bootstrap CDK (first time only):
```bash
make bootstrap
```

3. Configure your environment in `config.yaml`

### Deploy Infrastructure

```bash
# Deploy infrastructure
make deploy

# Destroy infrastructure
make destroy
```

### Manual CDK Commands

```bash
# Synthesize CloudFormation template
npx cdk synth

# Deploy infrastructure
npx cdk deploy

# View differences
npx cdk diff

# Destroy infrastructure
npx cdk destroy
```

## ECS Environment Variables

The ECS service receives the following environment variables:
- `METADATA_SCHEMAS_TABLE`: DynamoDB table name
- `METADATA_UPLOAD_JOB_TABLE`: DynamoDB table name
- `VALIDATION_RESULTS_BUCKET`: S3 bucket name
- `SCHEMA_STORAGE_BUCKET`: S3 bucket name
- `AUTHORITY`: Cognito authority URL
- `CLIENT_ID`: Cognito client ID

## Troubleshooting

### Deployment Failures
- Check IAM permissions for CDK deployment
- Verify AWS CLI configuration and credentials
- Check for resource naming conflicts

### API Health Check Failures
- Review ECS task logs in CloudWatch: `/aws/ecs/metadata-harmonization-api`
- Verify environment variables are set correctly
- Check security group configurations

### DynamoDB/S3 Access Issues
- Verify IAM permissions for ECS task role
- Check VPC endpoints for service access
- Validate resource names in environment variables

## Testing

```bash
# Run CDK unit tests
npm test

# Run infrastructure integration tests
npm run test:integration

# Verify deployment health
make verifyDeployment

# Test API endpoints
curl -H "Authorization: Bearer $TOKEN" \
  https://your-api-domain/api/health
```
