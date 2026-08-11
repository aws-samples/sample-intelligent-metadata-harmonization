/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Test configuration data for infrastructure tests
 */

export const TEST_CONFIG = {
  dev: {
    appName: 'metadata-harmonization-app-test',
    region: 'us-east-1',
    deploymentStage: 'dev',
    logLevel: 'DEBUG',
    removalPolicy: 'DESTROY',

    metadataConfig: {
      validationResultsBucketName: 'test-validation-results',
      schemaStorageBucketName: 'test-schema-storage',
      metadataSchemasTableName: 'test-metadata-schemas',
      metadataUploadJobTableName: 'test-metadata-upload-job',
      metadataConfigDir: '/test/config'
    },

    cognito: {
      userPoolId: 'us-east-1_testpool',
      userPoolClientId: 'test-client-id',
      userPoolDomain: 'test-domain'
    },

    cloudFront: {
      certificateArn: 'arn:aws:acm:us-east-1:123456789012:certificate/test-cert',
      domainName: 'test.example.com',
      hostedZoneId: 'Z123456789',
      hostedZoneName: 'example.com'
    }
  },

  staging: {
    appName: 'metadata-harmonization-app-staging',
    region: 'us-east-1',
    deploymentStage: 'staging',
    logLevel: 'INFO',
    removalPolicy: 'RETAIN',

    metadataConfig: {
      validationResultsBucketName: 'staging-validation-results',
      schemaStorageBucketName: 'staging-schema-storage',
      metadataSchemasTableName: 'staging-metadata-schemas',
      metadataUploadJobTableName: 'staging-metadata-upload-job',
      metadataConfigDir: '/staging/config'
    },

    cognito: {
      userPoolId: 'us-east-1_stagingpool',
      userPoolClientId: 'staging-client-id',
      userPoolDomain: 'staging-domain'
    },

    cloudFront: {
      certificateArn: 'arn:aws:acm:us-east-1:123456789012:certificate/staging-cert',
      domainName: 'staging.example.com',
      hostedZoneId: 'Z123456789',
      hostedZoneName: 'example.com'
    }
  }
};

export const MOCK_CLOUDFORMATION_OUTPUTS = {
  Stacks: [{
    StackName: 'metadata-harmonization-app-test-stack',
    StackStatus: 'CREATE_COMPLETE',
    Outputs: [
      {
        OutputKey: 'MetadataSchemasTableName',
        OutputValue: 'test-metadata-schemas-table',
        Description: 'DynamoDB table name for metadata schemas'
      },
      {
        OutputKey: 'MetadataUploadJobTableName',
        OutputValue: 'test-metadata-upload-job-table',
        Description: 'DynamoDB table name for metadata upload jobs'
      },
      {
        OutputKey: 'ValidationResultsBucketName',
        OutputValue: 'test-validation-results-bucket',
        Description: 'S3 bucket name for validation results'
      },
      {
        OutputKey: 'SchemaStorageBucketName',
        OutputValue: 'test-schema-storage-bucket',
        Description: 'S3 bucket name for schema storage'
      },
      {
        OutputKey: 'ApiUrl',
        OutputValue: 'https://test-api.example.com',
        Description: 'API Gateway URL'
      },
      {
        OutputKey: 'WebsiteUrl',
        OutputValue: 'https://test.example.com',
        Description: 'CloudFront distribution URL'
      }
    ]
  }]
};

export const SAMPLE_METADATA = {
  schema: {
    core_schema_id: 'cyclospora_core_v1',
    schema_name: 'Cyclospora Core Schema',
    schema_version: '1.0.0',
    schema_type: 'core',
    program: 'cyclospora',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },

  uploadJob: {
    job_id: 'job-12345',
    user_id: 'user-67890',
    status: 'pending',
    created_at: '2024-01-01T00:00:00Z',
    file_name: 'test_metadata.csv',
    schema_id: 'cyclospora_core_v1'
  },

  validationResult: {
    job_id: 'job-12345',
    validation_status: 'completed',
    total_records: 100,
    valid_records: 95,
    invalid_records: 5,
    errors: [{
      row: 10,
      field: 'collection_date',
      error: 'Invalid date format'
    }]
  }
};

export const TEST_ENVIRONMENT_VARIABLES = {
  AWS_REGION: 'us-east-1',
  METADATA_SCHEMAS_TABLE: 'test-metadata-schemas-table',
  METADATA_UPLOAD_JOB_TABLE: 'test-metadata-upload-job-table',
  VALIDATION_RESULTS_BUCKET: 'test-validation-results-bucket',
  SCHEMA_STORAGE_BUCKET: 'test-schema-storage-bucket',
  LOG_LEVEL: 'DEBUG'
};
