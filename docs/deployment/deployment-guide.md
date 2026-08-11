# Metadata Harmonization Platform - Deployment Guide

This guide provides step-by-step instructions for deploying the Metadata Harmonization Platform to AWS.

## Prerequisites

### Required Tools
- **Node.js 18+**: For CDK and frontend development
- **Python 3.12+**: For API development and deployment
- **AWS CLI**: Configured with appropriate permissions
- **AWS CDK CLI**: Install with `npm install -g aws-cdk`
- **Docker**: For building container images
- **Make**: For using the provided Makefile commands
- **yq**: Install with `sudo apt-get install yq` (or `brew install yq` on macOS). The Makefile uses it to read `config.yaml`
- **uv**: Python package manager for dependency management

### AWS Permissions

Your AWS user/role needs permissions for:
- ECS (Fargate services), DynamoDB, S3, Cognito, VPC, IAM, CloudFormation, ECR, CloudWatch

## Configuration Setup

### 1. Copy Configuration Template

```bash
cp config.yaml.example config.yaml
```

### 2. Update Configuration

Edit `config.yaml` with your specific values:

```yaml
# Application name
appName: "metadata-harmonization-app"

# Current environment
env: "dev"  # or "staging", "prod"

# Environment-specific configuration
dev:
  # AWS Configuration
  profile: "your-aws-profile"
  deploymentName: "metadata-harmonization-dev"
  accountNumber: "123456789012"  # Your 12-digit AWS account number
  region: "us-east-1"
  deploymentStage: "dev"
  removalPolicy: "destroy"  # Use "retain" for production

  # Application Configuration
  logLevel: "INFO"
  targetPlatform: "linux/amd64"

  # Metadata Configuration
  metadataConfig:
    metadataConfigDir: "./data"

  # Authentication Configuration
  cognitoAuthConfig:
    userPoolName: "metadata-harmonization-users"
    userPoolDomainName: "metadata-harmonization-auth"

  # Additional configuration sections...
```

### 3. Validate Configuration

```bash
make validateConfig
```

## Deployment Process

### Step 1: Install Dependencies

```bash
# Install all dependencies (recommended)
make install

# Or install individually:
make installPythonRequirements  # Python/processor dependencies
make installTypeScriptRequirements  # Node.js/frontend/infra dependencies

# Install uv package manager if not present
make installUv
```

### Step 2: Bootstrap CDK (First Time Only)

```bash
# Bootstrap CDK using the Makefile (recommended)
make bootstrap

# Or manually with CDK CLI
npx cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

### Step 3: Deploy Infrastructure

```bash
# Deploy the complete infrastructure
make deploy
```

This command will:
1. Build the API container image
2. Push the image to ECR
3. Deploy the CDK stack with all resources
4. Configure auto-scaling and monitoring

### Step 4: Generate Environment Variables

```bash
# Generate .env file with deployed resource information
make createLocalDotEnvFile
```

### Step 5: Verify Deployment

```bash
# Run deployment verification checks
make verifyDeployment
```

## Docker Configuration

The API is deployed as a Docker container with automatic configuration file handling:

### Configuration File Locations in Container

The Docker build process automatically:
1. Copies `config.yaml` from the project root to `/app/config.yaml` in the container
2. Sets the `CONFIG_PATH` environment variable to `/app/config.yaml`
3. The API's configuration loader searches multiple locations as fallback

### Container Environment Variables

Key environment variables set in the container:
- `CONFIG_PATH=/app/config.yaml` - Primary configuration file location
- `AWS_REGION` - AWS region for services
- `LOG_LEVEL` - Application logging level
- Database and storage service configurations (DynamoDB tables, S3 buckets)

### Configuration Override

If you need to override the configuration file location in a custom deployment:

```bash
# Set custom config path
export CONFIG_PATH=/custom/path/to/config.yaml

# Or mount config file to expected location
docker run -v /host/config.yaml:/app/config.yaml your-api-image
```

## Post-Deployment Configuration

### 1. Create Initial Schemas

Upload validation schemas to the schema storage bucket:

```bash
# Upload schemas from data directory
aws s3 sync ./data/ s3://your-schema-storage-bucket/schemas/
```

### 2. Create Cognito Users

Create initial users in the Cognito user pool using the AWS Console or CLI.

**AWS Console:**

1. Open the [Amazon Cognito console](https://console.aws.amazon.com/cognito/v2/idp/user-pools)
2. Select the user pool created by the deployment (e.g. `metadata-harmonization-users`)
3. Go to **Users** and click **Create user**
4. Enter the user's email address and a temporary password
5. Click **Create user**

The user will be prompted to set a permanent password on first login.

**AWS CLI:**

```bash
# Create a user via AWS CLI
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS
```

### 3. Test API Endpoints

```bash
# Test health endpoint
curl https://your-api-domain/api/health

# Test authenticated endpoint (requires token)
curl -H "Authorization: Bearer $TOKEN" \
  https://your-api-domain/api/v1/metadata/schemas
```

## Monitoring

### CloudWatch Dashboards

The deployment creates CloudWatch dashboards for:
- **API Metrics**: Request count, response time, error rate
- **Infrastructure Metrics**: ECS tasks, DynamoDB usage, S3 requests
- **Cost Metrics**: Resource usage and estimated costs

### Log Groups

- **API Logs**: `/aws/ecs/metadata-harmonization-api`
- **CDK Logs**: `/aws/lambda/cdk-*`

### Alarms (Production)

When enabled, alarms monitor:
- High API error rates
- DynamoDB throttling
- ECS task failures
- High response times

## Deployment Verification

### Automated Testing

The platform includes comprehensive deployment testing scripts:

#### Infrastructure Testing
```bash
# Run comprehensive infrastructure tests
python scripts/test_infrastructure_deployment.py
```

This script tests:
- CloudFormation stack status
- DynamoDB table configuration and accessibility
- S3 bucket security and encryption
- ECS service health and task definitions
- API endpoint responsiveness
- Authentication configuration

#### Deployment Verification
```bash
# Run basic deployment verification
python scripts/verify_deployment.py
```

This script verifies:
- DynamoDB tables exist and are active
- S3 buckets are accessible
- API endpoints respond correctly
- Cognito configuration is valid

### Manual Verification Steps

1. **Check CloudFormation Stack**:
   ```bash
   aws cloudformation describe-stacks --stack-name your-stack-name
   ```

2. **Verify ECS Service**:
   ```bash
   aws ecs describe-services --cluster your-cluster --services your-service
   ```

3. **Test API Health**:
   ```bash
   curl https://your-api-domain/api/health
   ```

4. **Check Logs**:
   ```bash
   aws logs tail /aws/ecs/metadata-harmonization-api --follow
   ```

## Cleanup

### Development Environment

```bash
# Destroy all resources (with confirmation prompt)
make destroy

# Clean local development artifacts
make clean
```

### Production Environment

For production, consider:
1. Backup important data before cleanup
2. Update `removalPolicy` to "destroy" if needed
3. Manually delete retained resources after stack deletion

This sample also leaves several security controls disabled or unimplemented
on purpose to keep the reference architecture simple — see
[Production Considerations](../security/production-considerations.md) for the
full list (Bedrock Guardrails, WAF, CloudTrail, origin TLS, Cognito hardening,
rate limiting) before deploying this for real traffic.

## Related Documentation

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [Architecture Overview](../getting-started/architecture-overview.md) - System architecture
- [Production Considerations](../security/production-considerations.md) - Security controls to enable before a real deployment
