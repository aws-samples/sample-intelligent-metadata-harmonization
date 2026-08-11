/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Mock AWS API responses for testing
 */

export const MOCK_DYNAMODB_RESPONSES = {
  describeTableMetadataSchemas: {
    Table: {
      TableName: 'test-metadata-schemas-table',
      TableStatus: 'ACTIVE',
      KeySchema: [{
        AttributeName: 'core_schema_id',
        KeyType: 'HASH'
      }],
      AttributeDefinitions: [{
        AttributeName: 'core_schema_id',
        AttributeType: 'S'
      }],
      BillingModeSummary: {
        BillingMode: 'PAY_PER_REQUEST'
      },
      SSEDescription: {
        Status: 'ENABLED',
        SSEType: 'AES256'
      }
    }
  },

  describeTableMetadataUploadJob: {
    Table: {
      TableName: 'test-metadata-upload-job-table',
      TableStatus: 'ACTIVE',
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
        ],
        IndexStatus: 'ACTIVE'
      }],
      BillingModeSummary: {
        BillingMode: 'PAY_PER_REQUEST'
      },
      SSEDescription: {
        Status: 'ENABLED',
        SSEType: 'AES256'
      }
    }
  }
};

export const MOCK_S3_RESPONSES = {
  listBuckets: {
    Buckets: [
      {
        Name: 'test-validation-results-bucket',
        CreationDate: new Date('2024-01-01T00:00:00.000Z')
      },
      {
        Name: 'test-schema-storage-bucket',
        CreationDate: new Date('2024-01-01T00:00:00.000Z')
      }
    ]
  },

  getBucketEncryptionValidationResults: {
    ServerSideEncryptionConfiguration: {
      Rules: [{
        ApplyServerSideEncryptionByDefault: {
          SSEAlgorithm: 'AES256'
        }
      }]
    }
  },

  getBucketEncryptionSchemaStorage: {
    ServerSideEncryptionConfiguration: {
      Rules: [{
        ApplyServerSideEncryptionByDefault: {
          SSEAlgorithm: 'AES256'
        }
      }]
    }
  },

  getBucketPolicyValidationResults: {
    Policy: JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Deny',
        Principal: '*',
        Action: 's3:*',
        Resource: [
          'arn:aws:s3:::test-validation-results-bucket',
          'arn:aws:s3:::test-validation-results-bucket/*'
        ],
        Condition: {
          Bool: {
            'aws:SecureTransport': 'false'
          }
        }
      }]
    })
  },

  getBucketPolicySchemaStorage: {
    Policy: JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Deny',
        Principal: '*',
        Action: 's3:*',
        Resource: [
          'arn:aws:s3:::test-schema-storage-bucket',
          'arn:aws:s3:::test-schema-storage-bucket/*'
        ],
        Condition: {
          Bool: {
            'aws:SecureTransport': 'false'
          }
        }
      }]
    })
  }
};

export const MOCK_IAM_POLICIES = {
  dynamodbReadWrite: {
    Version: '2012-10-17',
    Statement: [{
      Effect: 'Allow',
      Action: [
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
        'dynamodb:Query',
        'dynamodb:Scan'
      ],
      Resource: [
        'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-schemas-table',
        'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table'
      ]
    }]
  },

  s3ValidationResults: {
    Version: '2012-10-17',
    Statement: [{
      Effect: 'Allow',
      Action: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject'
      ],
      Resource: 'arn:aws:s3:::test-validation-results-bucket/*'
    }]
  },

  s3SchemaStorage: {
    Version: '2012-10-17',
    Statement: [{
      Effect: 'Allow',
      Action: [
        's3:GetObject'
      ],
      Resource: 'arn:aws:s3:::test-schema-storage-bucket/*'
    }]
  }
};
