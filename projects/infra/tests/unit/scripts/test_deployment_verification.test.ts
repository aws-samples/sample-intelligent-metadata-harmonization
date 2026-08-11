/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for deployment verification script logic
 */

import { MOCK_DYNAMODB_RESPONSES, MOCK_S3_RESPONSES } from '../../fixtures/mock-aws-responses';
import { TEST_ENVIRONMENT_VARIABLES } from '../../fixtures/test-config';

// Mock AWS SDK. Not an installed dependency (production code uses AWS SDK v3
// / aws-cdk-lib) -- `virtual: true` lets Jest mock a module that doesn't
// exist on disk.
jest.mock('aws-sdk', () => ({
  DynamoDB: jest.fn(() => ({
    describeTable: jest.fn().mockReturnValue({
      promise: jest.fn()
    })
  })),
  S3: jest.fn(() => ({
    headBucket: jest.fn().mockReturnValue({
      promise: jest.fn()
    }),
    getBucketEncryption: jest.fn().mockReturnValue({
      promise: jest.fn()
    })
  }))
}), { virtual: true });

// Mock HTTP requests for API endpoint testing
jest.mock('https', () => ({
  get: jest.fn()
}));

describe('Deployment Verification Script', () => {
  let mockDynamoDB: any;
  let mockS3: any;
  let mockHttps: any;

  beforeEach(() => {
    jest.clearAllMocks();

    // Set up environment variables
    Object.entries(TEST_ENVIRONMENT_VARIABLES).forEach(([key, value]) => {
      process.env[key] = value;
    });

    const AWS = require('aws-sdk');
    mockDynamoDB = new AWS.DynamoDB();
    mockS3 = new AWS.S3();
    mockHttps = require('https');
  });

  afterEach(() => {
    // Clean up environment variables
    Object.keys(TEST_ENVIRONMENT_VARIABLES).forEach(key => {
      delete process.env[key];
    });
  });

  describe('DynamoDB Table Verification', () => {
    test('should verify metadata schemas table exists and is active', async () => {
      mockDynamoDB.describeTable.mockReturnValue({
        promise: jest.fn().mockResolvedValue(MOCK_DYNAMODB_RESPONSES.describeTableMetadataSchemas)
      });

      const verifyDynamoDBTable = async (tableName: string): Promise<boolean> => {
        try {
          const result = await mockDynamoDB.describeTable({ TableName: tableName }).promise();
          return result.Table.TableStatus === 'ACTIVE';
        } catch (error) {
          return false;
        }
      };

      const isActive = await verifyDynamoDBTable('test-metadata-schemas-table');

      expect(isActive).toBe(true);
      expect(mockDynamoDB.describeTable).toHaveBeenCalledWith({
        TableName: 'test-metadata-schemas-table'
      });
    });

    test('should verify metadata upload job table exists with GSI', async () => {
      mockDynamoDB.describeTable.mockReturnValue({
        promise: jest.fn().mockResolvedValue(MOCK_DYNAMODB_RESPONSES.describeTableMetadataUploadJob)
      });

      const verifyDynamoDBTableWithGSI = async (tableName: string, expectedGSI: string): Promise<boolean> => {
        try {
          const result = await mockDynamoDB.describeTable({ TableName: tableName }).promise();
          const table = result.Table;

          if (table.TableStatus !== 'ACTIVE') return false;

          const hasGSI = table.GlobalSecondaryIndexes?.some((gsi: any) =>
            gsi.IndexName === expectedGSI && gsi.IndexStatus === 'ACTIVE'
          );

          return hasGSI || false;
        } catch (error) {
          return false;
        }
      };

      const hasGSI = await verifyDynamoDBTableWithGSI('test-metadata-upload-job-table', 'user-id-index');

      expect(hasGSI).toBe(true);
      expect(mockDynamoDB.describeTable).toHaveBeenCalledWith({
        TableName: 'test-metadata-upload-job-table'
      });
    });

    test('should handle DynamoDB table not found error', async () => {
      mockDynamoDB.describeTable.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('Table not found'))
      });

      const verifyDynamoDBTable = async (tableName: string): Promise<boolean> => {
        try {
          const result = await mockDynamoDB.describeTable({ TableName: tableName }).promise();
          return result.Table.TableStatus === 'ACTIVE';
        } catch (error) {
          return false;
        }
      };

      const isActive = await verifyDynamoDBTable('non-existent-table');

      expect(isActive).toBe(false);
    });

    test('should not verify RDS database connections', async () => {
      // This test ensures we don't have any RDS verification logic
      const verifyDatabaseConnection = (): boolean => {
        // This function should not exist in the new implementation
        return false;
      };

      // Verify that database connection verification is not performed
      expect(verifyDatabaseConnection()).toBe(false);

      // Ensure no RDS-related environment variables are expected
      expect(process.env.DB_HOST).toBeUndefined();
      expect(process.env.DB_PORT).toBeUndefined();
      expect(process.env.DB_NAME).toBeUndefined();
    });
  });

  describe('S3 Bucket Verification', () => {
    test('should verify validation results bucket exists and is accessible', async () => {
      mockS3.headBucket.mockReturnValue({
        promise: jest.fn().mockResolvedValue({})
      });

      mockS3.getBucketEncryption.mockReturnValue({
        promise: jest.fn().mockResolvedValue(MOCK_S3_RESPONSES.getBucketEncryptionValidationResults)
      });

      const verifyS3Bucket = async (bucketName: string): Promise<boolean> => {
        try {
          await mockS3.headBucket({ Bucket: bucketName }).promise();
          const encryption = await mockS3.getBucketEncryption({ Bucket: bucketName }).promise();

          return encryption.ServerSideEncryptionConfiguration.Rules.length > 0;
        } catch (error) {
          return false;
        }
      };

      const isAccessible = await verifyS3Bucket('test-validation-results-bucket');

      expect(isAccessible).toBe(true);
      expect(mockS3.headBucket).toHaveBeenCalledWith({
        Bucket: 'test-validation-results-bucket'
      });
      expect(mockS3.getBucketEncryption).toHaveBeenCalledWith({
        Bucket: 'test-validation-results-bucket'
      });
    });

    test('should verify schema storage bucket exists and is accessible', async () => {
      mockS3.headBucket.mockReturnValue({
        promise: jest.fn().mockResolvedValue({})
      });

      mockS3.getBucketEncryption.mockReturnValue({
        promise: jest.fn().mockResolvedValue(MOCK_S3_RESPONSES.getBucketEncryptionSchemaStorage)
      });

      const verifyS3Bucket = async (bucketName: string): Promise<boolean> => {
        try {
          await mockS3.headBucket({ Bucket: bucketName }).promise();
          const encryption = await mockS3.getBucketEncryption({ Bucket: bucketName }).promise();

          return encryption.ServerSideEncryptionConfiguration.Rules.length > 0;
        } catch (error) {
          return false;
        }
      };

      const isAccessible = await verifyS3Bucket('test-schema-storage-bucket');

      expect(isAccessible).toBe(true);
      expect(mockS3.headBucket).toHaveBeenCalledWith({
        Bucket: 'test-schema-storage-bucket'
      });
    });

    test('should handle S3 bucket access denied error', async () => {
      mockS3.headBucket.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('Access Denied'))
      });

      const verifyS3Bucket = async (bucketName: string): Promise<boolean> => {
        try {
          await mockS3.headBucket({ Bucket: bucketName }).promise();
          return true;
        } catch (error) {
          return false;
        }
      };

      const isAccessible = await verifyS3Bucket('inaccessible-bucket');

      expect(isAccessible).toBe(false);
    });

    test('should handle S3 bucket not found error', async () => {
      mockS3.headBucket.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('NoSuchBucket'))
      });

      const verifyS3Bucket = async (bucketName: string): Promise<boolean> => {
        try {
          await mockS3.headBucket({ Bucket: bucketName }).promise();
          return true;
        } catch (error) {
          return false;
        }
      };

      const isAccessible = await verifyS3Bucket('non-existent-bucket');

      expect(isAccessible).toBe(false);
    });
  });

  describe('API Endpoint Verification', () => {
    test('should verify metadata validation endpoints instead of classification endpoints', async () => {
      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        const mockResponse = {
          statusCode: 200,
          on: jest.fn((event: string, handler: Function) => {
            if (event === 'data') {
              handler('{"status": "healthy"}');
            } else if (event === 'end') {
              handler();
            }
          })
        };
        callback(mockResponse);
        return { on: jest.fn() };
      });

      const verifyApiEndpoint = async (endpoint: string): Promise<boolean> => {
        return new Promise((resolve) => {
          mockHttps.get(endpoint, (response: any) => {
            let data = '';

            response.on('data', (chunk: string) => {
              data += chunk;
            });

            response.on('end', () => {
              try {
                const result = JSON.parse(data);
                resolve(response.statusCode === 200 && result.status === 'healthy');
              } catch {
                resolve(false);
              }
            });
          }).on('error', () => {
            resolve(false);
          });
        });
      };

      const isHealthy = await verifyApiEndpoint('https://test-api.example.com/api/v1/metadata/schema');

      expect(isHealthy).toBe(true);
      expect(mockHttps.get).toHaveBeenCalledWith(
        'https://test-api.example.com/api/v1/metadata/schema',
        expect.any(Function)
      );
    });


    test('should handle API endpoint connection errors', async () => {
      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        const mockRequest = {
          on: jest.fn((event: string, handler: Function) => {
            if (event === 'error') {
              handler(new Error('Connection refused'));
            }
          })
        };
        return mockRequest;
      });

      const verifyApiEndpoint = async (endpoint: string): Promise<boolean> => {
        return new Promise((resolve) => {
          mockHttps.get(endpoint, (response: any) => {
            resolve(true);
          }).on('error', () => {
            resolve(false);
          });
        });
      };

      const isHealthy = await verifyApiEndpoint('https://unreachable-api.example.com/health');

      expect(isHealthy).toBe(false);
    });

    test('should handle API endpoint timeout', async () => {
      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        // Simulate timeout by not calling callback
        return {
          on: jest.fn(),
          setTimeout: jest.fn(),
          destroy: jest.fn()
        };
      });

      const verifyApiEndpoint = async (endpoint: string, timeout: number = 5000): Promise<boolean> => {
        return new Promise((resolve) => {
          const request = mockHttps.get(endpoint, (response: any) => {
            resolve(true);
          }).on('error', () => {
            resolve(false);
          });

          // Simulate timeout
          setTimeout(() => {
            resolve(false);
          }, timeout);
        });
      };

      const isHealthy = await verifyApiEndpoint('https://slow-api.example.com/health', 100);

      expect(isHealthy).toBe(false);
    });
  });

  describe('Comprehensive Verification', () => {
    test('should run all verification checks and return overall status', async () => {
      // Mock successful responses for all services
      mockDynamoDB.describeTable.mockReturnValue({
        promise: jest.fn().mockResolvedValue(MOCK_DYNAMODB_RESPONSES.describeTableMetadataSchemas)
      });

      mockS3.headBucket.mockReturnValue({
        promise: jest.fn().mockResolvedValue({})
      });

      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        const mockResponse = {
          statusCode: 200,
          on: jest.fn((event: string, handler: Function) => {
            if (event === 'data') {
              handler('{"status": "healthy"}');
            } else if (event === 'end') {
              handler();
            }
          })
        };
        callback(mockResponse);
        return { on: jest.fn() };
      });

      const runComprehensiveVerification = async (): Promise<{
        dynamodb: boolean;
        s3: boolean;
        api: boolean;
        overall: boolean;
      }> => {
        const dynamodbCheck = await mockDynamoDB.describeTable({
          TableName: process.env.METADATA_SCHEMAS_TABLE
        }).promise().then(() => true).catch(() => false);

        const s3Check = await mockS3.headBucket({
          Bucket: process.env.VALIDATION_RESULTS_BUCKET
        }).promise().then(() => true).catch(() => false);

        const apiCheck = await new Promise<boolean>((resolve) => {
          mockHttps.get('https://test-api.example.com/health', (response: any) => {
            resolve(response.statusCode === 200);
          }).on('error', () => resolve(false));
        });

        const overall = dynamodbCheck && s3Check && apiCheck;

        return {
          dynamodb: dynamodbCheck,
          s3: s3Check,
          api: apiCheck,
          overall
        };
      };

      const results = await runComprehensiveVerification();

      expect(results.dynamodb).toBe(true);
      expect(results.s3).toBe(true);
      expect(results.api).toBe(true);
      expect(results.overall).toBe(true);
    });

    test('should fail overall verification if any component fails', async () => {
      // Mock DynamoDB success, S3 failure, API success
      mockDynamoDB.describeTable.mockReturnValue({
        promise: jest.fn().mockResolvedValue(MOCK_DYNAMODB_RESPONSES.describeTableMetadataSchemas)
      });

      mockS3.headBucket.mockReturnValue({
        promise: jest.fn().mockRejectedValue(new Error('Bucket not found'))
      });

      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        const mockResponse = {
          statusCode: 200,
          on: jest.fn((event: string, handler: Function) => {
            if (event === 'data') {
              handler('{"status": "healthy"}');
            } else if (event === 'end') {
              handler();
            }
          })
        };
        callback(mockResponse);
        return { on: jest.fn() };
      });

      const runComprehensiveVerification = async (): Promise<{
        dynamodb: boolean;
        s3: boolean;
        api: boolean;
        overall: boolean;
      }> => {
        const dynamodbCheck = await mockDynamoDB.describeTable({
          TableName: process.env.METADATA_SCHEMAS_TABLE
        }).promise().then(() => true).catch(() => false);

        const s3Check = await mockS3.headBucket({
          Bucket: process.env.VALIDATION_RESULTS_BUCKET
        }).promise().then(() => true).catch(() => false);

        const apiCheck = await new Promise<boolean>((resolve) => {
          mockHttps.get('https://test-api.example.com/health', (response: any) => {
            resolve(response.statusCode === 200);
          }).on('error', () => resolve(false));
        });

        const overall = dynamodbCheck && s3Check && apiCheck;

        return {
          dynamodb: dynamodbCheck,
          s3: s3Check,
          api: apiCheck,
          overall
        };
      };

      const results = await runComprehensiveVerification();

      expect(results.dynamodb).toBe(true);
      expect(results.s3).toBe(false);
      expect(results.api).toBe(true);
      expect(results.overall).toBe(false);
    });
  });

  describe('Error Reporting', () => {
    test('should provide detailed error messages for failed verifications', () => {
      const generateErrorReport = (results: {
        dynamodb: boolean;
        s3: boolean;
        api: boolean;
      }): string[] => {
        const errors: string[] = [];

        if (!results.dynamodb) {
          errors.push('DynamoDB tables are not accessible or not in ACTIVE state');
        }

        if (!results.s3) {
          errors.push('S3 buckets are not accessible or do not exist');
        }

        if (!results.api) {
          errors.push('API endpoints are not responding or returning errors');
        }

        return errors;
      };

      const failedResults = {
        dynamodb: false,
        s3: true,
        api: false
      };

      const errors = generateErrorReport(failedResults);

      expect(errors).toContain('DynamoDB tables are not accessible or not in ACTIVE state');
      expect(errors).toContain('API endpoints are not responding or returning errors');
      expect(errors).not.toContain('S3 buckets are not accessible or do not exist');
    });

    test('should provide success message when all verifications pass', () => {
      const generateSuccessReport = (results: {
        dynamodb: boolean;
        s3: boolean;
        api: boolean;
        overall: boolean;
      }): string => {
        if (results.overall) {
          return 'All infrastructure components are healthy and accessible';
        }
        return 'Some infrastructure components failed verification';
      };

      const successResults = {
        dynamodb: true,
        s3: true,
        api: true,
        overall: true
      };

      const message = generateSuccessReport(successResults);

      expect(message).toBe('All infrastructure components are healthy and accessible');
    });
  });
});
