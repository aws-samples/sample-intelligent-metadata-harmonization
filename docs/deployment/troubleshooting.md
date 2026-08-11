# Troubleshooting Guide

This guide provides solutions to common deployment and runtime issues encountered with the Metadata Harmonization Platform.

## Deployment Issues

### CDK Bootstrap Issues

**Error: Need to perform AWS CDK bootstrap**
- Cause: CDK requires a bootstrap stack to manage deployment artifacts
- Fix: Run `make bootstrap` or `npx cdk bootstrap aws://ACCOUNT-NUMBER/REGION`

**Error: Bootstrap stack version mismatch**
- Cause: CDK CLI version doesn't match library version
- Fix: Run `npm install -g aws-cdk@latest` and re-bootstrap with `make bootstrap`

### Permission Issues

**Error: User is not authorized to perform action**
- Cause: IAM user/role lacks required permissions
- Fix:
  1. Verify credentials: `aws sts get-caller-identity`
  2. Ensure IAM permissions for: CloudFormation, ECS, DynamoDB, S3, IAM role management, VPC, Cognito
  3. Check AWS profile: `export AWS_PROFILE=your-profile-name`

**Error: Cannot assume role**
- Cause: CDK execution role not accessible or misconfigured
- Fix:
  1. Verify account number matches your AWS account in config
  2. Ensure CDK bootstrap ran in correct account/region
  3. Check trust relationships on CDK execution role

### Resource Naming Conflicts

**Error: Resource already exists**
- Cause: Resource names must be unique within account/region
- Fix: Update `deploymentName` in `config.yaml` to use a unique name:
  ```yaml
  dev:
    deploymentName: "metadata-harmonization-dev-v2"
  ```
- Or delete conflicting stack: `aws cloudformation delete-stack --stack-name conflicting-stack-name`

**Error: S3 bucket name already taken**
- Cause: S3 bucket names are globally unique
- Fix: CDK automatically generates unique names with random suffixes. If using custom names, ensure global uniqueness.

### Configuration Issues

**Error: Invalid configuration**
- Cause: Missing or malformed configuration fields
- Fix:
  1. Validate config: `make validateConfig`
  2. Ensure required fields exist:
     ```yaml
     dev:
       region: "us-east-1"
       accountNumber: "123456789012"
       deploymentName: "your-unique-name"
       deploymentStage: "dev"
     ```

**Error: Configuration file not found**
- Cause: Config file missing or inaccessible
- Fix:
  1. Ensure `config.yaml` exists in project root
  2. For Docker, verify file copied in Dockerfile
  3. Set custom path: `export CONFIG_PATH=/path/to/your/config.yaml`
  4. Check file permissions

**Error: YAML syntax error**
- Cause: Invalid YAML formatting
- Fix:
  1. Use spaces, not tabs
  2. Validate YAML syntax with linter
  3. Ensure proper string quoting

## Runtime Issues

### API Health Check Failures

**Error: ECS tasks failing health checks**
- Cause: Environment variables missing, database connection issues, or insufficient resources
- Diagnosis:
  ```bash
  # Check service status
  aws ecs describe-services --cluster your-cluster-name --services your-service-name

  # View logs
  aws logs tail /aws/ecs/metadata-harmonization-api --follow
  ```
- Fix:
  1. Verify environment variables in task definition
  2. Check DynamoDB table names and IAM permissions
  3. Ensure VPC endpoints configured for DynamoDB
  4. Increase memory/CPU limits if needed

### DynamoDB Access Issues

**Error: ResourceNotFoundException**
- Cause: Table doesn't exist or incorrect name
- Fix:
  1. List tables: `aws dynamodb list-tables --region your-region`
  2. Verify table names in environment variables
  3. Ensure ECS task role has DynamoDB permissions (GetItem, PutItem, Query, Scan, UpdateItem, DeleteItem)

**Error: ProvisionedThroughputExceededException**
- Cause: Provisioned capacity exceeded (rare with on-demand billing)
- Fix: Tables use on-demand billing by default. If using provisioned, increase capacity or implement exponential backoff.

### S3 Access Issues

**Error: Access Denied**
- Cause: Missing S3 permissions or incorrect bucket name
- Fix:
  1. Verify bucket names in environment variables
  2. Ensure ECS task role has S3 permissions (GetObject, PutObject, DeleteObject, ListBucket)
  3. Configure VPC endpoints for S3 access

### Authentication Issues

**Error: Invalid token**
- Cause: Token expired, invalid JWT config, or clock sync issues
- Fix:
  1. Verify Cognito config: `aws cognito-idp describe-user-pool --user-pool-id your-pool-id`
  2. Check JWT token configuration in API
  3. Ensure clock synchronization
  4. Verify token hasn't expired

**Error: User pool domain not found**
- Cause: Domain name taken or creation failed
- Fix:
  1. Check domain: `aws cognito-idp describe-user-pool-domain --domain your-domain-name`
  2. Use different domain name in configuration
  3. Verify domain created successfully during deployment

## Monitoring and Debugging

### Enable Debug Logging

1. Update log level in `config.yaml`:
   ```yaml
   dev:
     logLevel: "DEBUG"
   ```
2. Redeploy: `make deploy`
3. View logs: `aws logs tail /aws/ecs/metadata-harmonization-api --follow`

### Key CloudWatch Metrics

Monitor these metrics:
- ECS service CPU and memory utilization
- DynamoDB read/write capacity and throttling
- S3 request metrics and error rates
- ALB request count and response times

### Application Debugging

Filter error logs:
```bash
aws logs filter-log-events \
  --log-group-name /aws/ecs/metadata-harmonization-api \
  --filter-pattern "ERROR"
```

### Performance Optimization

For high response times or resource issues:
1. Scale up resources in `config.yaml`:
   ```yaml
   restApiConfig:
     containerConfig:
       cpuLimit: 2048
       memoryLimit: 4096
     autoScalingConfig:
       maxCapacity: 10
   ```
2. Optimize database queries (use query vs scan, add indexes, implement pagination)
3. Consider caching solutions (CloudFront, application-level, DynamoDB DAX)

## Related Documentation

- [Deployment Guide](deployment-guide.md) - Step-by-step deployment instructions
- [Configuration Guide](configuration.md) - Detailed configuration options
- [Architecture Overview](../getting-started/architecture-overview.md) - System architecture
