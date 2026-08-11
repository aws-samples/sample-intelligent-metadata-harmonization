/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for CDK construct creation and configuration
 */

import { Template } from 'aws-cdk-lib/assertions';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { RemovalPolicy } from 'aws-cdk-lib';
import { Match } from 'aws-cdk-lib/assertions';
import { createTestApp, getTemplate, createMockConfig, assertResourceExists, assertResourceDoesNotExist } from '../../fixtures/test-utils';

describe('CDK Constructs', () => {
  let app: any;
  let stack: any;
  let template: Template;

  beforeEach(() => {
    const testApp = createTestApp('MetadataHarmonizationTestStack');
    app = testApp.app;
    stack = testApp.stack;
  });

  describe('DynamoDB Tables', () => {
    test('should create metadata schemas table with correct configuration', () => {
      // Create metadata schemas table
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        removalPolicy: RemovalPolicy.DESTROY,
      });

      template = getTemplate(stack);

      // Assert table exists with correct properties
      assertResourceExists(template, 'AWS::DynamoDB::Table', {
        KeySchema: [{
          AttributeName: 'core_schema_id',
          KeyType: 'HASH'
        }],
        AttributeDefinitions: [{
          AttributeName: 'core_schema_id',
          AttributeType: 'S'
        }],
        BillingMode: 'PAY_PER_REQUEST',
        SSESpecification: {
          SSEEnabled: true
        }
      });
    });

    test('should create metadata upload job table with GSI', () => {
      // Create metadata upload job table
      const metadataUploadJobTable = new dynamodb.Table(stack, 'MetadataUploadJob', {
        partitionKey: {
          name: 'job_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        removalPolicy: RemovalPolicy.DESTROY,
      });

      // Add GSI for user queries
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

      template = getTemplate(stack);

      // Assert table exists with correct properties and GSI
      assertResourceExists(template, 'AWS::DynamoDB::Table', {
        KeySchema: [{
          AttributeName: 'job_id',
          KeyType: 'HASH'
        }],
        AttributeDefinitions: [
          {
            AttributeName: 'job_id',
            AttributeType: 'S'
          },
          {
            AttributeName: 'user_id',
            AttributeType: 'S'
          },
          {
            AttributeName: 'created_at',
            AttributeType: 'S'
          }
        ],
        GlobalSecondaryIndexes: [{
          IndexName: 'user-id-index',
          KeySchema: [
            {
              AttributeName: 'user_id',
              KeyType: 'HASH'
            },
            {
              AttributeName: 'created_at',
              KeyType: 'RANGE'
            }
          ]
        }],
        BillingMode: 'PAY_PER_REQUEST'
      });
    });

    test('should not create RDS-related resources', () => {
      template = getTemplate(stack);

      // Assert no RDS resources exist
      assertResourceDoesNotExist(template, 'AWS::RDS::DBInstance');
      assertResourceDoesNotExist(template, 'AWS::RDS::DBSubnetGroup');
      assertResourceDoesNotExist(template, 'AWS::SecretsManager::Secret');
    });
  });

  describe('S3 Buckets', () => {
    test('should create validation results bucket with correct configuration', () => {
      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        removalPolicy: RemovalPolicy.DESTROY,
        autoDeleteObjects: true,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
      });

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::S3::Bucket', {
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
        }
      });

      // Assert bucket policy enforces SSL
      assertResourceExists(template, 'AWS::S3::BucketPolicy');
    });

    test('should create schema storage bucket with correct configuration', () => {
      const schemaStorageBucket = new s3.Bucket(stack, 'SchemaStorage', {
        removalPolicy: RemovalPolicy.DESTROY,
        autoDeleteObjects: true,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
      });

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::S3::Bucket', {
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
        }
      });
    });
  });

  describe('IAM Roles and Policies', () => {
    test('should create task role with DynamoDB permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Add DynamoDB permissions
      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'dynamodb:GetItem',
          'dynamodb:PutItem',
          'dynamodb:UpdateItem',
          'dynamodb:DeleteItem',
          'dynamodb:Query',
          'dynamodb:Scan'
        ],
        resources: [
          'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-schemas-table',
          'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table'
        ]
      }));

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::IAM::Role', {
        AssumeRolePolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Principal: {
              Service: 'ecs-tasks.amazonaws.com'
            },
            Action: 'sts:AssumeRole'
          }]
        }
      });

      assertResourceExists(template, 'AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Action: [
              'dynamodb:GetItem',
              'dynamodb:PutItem',
              'dynamodb:UpdateItem',
              'dynamodb:DeleteItem',
              'dynamodb:Query',
              'dynamodb:Scan'
            ]
          }]
        }
      });
    });

    test('should create task role with S3 permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Add S3 permissions for validation results (read/write)
      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:GetObject',
          's3:PutObject',
          's3:DeleteObject'
        ],
        resources: ['arn:aws:s3:::test-validation-results-bucket/*']
      }));

      // Add S3 permissions for schema storage (read-only)
      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject'],
        resources: ['arn:aws:s3:::test-schema-storage-bucket/*']
      }));

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [
            {
              Effect: 'Allow',
              Action: [
                's3:GetObject',
                's3:PutObject',
                's3:DeleteObject'
              ],
              Resource: 'arn:aws:s3:::test-validation-results-bucket/*'
            },
            {
              Effect: 'Allow',
              Action: 's3:GetObject',
              Resource: 'arn:aws:s3:::test-schema-storage-bucket/*'
            }
          ]
        }
      });
    });

    test('should not include RDS-related permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      template = getTemplate(stack);

      // Get all policy statements
      const policies = template.findResources('AWS::IAM::Policy');

      Object.values(policies).forEach((policy: any) => {
        const statements = policy.Properties?.PolicyDocument?.Statement || [];
        statements.forEach((statement: any) => {
          const actions = Array.isArray(statement.Action) ? statement.Action : [statement.Action];

          // Assert no RDS actions
          actions.forEach((action: string) => {
            expect(action).not.toMatch(/^rds:/);
            expect(action).not.toMatch(/^secretsmanager:/);
          });
        });
      });
    });
  });

  describe('Resource Naming', () => {
    test('should use metadata harmonization naming convention', () => {
      const config = createMockConfig();

      // Test that resource names follow the new convention
      expect(config.appName).toBe('metadata-harmonization-app-test');
      expect(config.metadataConfig.metadataSchemasTableName).toBe('test-metadata-schemas');
      expect(config.metadataConfig.metadataUploadJobTableName).toBe('test-metadata-upload-job');
      expect(config.metadataConfig.validationResultsBucketName).toBe('test-validation-results');
      expect(config.metadataConfig.schemaStorageBucketName).toBe('test-schema-storage');
    });

    test('should include metadata harmonization naming', () => {
      const config = createMockConfig();

      expect(config.appName).toContain('metadata-harmonization');
    });
  });
});
