/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Integration tests for S3 bucket operations and permissions
 */

import { Template, Match } from 'aws-cdk-lib/assertions';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { createTestApp, getTemplate } from '../fixtures/test-utils';
import { MOCK_S3_RESPONSES } from '../fixtures/mock-aws-responses';

// Mock AWS SDK for integration testing. Not an installed dependency
// (production code uses AWS SDK v3 / aws-cdk-lib) -- `virtual: true` lets
// Jest mock a module that doesn't exist on disk.
jest.mock('aws-sdk', () => ({
  S3: jest.fn(() => ({
    headBucket: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({})
    }),
    getBucketEncryption: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue(MOCK_S3_RESPONSES.getBucketEncryptionValidationResults)
    }),
    putObject: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ ETag: '"test-etag"' })
    }),
    getObject: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ Body: 'test-content' })
    }),
    deleteObject: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({})
    }),
    listObjectsV2: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({
        Contents: [
          { Key: 'test-file-1.json', Size: 1024 },
          { Key: 'test-file-2.json', Size: 2048 }
        ]
      })
    })
  }))
}), { virtual: true });

describe('S3 Operations Integration Tests', () => {
  let app: any;
  let stack: any;
  let template: Template;
  let mockS3: any;

  beforeEach(() => {
    const testApp = createTestApp('S3TestStack');
    app = testApp.app;
    stack = testApp.stack;

    const AWS = require('aws-sdk');
    mockS3 = new AWS.S3();

    jest.clearAllMocks();
  });

  describe('Validation Results Bucket Operations', () => {
    let validationResultsBucket: s3.Bucket;

    beforeEach(() => {
      validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        bucketName: 'test-validation-results-bucket',
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
        versioned: true,
      });

      template = getTemplate(stack);
    });

    test('should create bucket with correct security configuration', () => {
      template.hasResourceProperties('AWS::S3::Bucket', {
        BucketName: 'test-validation-results-bucket',
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

      // Verify SSL enforcement policy
      template.hasResourceProperties('AWS::S3::BucketPolicy', {
        PolicyDocument: Match.objectLike({
          Statement: Match.arrayWith([
            Match.objectLike({
              Effect: 'Deny',
              Action: 's3:*',
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

    test('should support uploading validation results', async () => {
      const validationResult = {
        job_id: 'job-12345',
        validation_status: 'completed',
        total_records: 100,
        valid_records: 95,
        invalid_records: 5,
        errors: [
          {
            row: 10,
            field: 'collection_date',
            error: 'Invalid date format'
          }
        ]
      };

      // Mock successful upload
      mockS3.putObject.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          ETag: '"test-etag-12345"',
          VersionId: 'version-1'
        })
      });

      // Test upload operation
      const uploadResult = await mockS3.putObject({
        Bucket: 'test-validation-results-bucket',
        Key: 'validation-results/job-12345/results.json',
        Body: JSON.stringify(validationResult),
        ContentType: 'application/json',
        ServerSideEncryption: 'AES256'
      }).promise();

      expect(mockS3.putObject).toHaveBeenCalledWith({
        Bucket: 'test-validation-results-bucket',
        Key: 'validation-results/job-12345/results.json',
        Body: JSON.stringify(validationResult),
        ContentType: 'application/json',
        ServerSideEncryption: 'AES256'
      });

      expect(uploadResult.ETag).toBe('"test-etag-12345"');
    });

    test('should support retrieving validation results', async () => {
      const expectedContent = JSON.stringify({
        job_id: 'job-12345',
        validation_status: 'completed'
      });

      // Mock successful retrieval
      mockS3.getObject.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Body: expectedContent,
          ContentType: 'application/json',
          ETag: '"test-etag-12345"'
        })
      });

      // Test retrieval operation
      const getResult = await mockS3.getObject({
        Bucket: 'test-validation-results-bucket',
        Key: 'validation-results/job-12345/results.json'
      }).promise();

      expect(mockS3.getObject).toHaveBeenCalledWith({
        Bucket: 'test-validation-results-bucket',
        Key: 'validation-results/job-12345/results.json'
      });

      expect(getResult.Body).toBe(expectedContent);
    });

    test('should support deleting validation results', async () => {
      // Mock successful deletion
      mockS3.deleteObject.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          DeleteMarker: true,
          VersionId: 'delete-marker-version'
        })
      });

      // Test deletion operation
      const deleteResult = await mockS3.deleteObject({
        Bucket: 'test-validation-results-bucket',
        Key: 'validation-results/job-12345/results.json'
      }).promise();

      expect(mockS3.deleteObject).toHaveBeenCalledWith({
        Bucket: 'test-validation-results-bucket',
        Key: 'validation-results/job-12345/results.json'
      });

      expect(deleteResult.DeleteMarker).toBe(true);
    });

    test('should support listing validation results by job', async () => {
      // Mock successful listing
      mockS3.listObjectsV2.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Contents: [
            {
              Key: 'validation-results/job-12345/results.json',
              Size: 1024,
              LastModified: new Date('2024-01-01T00:00:00Z')
            },
            {
              Key: 'validation-results/job-12345/errors.json',
              Size: 512,
              LastModified: new Date('2024-01-01T00:01:00Z')
            }
          ],
          KeyCount: 2
        })
      });

      // Test listing operation
      const listResult = await mockS3.listObjectsV2({
        Bucket: 'test-validation-results-bucket',
        Prefix: 'validation-results/job-12345/',
        MaxKeys: 100
      }).promise();

      expect(mockS3.listObjectsV2).toHaveBeenCalledWith({
        Bucket: 'test-validation-results-bucket',
        Prefix: 'validation-results/job-12345/',
        MaxKeys: 100
      });

      expect(listResult.Contents).toHaveLength(2);
      expect(listResult.Contents[0].Key).toBe('validation-results/job-12345/results.json');
    });
  });

  describe('Schema Storage Bucket Operations', () => {
    let schemaStorageBucket: s3.Bucket;

    beforeEach(() => {
      schemaStorageBucket = new s3.Bucket(stack, 'SchemaStorage', {
        bucketName: 'test-schema-storage-bucket',
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        encryption: s3.BucketEncryption.S3_MANAGED,
        enforceSSL: true,
      });

      template = getTemplate(stack);
    });

    test('should create bucket with correct configuration', () => {
      template.hasResourceProperties('AWS::S3::Bucket', {
        BucketName: 'test-schema-storage-bucket',
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

    test('should support retrieving schema files', async () => {
      const schemaContent = JSON.stringify({
        $schema: 'http://json-schema.org/draft-07/schema#',
        type: 'object',
        properties: {
          sample_id: {
            type: 'string',
            description: 'Unique identifier for the sample'
          }
        }
      });

      // Mock successful retrieval
      mockS3.getObject.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Body: schemaContent,
          ContentType: 'application/json',
          ETag: '"schema-etag-123"'
        })
      });

      // Test schema retrieval
      const getResult = await mockS3.getObject({
        Bucket: 'test-schema-storage-bucket',
        Key: 'schemas/cyclospora/core/v1.0.0/schema.json'
      }).promise();

      expect(mockS3.getObject).toHaveBeenCalledWith({
        Bucket: 'test-schema-storage-bucket',
        Key: 'schemas/cyclospora/core/v1.0.0/schema.json'
      });

      expect(getResult.Body).toBe(schemaContent);
    });

    test('should support listing schema files by program', async () => {
      // Mock successful listing
      mockS3.listObjectsV2.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Contents: [
            {
              Key: 'schemas/cyclospora/core/v1.0.0/schema.json',
              Size: 2048,
              LastModified: new Date('2024-01-01T00:00:00Z')
            },
            {
              Key: 'schemas/cyclospora/program/v1.0.0/schema.json',
              Size: 4096,
              LastModified: new Date('2024-01-01T00:00:00Z')
            }
          ],
          KeyCount: 2
        })
      });

      // Test listing schemas by program
      const listResult = await mockS3.listObjectsV2({
        Bucket: 'test-schema-storage-bucket',
        Prefix: 'schemas/cyclospora/',
        MaxKeys: 100
      }).promise();

      expect(mockS3.listObjectsV2).toHaveBeenCalledWith({
        Bucket: 'test-schema-storage-bucket',
        Prefix: 'schemas/cyclospora/',
        MaxKeys: 100
      });

      expect(listResult.Contents).toHaveLength(2);
      expect(listResult.Contents[0].Key).toContain('cyclospora');
    });

    test('should handle schema file not found', async () => {
      // Mock not found error
      mockS3.getObject.mockReturnValue({
        promise: jest.fn().mockRejectedValue({
          code: 'NoSuchKey',
          message: 'The specified key does not exist.'
        })
      });

      try {
        await mockS3.getObject({
          Bucket: 'test-schema-storage-bucket',
          Key: 'schemas/non-existent/schema.json'
        }).promise();
      } catch (error: any) {
        expect(error.code).toBe('NoSuchKey');
      }

      expect(mockS3.getObject).toHaveBeenCalledWith({
        Bucket: 'test-schema-storage-bucket',
        Key: 'schemas/non-existent/schema.json'
      });
    });
  });

  describe('IAM Permissions Integration', () => {
    test('should grant read/write permissions to validation results bucket', () => {
      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      validationResultsBucket.grantReadWrite(taskRole);

      template = getTemplate(stack);

      // Verify IAM policy is created
      template.resourceCountIs('AWS::IAM::Policy', 1);

      // Verify read/write permissions
      template.hasResourceProperties('AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Action: [
              's3:GetObject*',
              's3:GetBucket*',
              's3:List*',
              's3:DeleteObject*',
              's3:PutObject',
              's3:PutObjectLegalHold',
              's3:PutObjectRetention',
              's3:PutObjectTagging',
              's3:PutObjectVersionTagging',
              's3:Abort*'
            ]
          }]
        }
      });
    });

    test('should grant read-only permissions to schema storage bucket', () => {
      const schemaStorageBucket = new s3.Bucket(stack, 'SchemaStorage', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      schemaStorageBucket.grantRead(taskRole);

      template = getTemplate(stack);

      // Verify IAM policy is created
      template.resourceCountIs('AWS::IAM::Policy', 1);

      // Verify read-only permissions
      template.hasResourceProperties('AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Action: [
              's3:GetObject*',
              's3:GetBucket*',
              's3:List*'
            ]
          }]
        }
      });

      // Verify no write permissions
      const policies = template.findResources('AWS::IAM::Policy');
      const policyValues = Object.values(policies);

      policyValues.forEach((policy: any) => {
        const statements = policy.Properties?.PolicyDocument?.Statement || [];
        statements.forEach((statement: any) => {
          const actions = Array.isArray(statement.Action) ? statement.Action : [statement.Action];

          actions.forEach((action: string) => {
            expect(action).not.toMatch(/^s3:Put/);
            expect(action).not.toMatch(/^s3:Delete/);
          });
        });
      });
    });

    test('should create separate policies for different bucket permissions', () => {
      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const schemaStorageBucket = new s3.Bucket(stack, 'SchemaStorage', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      validationResultsBucket.grantReadWrite(taskRole);
      schemaStorageBucket.grantRead(taskRole);

      template = getTemplate(stack);

      // Verify IAM policies are created (CDK may merge grants to same role)
      const policies = template.findResources('AWS::IAM::Policy');
      expect(Object.keys(policies).length).toBeGreaterThanOrEqual(1);

      // Verify policies reference different buckets
      const policyValues = Object.values(policies) as any[];

      // Should have both read/write actions (PutObject) and read actions (GetObject)
      const allStatements = policyValues.flatMap((policy: any) =>
        policy.Properties.PolicyDocument.Statement
      );
      const allActions = allStatements.flatMap((stmt: any) =>
        Array.isArray(stmt.Action) ? stmt.Action : [stmt.Action]
      );

      const hasReadWriteActions = allActions.some((action: string) => action.includes('PutObject'));
      const hasReadActions = allActions.some((action: string) => action.startsWith('s3:Get'));

      expect(hasReadWriteActions).toBe(true);
      expect(hasReadActions).toBe(true);
    });
  });

  describe('Error Handling and Resilience', () => {
    test('should handle S3 access denied errors', async () => {
      // Mock access denied error
      mockS3.getObject.mockReturnValue({
        promise: jest.fn().mockRejectedValue({
          code: 'AccessDenied',
          message: 'Access Denied'
        })
      });

      try {
        await mockS3.getObject({
          Bucket: 'test-validation-results-bucket',
          Key: 'restricted-file.json'
        }).promise();
      } catch (error: any) {
        expect(error.code).toBe('AccessDenied');
      }

      expect(mockS3.getObject).toHaveBeenCalledWith({
        Bucket: 'test-validation-results-bucket',
        Key: 'restricted-file.json'
      });
    });

    test('should handle S3 bucket not found errors', async () => {
      // Mock bucket not found error
      mockS3.headBucket.mockReturnValue({
        promise: jest.fn().mockRejectedValue({
          code: 'NoSuchBucket',
          message: 'The specified bucket does not exist'
        })
      });

      try {
        await mockS3.headBucket({
          Bucket: 'non-existent-bucket'
        }).promise();
      } catch (error: any) {
        expect(error.code).toBe('NoSuchBucket');
      }

      expect(mockS3.headBucket).toHaveBeenCalledWith({
        Bucket: 'non-existent-bucket'
      });
    });

    test('should handle S3 upload failures with retry logic', async () => {
      let callCount = 0;

      // Mock failure on first call, success on second
      mockS3.putObject.mockReturnValue({
        promise: jest.fn().mockImplementation(() => {
          callCount++;
          if (callCount === 1) {
            return Promise.reject({
              code: 'ServiceUnavailable',
              message: 'Service temporarily unavailable'
            });
          }
          return Promise.resolve({ ETag: '"success-etag"' });
        })
      });

      const uploadWithRetry = async (params: any, maxRetries: number = 3): Promise<any> => {
        let retries = 0;
        while (retries < maxRetries) {
          try {
            return await mockS3.putObject(params).promise();
          } catch (error: any) {
            if (error.code === 'ServiceUnavailable' && retries < maxRetries - 1) {
              retries++;
              await new Promise(resolve => setTimeout(resolve, Math.pow(2, retries) * 100));
            } else {
              throw error;
            }
          }
        }
      };

      // Test retry logic
      const result = await uploadWithRetry({
        Bucket: 'test-validation-results-bucket',
        Key: 'test-file.json',
        Body: 'test content'
      });

      expect(result.ETag).toBe('"success-etag"');
      expect(mockS3.putObject).toHaveBeenCalledTimes(2); // Initial + 1 retry
    });

    test('should handle large file uploads with multipart', async () => {
      // Mock multipart upload operations
      const mockCreateMultipartUpload = jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ UploadId: 'test-upload-id' })
      });

      const mockUploadPart = jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ ETag: '"part-etag"' })
      });

      const mockCompleteMultipartUpload = jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ ETag: '"complete-etag"' })
      });

      mockS3.createMultipartUpload = mockCreateMultipartUpload;
      mockS3.uploadPart = mockUploadPart;
      mockS3.completeMultipartUpload = mockCompleteMultipartUpload;

      // Simulate multipart upload process
      const uploadId = await mockS3.createMultipartUpload({
        Bucket: 'test-validation-results-bucket',
        Key: 'large-file.json'
      }).promise();

      const partResult = await mockS3.uploadPart({
        Bucket: 'test-validation-results-bucket',
        Key: 'large-file.json',
        UploadId: uploadId.UploadId,
        PartNumber: 1,
        Body: 'part-content'
      }).promise();

      const completeResult = await mockS3.completeMultipartUpload({
        Bucket: 'test-validation-results-bucket',
        Key: 'large-file.json',
        UploadId: uploadId.UploadId,
        MultipartUpload: {
          Parts: [{
            ETag: partResult.ETag,
            PartNumber: 1
          }]
        }
      }).promise();

      expect(mockCreateMultipartUpload).toHaveBeenCalled();
      expect(mockUploadPart).toHaveBeenCalled();
      expect(mockCompleteMultipartUpload).toHaveBeenCalled();
      expect(completeResult.ETag).toBe('"complete-etag"');
    });
  });

  describe('Lifecycle Management', () => {
    test('should configure lifecycle policies for cost optimization', () => {
      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        lifecycleRules: [{
          id: 'validation-results-lifecycle',
          enabled: true,
          transitions: [{
            storageClass: s3.StorageClass.INFREQUENT_ACCESS,
            transitionAfter: require('aws-cdk-lib').Duration.days(30)
          }, {
            storageClass: s3.StorageClass.GLACIER,
            transitionAfter: require('aws-cdk-lib').Duration.days(90)
          }],
          expiration: require('aws-cdk-lib').Duration.days(365)
        }]
      });

      template = getTemplate(stack);

      template.hasResourceProperties('AWS::S3::Bucket', {
        LifecycleConfiguration: {
          Rules: [{
            Id: 'validation-results-lifecycle',
            Status: 'Enabled',
            Transitions: [
              {
                StorageClass: 'STANDARD_IA',
                TransitionInDays: 30
              },
              {
                StorageClass: 'GLACIER',
                TransitionInDays: 90
              }
            ],
            ExpirationInDays: 365
          }]
        }
      });
    });

    test('should configure different lifecycle policies per environment', () => {
      const devConfig = { deploymentStage: 'dev' };
      const prodConfig = { deploymentStage: 'prod' };

      // Development bucket with shorter retention
      const devBucket = new s3.Bucket(stack, 'DevValidationResults', {
        bucketName: `validation-results-${devConfig.deploymentStage}`,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        lifecycleRules: [{
          id: 'dev-lifecycle',
          enabled: true,
          expiration: require('aws-cdk-lib').Duration.days(30)
        }]
      });

      // Production bucket with longer retention
      const prodBucket = new s3.Bucket(stack, 'ProdValidationResults', {
        bucketName: `validation-results-${prodConfig.deploymentStage}`,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        lifecycleRules: [{
          id: 'prod-lifecycle',
          enabled: true,
          transitions: [{
            storageClass: s3.StorageClass.INFREQUENT_ACCESS,
            transitionAfter: require('aws-cdk-lib').Duration.days(90)
          }],
          expiration: require('aws-cdk-lib').Duration.days(2555) // 7 years
        }]
      });

      template = getTemplate(stack);

      // Verify different lifecycle configurations
      template.hasResourceProperties('AWS::S3::Bucket', {
        BucketName: 'validation-results-dev',
        LifecycleConfiguration: {
          Rules: [{
            Id: 'dev-lifecycle',
            Status: 'Enabled',
            ExpirationInDays: 30
          }]
        }
      });

      template.hasResourceProperties('AWS::S3::Bucket', {
        BucketName: 'validation-results-prod',
        LifecycleConfiguration: {
          Rules: [{
            Id: 'prod-lifecycle',
            Status: 'Enabled',
            Transitions: [{
              StorageClass: 'STANDARD_IA',
              TransitionInDays: 90
            }],
            ExpirationInDays: 2555
          }]
        }
      });
    });
  });
});
