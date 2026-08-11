/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Integration tests for full stack deployment with new infrastructure
 */

import { App, Stack, CfnOutput, PhysicalName } from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import { createTestApp, getTemplate, createMockConfig } from '../fixtures/test-utils';

describe('Full Stack Deployment Integration Tests', () => {
  let app: App;
  let stack: Stack;
  let template: Template;
  let config: any;

  beforeEach(() => {
    const testApp = createTestApp('FullStackTestStack');
    app = testApp.app;
    stack = testApp.stack;
    config = createMockConfig();
  });

  describe('Complete Infrastructure Stack', () => {
    test('should deploy all required resources for metadata harmonization', () => {
      // Create DynamoDB tables
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
      });

      const metadataUploadJobTable = new dynamodb.Table(stack, 'MetadataUploadJob', {
        partitionKey: {
          name: 'job_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
      });

      metadataUploadJobTable.addGlobalSecondaryIndex({
        indexName: 'user-id-index',
        partitionKey: {
          name: 'user_id',
          type: dynamodb.AttributeType.STRING,
        },
        sortKey: {
          name: 'created_at',
          type: dynamodb.AttributeType.STRING,
        },
      });

      // Create S3 buckets
      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
      });

      const schemaStorageBucket = new s3.Bucket(stack, 'SchemaStorage', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
      });

      // Create IAM role with permissions
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Grant DynamoDB permissions
      metadataSchemasTable.grantReadWriteData(taskRole);
      metadataUploadJobTable.grantReadWriteData(taskRole);

      // Grant S3 permissions
      validationResultsBucket.grantReadWrite(taskRole);
      schemaStorageBucket.grantRead(taskRole);

      template = getTemplate(stack);

      // Verify all resources exist
      template.resourceCountIs('AWS::DynamoDB::Table', 2);
      template.resourceCountIs('AWS::S3::Bucket', 2);
      template.resourceCountIs('AWS::IAM::Role', 1);
      const policies = template.findResources('AWS::IAM::Policy');
      expect(Object.keys(policies).length).toBeGreaterThanOrEqual(1);

      // Verify no RDS resources
      template.resourceCountIs('AWS::RDS::DBInstance', 0);
      template.resourceCountIs('AWS::RDS::DBSubnetGroup', 0);
      template.resourceCountIs('AWS::SecretsManager::Secret', 0);
    });

    test('should create resources with correct naming convention', () => {
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        tableName: `${config.appName}-metadata-schemas-${config.deploymentStage}`,
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        bucketName: `${config.appName}-validation-results-${config.deploymentStage}`,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      template = getTemplate(stack);

      // Verify naming convention
      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'metadata-harmonization-app-test-metadata-schemas-dev'
      });

      template.hasResourceProperties('AWS::S3::Bucket', {
        BucketName: 'metadata-harmonization-app-test-validation-results-dev'
      });
    });

    test('should configure resources with proper security settings', () => {
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        pointInTimeRecovery: true,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
        versioned: true,
      });

      template = getTemplate(stack);

      // Verify security configurations
      template.hasResourceProperties('AWS::DynamoDB::Table', {
        SSESpecification: {
          SSEEnabled: true
        },
        PointInTimeRecoverySpecification: {
          PointInTimeRecoveryEnabled: true
        }
      });

      template.hasResourceProperties('AWS::S3::Bucket', {
        BucketEncryption: {
          ServerSideEncryptionConfiguration: [{
            ServerSideEncryptionByDefault: {
              SSEAlgorithm: 'AES256'
            }
          }]
        },
        PublicAccessBlockConfiguration: {
          BlockPublicAcls: true,
          BlockPublicPolicy: true,
          IgnorePublicAcls: true,
          RestrictPublicBuckets: true
        },
        VersioningConfiguration: {
          Status: 'Enabled'
        }
      });

      // Verify SSL enforcement policy exists
      template.hasResourceProperties('AWS::S3::BucketPolicy', {
        PolicyDocument: Match.objectLike({
          Statement: Match.arrayWith([
            Match.objectLike({
              Effect: 'Deny',
              Condition: {
                Bool: {
                  'aws:SecureTransport': 'false'
                }
              }
            })
          ])
        })
      });
    });
  });

  describe('ECS Service Integration', () => {
    test('should create ECS task definition with correct environment variables', () => {
      // Create infrastructure resources
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      // Create ECS task definition
      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      const container = taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        environment: {
          AWS_REGION: config.region,
          METADATA_SCHEMAS_TABLE: metadataSchemasTable.tableName,
          VALIDATION_RESULTS_BUCKET: validationResultsBucket.bucketName,
          LOG_LEVEL: config.logLevel,
        },
        logging: ecs.LogDrivers.awsLogs({
          streamPrefix: 'metadata-api',
        }),
      });

      container.addPortMappings({
        containerPort: 8080,
        protocol: ecs.Protocol.TCP,
      });

      template = getTemplate(stack);

      // Verify task definition
      template.hasResourceProperties('AWS::ECS::TaskDefinition', {
        ContainerDefinitions: [{
          Environment: Match.arrayWith([
            Match.objectLike({ Name: 'AWS_REGION', Value: 'us-east-1' }),
            Match.objectLike({ Name: 'LOG_LEVEL', Value: 'DEBUG' }),
          ]),
          Image: 'metadata-harmonization-api:latest',
          PortMappings: [{
            ContainerPort: 8080,
            Protocol: 'tcp'
          }]
        }]
      });

      // Verify no database-related environment variables
      const taskDef = template.findResources('AWS::ECS::TaskDefinition');
      const containerDef = Object.values(taskDef)[0] as any;
      const environment = containerDef.Properties.ContainerDefinitions[0].Environment;

      const envNames = environment.map((env: any) => env.Name);
      expect(envNames).not.toContain('DB_HOST');
      expect(envNames).not.toContain('DB_PORT');
      expect(envNames).not.toContain('DB_NAME');
      expect(envNames).not.toContain('DB_USERNAME');
      expect(envNames).not.toContain('DB_PASSWORD_SECRET_ARN');
    });

    test('should grant proper permissions to ECS task role', () => {
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      // Grant permissions
      metadataSchemasTable.grantReadWriteData(taskDefinition.taskRole);
      validationResultsBucket.grantReadWrite(taskDefinition.taskRole);

      template = getTemplate(stack);

      // Verify IAM policies are created (CDK may merge into single policy)
      const grantPolicies = template.findResources('AWS::IAM::Policy');
      expect(Object.keys(grantPolicies).length).toBeGreaterThanOrEqual(1);

      // Verify DynamoDB permissions exist in one of the policies
      const policyValues = Object.values(grantPolicies) as any[];
      const hasDynamoActions = policyValues.some((p: any) =>
        p.Properties.PolicyDocument.Statement.some((s: any) =>
          Array.isArray(s.Action) && s.Action.some((a: string) => a.startsWith('dynamodb:'))
        )
      );
      expect(hasDynamoActions).toBe(true);

      // Verify S3 permissions exist in one of the policies
      const hasS3Actions = policyValues.some((p: any) =>
        p.Properties.PolicyDocument.Statement.some((s: any) =>
          Array.isArray(s.Action) && s.Action.some((a: string) => a.startsWith('s3:'))
        )
      );
      expect(hasS3Actions).toBe(true);
    });
  });

  describe('CloudFormation Outputs', () => {
    test('should create outputs for all infrastructure resources', () => {
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const metadataUploadJobTable = new dynamodb.Table(stack, 'MetadataUploadJob', {
        partitionKey: {
          name: 'job_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const schemaStorageBucket = new s3.Bucket(stack, 'SchemaStorage', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      // Add CloudFormation outputs
      new CfnOutput(stack, 'MetadataSchemasTableName', {
        value: metadataSchemasTable.tableName,
        description: 'DynamoDB table name for metadata schemas',
      });
      new CfnOutput(stack, 'MetadataUploadJobTableName', {
        value: metadataUploadJobTable.tableName,
        description: 'DynamoDB table name for metadata upload jobs',
      });
      new CfnOutput(stack, 'ValidationResultsBucketName', {
        value: validationResultsBucket.bucketName,
        description: 'S3 bucket name for validation results',
      });
      new CfnOutput(stack, 'SchemaStorageBucketName', {
        value: schemaStorageBucket.bucketName,
        description: 'S3 bucket name for schema storage',
      });

      template = getTemplate(stack);

      // Verify outputs exist
      template.hasOutput('MetadataSchemasTableName', {
        Description: 'DynamoDB table name for metadata schemas',
      });

      template.hasOutput('MetadataUploadJobTableName', {
        Description: 'DynamoDB table name for metadata upload jobs',
      });

      template.hasOutput('ValidationResultsBucketName', {
        Description: 'S3 bucket name for validation results',
      });

      template.hasOutput('SchemaStorageBucketName', {
        Description: 'S3 bucket name for schema storage',
      });

      // Verify no RDS-related outputs
      const outputs = template.toJSON().Outputs || {};
      const outputKeys = Object.keys(outputs);

      expect(outputKeys).not.toContain('DBHost');
      expect(outputKeys).not.toContain('DBPort');
      expect(outputKeys).not.toContain('DBName');
      expect(outputKeys).not.toContain('DBSecretArn');
    });
  });

  describe('Resource Dependencies', () => {
    test('should create proper dependencies between resources', () => {
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Create dependencies
      metadataSchemasTable.grantReadWriteData(taskRole);
      validationResultsBucket.grantReadWrite(taskRole);

      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        taskRole: taskRole,
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      template = getTemplate(stack);

      // Verify that IAM policies reference the correct resources
      const policies = template.findResources('AWS::IAM::Policy');
      const policyValues = Object.values(policies);

      // Check that policies reference the DynamoDB table and S3 bucket
      const dynamoPolicy = policyValues.find((policy: any) =>
        policy.Properties.PolicyDocument.Statement.some((stmt: any) =>
          stmt.Action.some((action: string) => action.startsWith('dynamodb:'))
        )
      ) as any;

      const s3Policy = policyValues.find((policy: any) =>
        policy.Properties.PolicyDocument.Statement.some((stmt: any) =>
          stmt.Action.some((action: string) => action.startsWith('s3:'))
        )
      ) as any;

      expect(dynamoPolicy).toBeDefined();
      expect(s3Policy).toBeDefined();

      // Verify that task definition references the task role
      const taskDefs = template.findResources('AWS::ECS::TaskDefinition');
      const taskDef = Object.values(taskDefs)[0] as any;
      const taskRoleArn = taskDef.Properties.TaskRoleArn;
      expect(taskRoleArn).toBeDefined();
      expect(taskRoleArn['Fn::GetAtt']).toBeDefined();
      expect(taskRoleArn['Fn::GetAtt'][0]).toMatch(/TaskRole/);
      expect(taskRoleArn['Fn::GetAtt'][1]).toBe('Arn');
    });

    test('should handle resource deletion order correctly', () => {
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: config.removalPolicy === 'DESTROY' ?
          require('aws-cdk-lib').RemovalPolicy.DESTROY :
          require('aws-cdk-lib').RemovalPolicy.RETAIN,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        removalPolicy: config.removalPolicy === 'DESTROY' ?
          require('aws-cdk-lib').RemovalPolicy.DESTROY :
          require('aws-cdk-lib').RemovalPolicy.RETAIN,
        autoDeleteObjects: config.deploymentStage === 'dev',
      });

      template = getTemplate(stack);

      // Verify removal policies are set correctly
      if (config.removalPolicy === 'DESTROY') {
        template.hasResource('AWS::DynamoDB::Table', {
          DeletionPolicy: 'Delete'
        });

        template.hasResource('AWS::S3::Bucket', {
          DeletionPolicy: 'Delete'
        });
      }
    });
  });

  describe('Cross-Stack References', () => {
    test('should support cross-stack resource references', () => {
      // Create a separate stack for shared resources
      const sharedStack = new Stack(app, 'SharedStack', {
        env: { account: '123456789012', region: 'us-east-1' },
      });

      const sharedBucket = new s3.Bucket(sharedStack, 'SharedBucket', {
        bucketName: PhysicalName.GENERATE_IF_NEEDED,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      // Reference shared resource in main stack (same env for cross-stack refs)
      const mainStack = new Stack(app, 'MainStack', {
        env: { account: '123456789012', region: 'us-east-1' },
      });

      const taskDefinition = new ecs.FargateTaskDefinition(mainStack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        environment: {
          SHARED_BUCKET: sharedBucket.bucketName,
        },
      });

      const mainTemplate = getTemplate(mainStack);
      const sharedTemplate = getTemplate(sharedStack);

      // Verify shared resource exists
      sharedTemplate.resourceCountIs('AWS::S3::Bucket', 1);

      // Verify cross-stack reference in task definition
      const taskDefs = mainTemplate.findResources('AWS::ECS::TaskDefinition');
      const taskDef = Object.values(taskDefs)[0] as any;
      const environment = taskDef.Properties.ContainerDefinitions[0].Environment;
      const sharedBucketEnv = environment.find((e: any) => e.Name === 'SHARED_BUCKET');
      expect(sharedBucketEnv).toBeDefined();
      expect(sharedBucketEnv.Value).toBeDefined();
    });
  });

  describe('Environment-Specific Configuration', () => {
    test('should deploy with development environment settings', () => {
      const devConfig = createMockConfig({
        deploymentStage: 'dev',
        removalPolicy: 'DESTROY',
        logLevel: 'DEBUG'
      });

      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        tableName: `${devConfig.appName}-metadata-schemas-${devConfig.deploymentStage}`,
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: require('aws-cdk-lib').RemovalPolicy.DESTROY,
      });

      template = getTemplate(stack);

      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'metadata-harmonization-app-test-metadata-schemas-dev'
      });

      template.hasResource('AWS::DynamoDB::Table', {
        DeletionPolicy: 'Delete'
      });
    });

    test('should deploy with production environment settings', () => {
      const prodConfig = createMockConfig({
        deploymentStage: 'prod',
        removalPolicy: 'RETAIN',
        logLevel: 'INFO'
      });

      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        tableName: `${prodConfig.appName}-metadata-schemas-${prodConfig.deploymentStage}`,
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: require('aws-cdk-lib').RemovalPolicy.RETAIN,
        pointInTimeRecovery: true,
      });

      template = getTemplate(stack);

      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'metadata-harmonization-app-test-metadata-schemas-prod',
        PointInTimeRecoverySpecification: {
          PointInTimeRecoveryEnabled: true
        }
      });

      template.hasResource('AWS::DynamoDB::Table', {
        DeletionPolicy: 'Retain'
      });
    });
  });
});
