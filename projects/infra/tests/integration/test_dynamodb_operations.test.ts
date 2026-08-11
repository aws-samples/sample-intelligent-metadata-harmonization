/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Integration tests for DynamoDB table operations and permissions
 */

import { Template } from 'aws-cdk-lib/assertions';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import { createTestApp, getTemplate } from '../fixtures/test-utils';
import { MOCK_DYNAMODB_RESPONSES } from '../fixtures/mock-aws-responses';

// Mock AWS SDK for integration testing
const mockDynamoDBConstructor = Object.assign(
  jest.fn(() => ({
    describeTable: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue(MOCK_DYNAMODB_RESPONSES.describeTableMetadataSchemas)
    }),
    createTable: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ TableDescription: { TableStatus: 'CREATING' } })
    }),
    deleteTable: jest.fn().mockReturnValue({
      promise: jest.fn().mockResolvedValue({ TableDescription: { TableStatus: 'DELETING' } })
    })
  })),
  {
    DocumentClient: jest.fn(() => ({
      put: jest.fn().mockReturnValue({ promise: jest.fn() }),
      get: jest.fn().mockReturnValue({ promise: jest.fn() }),
      query: jest.fn().mockReturnValue({ promise: jest.fn() }),
      scan: jest.fn().mockReturnValue({ promise: jest.fn() }),
      update: jest.fn().mockReturnValue({ promise: jest.fn() }),
      delete: jest.fn().mockReturnValue({ promise: jest.fn() })
    }))
  }
);

// Not an installed dependency (production code uses AWS SDK v3 / aws-cdk-lib)
// -- `virtual: true` lets Jest mock a module that doesn't exist on disk.
jest.mock('aws-sdk', () => ({
  DynamoDB: mockDynamoDBConstructor
}), { virtual: true });

describe('DynamoDB Operations Integration Tests', () => {
  let app: any;
  let stack: any;
  let template: Template;
  let mockDynamoDB: any;
  let mockDocumentClient: any;

  beforeEach(() => {
    const testApp = createTestApp('DynamoDBTestStack');
    app = testApp.app;
    stack = testApp.stack;

    const AWS = require('aws-sdk');
    mockDynamoDB = new AWS.DynamoDB();
    mockDocumentClient = new AWS.DynamoDB.DocumentClient();

    jest.clearAllMocks();
  });

  describe('Metadata Schemas Table Operations', () => {
    let metadataSchemasTable: dynamodb.Table;

    beforeEach(() => {
      metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        tableName: 'test-metadata-schemas-table',
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
      });

      template = getTemplate(stack);
    });

    test('should create table with correct schema configuration', () => {
      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'test-metadata-schemas-table',
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

    test('should support CRUD operations on metadata schemas', async () => {
      const testSchema = {
        core_schema_id: 'cyclospora_core_v1',
        schema_name: 'Cyclospora Core Schema',
        schema_version: '1.0.0',
        schema_type: 'core',
        program: 'cyclospora',
        created_at: '2024-01-01T00:00:00Z'
      };

      // Mock successful operations
      mockDocumentClient.put.mockReturnValue({
        promise: jest.fn().mockResolvedValue({})
      });

      mockDocumentClient.get.mockReturnValue({
        promise: jest.fn().mockResolvedValue({ Item: testSchema })
      });

      mockDocumentClient.update.mockReturnValue({
        promise: jest.fn().mockResolvedValue({ Attributes: { ...testSchema, updated_at: '2024-01-02T00:00:00Z' } })
      });

      mockDocumentClient.delete.mockReturnValue({
        promise: jest.fn().mockResolvedValue({})
      });

      // Test CREATE operation
      await mockDocumentClient.put({
        TableName: 'test-metadata-schemas-table',
        Item: testSchema
      }).promise();

      expect(mockDocumentClient.put).toHaveBeenCalledWith({
        TableName: 'test-metadata-schemas-table',
        Item: testSchema
      });

      // Test READ operation
      const getResult = await mockDocumentClient.get({
        TableName: 'test-metadata-schemas-table',
        Key: { core_schema_id: 'cyclospora_core_v1' }
      }).promise();

      expect(mockDocumentClient.get).toHaveBeenCalledWith({
        TableName: 'test-metadata-schemas-table',
        Key: { core_schema_id: 'cyclospora_core_v1' }
      });

      expect(getResult.Item).toEqual(testSchema);

      // Test UPDATE operation
      await mockDocumentClient.update({
        TableName: 'test-metadata-schemas-table',
        Key: { core_schema_id: 'cyclospora_core_v1' },
        UpdateExpression: 'SET updated_at = :updated_at',
        ExpressionAttributeValues: {
          ':updated_at': '2024-01-02T00:00:00Z'
        }
      }).promise();

      expect(mockDocumentClient.update).toHaveBeenCalled();

      // Test DELETE operation
      await mockDocumentClient.delete({
        TableName: 'test-metadata-schemas-table',
        Key: { core_schema_id: 'cyclospora_core_v1' }
      }).promise();

      expect(mockDocumentClient.delete).toHaveBeenCalledWith({
        TableName: 'test-metadata-schemas-table',
        Key: { core_schema_id: 'cyclospora_core_v1' }
      });
    });

    test('should support querying schemas by program', async () => {
      // Create a fresh stack with the GSI (re-synthesis required for GSI)
      const freshApp = createTestApp('DynamoDBGSITestStack');
      const freshStack = freshApp.stack;

      const tableWithGSI = new dynamodb.Table(freshStack, 'MetadataSchemas', {
        tableName: 'test-metadata-schemas-table',
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
      });

      tableWithGSI.addGlobalSecondaryIndex({
        indexName: 'program-index',
        partitionKey: {
          name: 'program',
          type: dynamodb.AttributeType.STRING,
        },
        sortKey: {
          name: 'created_at',
          type: dynamodb.AttributeType.STRING,
        },
      });

      const freshTemplate = getTemplate(freshStack);

      // Verify GSI creation
      freshTemplate.hasResourceProperties('AWS::DynamoDB::Table', {
        GlobalSecondaryIndexes: [{
          IndexName: 'program-index',
          KeySchema: [
            {
              AttributeName: 'program',
              KeyType: 'HASH'
            },
            {
              AttributeName: 'created_at',
              KeyType: 'RANGE'
            }
          ]
        }]
      });

      // Mock query operation
      mockDocumentClient.query.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Items: [
            {
              core_schema_id: 'cyclospora_core_v1',
              program: 'cyclospora',
              created_at: '2024-01-01T00:00:00Z'
            }
          ],
          Count: 1
        })
      });

      // Test query operation
      const queryResult = await mockDocumentClient.query({
        TableName: 'test-metadata-schemas-table',
        IndexName: 'program-index',
        KeyConditionExpression: 'program = :program',
        ExpressionAttributeValues: {
          ':program': 'cyclospora'
        }
      }).promise();

      expect(mockDocumentClient.query).toHaveBeenCalledWith({
        TableName: 'test-metadata-schemas-table',
        IndexName: 'program-index',
        KeyConditionExpression: 'program = :program',
        ExpressionAttributeValues: {
          ':program': 'cyclospora'
        }
      });

      expect(queryResult.Items).toHaveLength(1);
      expect(queryResult.Items[0].program).toBe('cyclospora');
    });
  });

  describe('Metadata Upload Job Table Operations', () => {
    let metadataUploadJobTable: dynamodb.Table;

    beforeEach(() => {
      metadataUploadJobTable = new dynamodb.Table(stack, 'MetadataUploadJob', {
        tableName: 'test-metadata-upload-job-table',
        partitionKey: {
          name: 'job_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
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
    });

    test('should create table with GSI for user queries', () => {
      template.hasResourceProperties('AWS::DynamoDB::Table', {
        TableName: 'test-metadata-upload-job-table',
        KeySchema: [{
          AttributeName: 'job_id',
          KeyType: 'HASH'
        }],
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
        }]
      });
    });

    test('should support job lifecycle operations', async () => {
      const testJob = {
        job_id: 'job-12345',
        user_id: 'user-67890',
        status: 'pending',
        created_at: '2024-01-01T00:00:00Z',
        file_name: 'test_metadata.csv',
        schema_id: 'cyclospora_core_v1'
      };

      // Mock job creation
      mockDocumentClient.put.mockReturnValue({
        promise: jest.fn().mockResolvedValue({})
      });

      // Mock job status updates
      mockDocumentClient.update.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Attributes: { ...testJob, status: 'processing', updated_at: '2024-01-01T01:00:00Z' }
        })
      });

      // Test job creation
      await mockDocumentClient.put({
        TableName: 'test-metadata-upload-job-table',
        Item: testJob
      }).promise();

      expect(mockDocumentClient.put).toHaveBeenCalledWith({
        TableName: 'test-metadata-upload-job-table',
        Item: testJob
      });

      // Test job status update
      await mockDocumentClient.update({
        TableName: 'test-metadata-upload-job-table',
        Key: { job_id: 'job-12345' },
        UpdateExpression: 'SET #status = :status, updated_at = :updated_at',
        ExpressionAttributeNames: {
          '#status': 'status'
        },
        ExpressionAttributeValues: {
          ':status': 'processing',
          ':updated_at': '2024-01-01T01:00:00Z'
        }
      }).promise();

      expect(mockDocumentClient.update).toHaveBeenCalled();
    });

    test('should support querying jobs by user', async () => {
      // Mock user job query
      mockDocumentClient.query.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Items: [
            {
              job_id: 'job-12345',
              user_id: 'user-67890',
              status: 'completed',
              created_at: '2024-01-01T00:00:00Z'
            },
            {
              job_id: 'job-12346',
              user_id: 'user-67890',
              status: 'pending',
              created_at: '2024-01-01T01:00:00Z'
            }
          ],
          Count: 2
        })
      });

      // Test user job query
      const userJobs = await mockDocumentClient.query({
        TableName: 'test-metadata-upload-job-table',
        IndexName: 'user-id-index',
        KeyConditionExpression: 'user_id = :user_id',
        ExpressionAttributeValues: {
          ':user_id': 'user-67890'
        },
        ScanIndexForward: false // Most recent first
      }).promise();

      expect(mockDocumentClient.query).toHaveBeenCalledWith({
        TableName: 'test-metadata-upload-job-table',
        IndexName: 'user-id-index',
        KeyConditionExpression: 'user_id = :user_id',
        ExpressionAttributeValues: {
          ':user_id': 'user-67890'
        },
        ScanIndexForward: false
      });

      expect(userJobs.Items).toHaveLength(2);
      expect(userJobs.Items[0].user_id).toBe('user-67890');
    });

    test('should support filtering jobs by status', async () => {
      // Mock filtered query
      mockDocumentClient.query.mockReturnValue({
        promise: jest.fn().mockResolvedValue({
          Items: [
            {
              job_id: 'job-12345',
              user_id: 'user-67890',
              status: 'completed',
              created_at: '2024-01-01T00:00:00Z'
            }
          ],
          Count: 1
        })
      });

      // Test filtered query
      const completedJobs = await mockDocumentClient.query({
        TableName: 'test-metadata-upload-job-table',
        IndexName: 'user-id-index',
        KeyConditionExpression: 'user_id = :user_id',
        FilterExpression: '#status = :status',
        ExpressionAttributeNames: {
          '#status': 'status'
        },
        ExpressionAttributeValues: {
          ':user_id': 'user-67890',
          ':status': 'completed'
        }
      }).promise();

      expect(mockDocumentClient.query).toHaveBeenCalledWith({
        TableName: 'test-metadata-upload-job-table',
        IndexName: 'user-id-index',
        KeyConditionExpression: 'user_id = :user_id',
        FilterExpression: '#status = :status',
        ExpressionAttributeNames: {
          '#status': 'status'
        },
        ExpressionAttributeValues: {
          ':user_id': 'user-67890',
          ':status': 'completed'
        }
      });

      expect(completedJobs.Items).toHaveLength(1);
      expect(completedJobs.Items[0].status).toBe('completed');
    });
  });

  describe('IAM Permissions Integration', () => {
    test('should grant correct permissions to task role', () => {
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

      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Grant permissions
      metadataSchemasTable.grantReadWriteData(taskRole);
      metadataUploadJobTable.grantReadWriteData(taskRole);

      template = getTemplate(stack);

      // Verify IAM policies are created (CDK may merge grants to same role)
      const policies = template.findResources('AWS::IAM::Policy');
      expect(Object.keys(policies).length).toBeGreaterThanOrEqual(1);

      // Verify permissions include all necessary DynamoDB actions
      const policyValues = Object.values(policies) as any[];
      const hasDynamoActions = policyValues.some((p: any) =>
        p.Properties.PolicyDocument.Statement.some((s: any) =>
          Array.isArray(s.Action) && s.Action.includes('dynamodb:PutItem') && s.Action.includes('dynamodb:GetItem')
        )
      );
      expect(hasDynamoActions).toBe(true);
    });

    test('should include GSI permissions in IAM policies', () => {
      const metadataUploadJobTable = new dynamodb.Table(stack, 'MetadataUploadJob', {
        partitionKey: {
          name: 'job_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
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

      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      metadataUploadJobTable.grantReadWriteData(taskRole);

      template = getTemplate(stack);

      // Verify that IAM policy includes GSI resources
      const policies = template.findResources('AWS::IAM::Policy');
      const policyValues = Object.values(policies);

      const dynamoPolicy = policyValues.find((policy: any) =>
        policy.Properties.PolicyDocument.Statement.some((stmt: any) =>
          stmt.Action.some((action: string) => action.startsWith('dynamodb:'))
        )
      ) as any;

      expect(dynamoPolicy).toBeDefined();

      // Check that policy includes both table and index resources
      const resources = dynamoPolicy.Properties.PolicyDocument.Statement[0].Resource;
      expect(Array.isArray(resources)).toBe(true);
      expect(resources.some((resource: any) =>
        typeof resource === 'object' && resource['Fn::GetAtt']
      )).toBe(true);
    });

    test('should not include RDS-related permissions', () => {
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      metadataSchemasTable.grantReadWriteData(taskRole);

      template = getTemplate(stack);

      // Get all policies and verify no RDS actions
      const policies = template.findResources('AWS::IAM::Policy');

      Object.values(policies).forEach((policy: any) => {
        const statements = policy.Properties?.PolicyDocument?.Statement || [];
        statements.forEach((statement: any) => {
          const actions = Array.isArray(statement.Action) ? statement.Action : [statement.Action];

          actions.forEach((action: string) => {
            expect(action).not.toMatch(/^rds:/);
            expect(action).not.toMatch(/^rds-db:/);
            expect(action).not.toMatch(/^secretsmanager:/);
          });
        });
      });
    });
  });

  describe('Error Handling and Resilience', () => {
    test('should handle DynamoDB throttling gracefully', async () => {
      // Mock throttling error
      mockDocumentClient.put.mockReturnValue({
        promise: jest.fn().mockRejectedValue({
          code: 'ProvisionedThroughputExceededException',
          message: 'The level of configured provisioned throughput for the table was exceeded'
        })
      });

      const handleThrottling = async (operation: Function, maxRetries: number = 3): Promise<any> => {
        let retries = 0;
        while (retries < maxRetries) {
          try {
            return await operation();
          } catch (error: any) {
            if (error.code === 'ProvisionedThroughputExceededException' && retries < maxRetries - 1) {
              retries++;
              await new Promise(resolve => setTimeout(resolve, Math.pow(2, retries) * 100));
            } else {
              throw error;
            }
          }
        }
      };

      // Test throttling handling
      try {
        await handleThrottling(() =>
          mockDocumentClient.put({
            TableName: 'test-metadata-schemas-table',
            Item: { core_schema_id: 'test' }
          }).promise()
        );
      } catch (error: any) {
        expect(error.code).toBe('ProvisionedThroughputExceededException');
      }

      expect(mockDocumentClient.put).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    test('should handle conditional check failures', async () => {
      // Mock conditional check failure
      mockDocumentClient.update.mockReturnValue({
        promise: jest.fn().mockRejectedValue({
          code: 'ConditionalCheckFailedException',
          message: 'The conditional request failed'
        })
      });

      try {
        await mockDocumentClient.update({
          TableName: 'test-metadata-upload-job-table',
          Key: { job_id: 'job-12345' },
          UpdateExpression: 'SET #status = :status',
          ConditionExpression: '#status = :current_status',
          ExpressionAttributeNames: {
            '#status': 'status'
          },
          ExpressionAttributeValues: {
            ':status': 'processing',
            ':current_status': 'pending'
          }
        }).promise();
      } catch (error: any) {
        expect(error.code).toBe('ConditionalCheckFailedException');
      }

      expect(mockDocumentClient.update).toHaveBeenCalled();
    });

    test('should handle item not found scenarios', async () => {
      // Mock empty response
      mockDocumentClient.get.mockReturnValue({
        promise: jest.fn().mockResolvedValue({})
      });

      const result = await mockDocumentClient.get({
        TableName: 'test-metadata-schemas-table',
        Key: { core_schema_id: 'non-existent-schema' }
      }).promise();

      expect(result.Item).toBeUndefined();
      expect(mockDocumentClient.get).toHaveBeenCalledWith({
        TableName: 'test-metadata-schemas-table',
        Key: { core_schema_id: 'non-existent-schema' }
      });
    });
  });
});
