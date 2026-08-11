/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Jest setup file for infrastructure tests
 */

// Mock AWS SDK v2. Not an installed dependency (production code uses AWS SDK
// v3 / aws-cdk-lib) -- `virtual: true` lets Jest mock a module that doesn't
// exist on disk.
jest.mock('aws-sdk', () => ({
  CloudFormation: jest.fn(() => ({
    describeStacks: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({
        Stacks: [{
          Outputs: [
            { OutputKey: 'MetadataSchemasTableName', OutputValue: 'test-metadata-schemas-table' },
            { OutputKey: 'MetadataUploadJobTableName', OutputValue: 'test-metadata-upload-job-table' },
            { OutputKey: 'ValidationResultsBucketName', OutputValue: 'test-validation-results-bucket' },
            { OutputKey: 'SchemaStorageBucketName', OutputValue: 'test-schema-storage-bucket' }
          ]
        }]
      })
    })
  })),
  DynamoDB: jest.fn(() => ({
    describeTable: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({
        Table: {
          TableName: 'test-table',
          TableStatus: 'ACTIVE'
        }
      })
    })
  })),
  S3: jest.fn(() => ({
    headBucket: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({})
    }),
    getBucketEncryption: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({
        ServerSideEncryptionConfiguration: {
          Rules: [{ ApplyServerSideEncryptionByDefault: { SSEAlgorithm: 'AES256' } }]
        }
      })
    })
  }))
}), { virtual: true });

// Set up test environment variables
process.env.AWS_REGION = 'us-east-1';
process.env.AWS_ACCOUNT_ID = '123456789012';
process.env.NODE_ENV = 'test';

// Global test timeout
jest.setTimeout(30000);
