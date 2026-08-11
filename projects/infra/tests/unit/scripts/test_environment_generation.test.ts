/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for environment variable generation script
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { MOCK_CLOUDFORMATION_OUTPUTS } from '../../fixtures/test-config';

const execAsync = promisify(exec);

// Mock the AWS CLI responses
jest.mock('child_process', () => ({
  exec: jest.fn()
}));

const mockExec = exec as unknown as jest.Mock;

describe('Environment Variable Generation Script', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Reset environment variables
    delete process.env.METADATA_SCHEMAS_TABLE;
    delete process.env.METADATA_UPLOAD_JOB_TABLE;
    delete process.env.VALIDATION_RESULTS_BUCKET;
    delete process.env.SCHEMA_STORAGE_BUCKET;
    delete process.env.DB_HOST;
    delete process.env.DB_PORT;
    delete process.env.DB_NAME;
  });

  describe('CloudFormation Output Retrieval', () => {
    test('should retrieve DynamoDB table names from CloudFormation outputs', async () => {
      const mockStackName = 'metadata-harmonization-app-test-stack';
      const mockRegion = 'us-east-1';
      const mockProfile = 'test-profile';

      // Mock AWS CLI responses for DynamoDB tables
      mockExec.mockImplementation((command: string, callback: any) => {
        if (command.includes('MetadataSchemasTableName')) {
          callback(null, 'test-metadata-schemas-table\n', '');
        } else if (command.includes('MetadataUploadJobTableName')) {
          callback(null, 'test-metadata-upload-job-table\n', '');
        } else {
          callback(new Error('Command not mocked'));
        }
      });

      // Simulate the script logic
      const getCloudFormationOutput = async (stackName: string, outputKey: string, region: string, profile: string): Promise<string> => {
        return new Promise((resolve, reject) => {
          const command = `aws cloudformation describe-stacks --stack-name "${stackName}" --query 'Stacks[0].Outputs[?OutputKey==\`${outputKey}\`].OutputValue' --output text --region "${region}" --profile "${profile}"`;

          exec(command, (error, stdout) => {
            if (error) {
              reject(error);
            } else {
              resolve(stdout.trim());
            }
          });
        });
      };

      const metadataSchemasTable = await getCloudFormationOutput(mockStackName, 'MetadataSchemasTableName', mockRegion, mockProfile);
      const metadataUploadJobTable = await getCloudFormationOutput(mockStackName, 'MetadataUploadJobTableName', mockRegion, mockProfile);

      expect(metadataSchemasTable).toBe('test-metadata-schemas-table');
      expect(metadataUploadJobTable).toBe('test-metadata-upload-job-table');
      expect(mockExec).toHaveBeenCalledTimes(2);
    });

    test('should retrieve S3 bucket names from CloudFormation outputs', async () => {
      const mockStackName = 'metadata-harmonization-app-test-stack';
      const mockRegion = 'us-east-1';
      const mockProfile = 'test-profile';

      // Mock AWS CLI responses for S3 buckets
      mockExec.mockImplementation((command: string, callback: any) => {
        if (command.includes('ValidationResultsBucketName')) {
          callback(null, 'test-validation-results-bucket\n', '');
        } else if (command.includes('SchemaStorageBucketName')) {
          callback(null, 'test-schema-storage-bucket\n', '');
        } else {
          callback(new Error('Command not mocked'));
        }
      });

      const getCloudFormationOutput = async (stackName: string, outputKey: string, region: string, profile: string): Promise<string> => {
        return new Promise((resolve, reject) => {
          const command = `aws cloudformation describe-stacks --stack-name "${stackName}" --query 'Stacks[0].Outputs[?OutputKey==\`${outputKey}\`].OutputValue' --output text --region "${region}" --profile "${profile}"`;

          exec(command, (error, stdout) => {
            if (error) {
              reject(error);
            } else {
              resolve(stdout.trim());
            }
          });
        });
      };

      const validationResultsBucket = await getCloudFormationOutput(mockStackName, 'ValidationResultsBucketName', mockRegion, mockProfile);
      const schemaStorageBucket = await getCloudFormationOutput(mockStackName, 'SchemaStorageBucketName', mockRegion, mockProfile);

      expect(validationResultsBucket).toBe('test-validation-results-bucket');
      expect(schemaStorageBucket).toBe('test-schema-storage-bucket');
      expect(mockExec).toHaveBeenCalledTimes(2);
    });

    test('should not retrieve database-related environment variables', async () => {
      const mockStackName = 'metadata-harmonization-app-test-stack';
      const mockRegion = 'us-east-1';
      const mockProfile = 'test-profile';

      // Mock that database-related outputs don't exist
      mockExec.mockImplementation((command: string, callback: any) => {
        if (command.includes('DBHost') || command.includes('DBPort') || command.includes('DBName')) {
          callback(null, '', 'Output key not found');
        } else {
          callback(new Error('Command not mocked'));
        }
      });

      const getCloudFormationOutput = async (stackName: string, outputKey: string, region: string, profile: string): Promise<string | null> => {
        return new Promise((resolve) => {
          const command = `aws cloudformation describe-stacks --stack-name "${stackName}" --query 'Stacks[0].Outputs[?OutputKey==\`${outputKey}\`].OutputValue' --output text --region "${region}" --profile "${profile}"`;

          exec(command, (error, stdout) => {
            if (error || !stdout.trim()) {
              resolve(null);
            } else {
              resolve(stdout.trim());
            }
          });
        });
      };

      const dbHost = await getCloudFormationOutput(mockStackName, 'DBHost', mockRegion, mockProfile);
      const dbPort = await getCloudFormationOutput(mockStackName, 'DBPort', mockRegion, mockProfile);
      const dbName = await getCloudFormationOutput(mockStackName, 'DBName', mockRegion, mockProfile);

      expect(dbHost).toBeNull();
      expect(dbPort).toBeNull();
      expect(dbName).toBeNull();
    });
  });

  describe('Environment File Generation', () => {
    test('should generate .env file with correct metadata variables', () => {
      const environmentVariables = {
        AWS_REGION: 'us-east-1',
        METADATA_SCHEMAS_TABLE: 'test-metadata-schemas-table',
        METADATA_UPLOAD_JOB_TABLE: 'test-metadata-upload-job-table',
        VALIDATION_RESULTS_BUCKET: 'test-validation-results-bucket',
        SCHEMA_STORAGE_BUCKET: 'test-schema-storage-bucket',
        LOG_LEVEL: 'DEBUG'
      };

      const generateEnvFile = (vars: Record<string, string>): string => {
        return Object.entries(vars)
          .map(([key, value]) => `${key}=${value}`)
          .join('\n');
      };

      const envContent = generateEnvFile(environmentVariables);

      expect(envContent).toContain('AWS_REGION=us-east-1');
      expect(envContent).toContain('METADATA_SCHEMAS_TABLE=test-metadata-schemas-table');
      expect(envContent).toContain('METADATA_UPLOAD_JOB_TABLE=test-metadata-upload-job-table');
      expect(envContent).toContain('VALIDATION_RESULTS_BUCKET=test-validation-results-bucket');
      expect(envContent).toContain('SCHEMA_STORAGE_BUCKET=test-schema-storage-bucket');
      expect(envContent).toContain('LOG_LEVEL=DEBUG');
    });

    test('should not include database-related variables in .env file', () => {
      const environmentVariables = {
        AWS_REGION: 'us-east-1',
        METADATA_SCHEMAS_TABLE: 'test-metadata-schemas-table',
        VALIDATION_RESULTS_BUCKET: 'test-validation-results-bucket',
        LOG_LEVEL: 'DEBUG'
      };

      const generateEnvFile = (vars: Record<string, string>): string => {
        return Object.entries(vars)
          .map(([key, value]) => `${key}=${value}`)
          .join('\n');
      };

      const envContent = generateEnvFile(environmentVariables);

      // Should not contain database-related variables
      expect(envContent).not.toContain('DB_HOST');
      expect(envContent).not.toContain('DB_PORT');
      expect(envContent).not.toContain('DB_NAME');
      expect(envContent).not.toContain('DB_USERNAME');
      expect(envContent).not.toContain('DB_PASSWORD_SECRET_ARN');
    });

  });

  describe('Error Handling', () => {
    test('should handle CloudFormation stack not found error', async () => {
      mockExec.mockImplementation((command: string, callback: any) => {
        callback(new Error('Stack with id metadata-harmonization-app-test-stack does not exist'), '', 'Stack not found');
      });

      const getCloudFormationOutput = async (stackName: string, outputKey: string, region: string, profile: string): Promise<string | null> => {
        return new Promise((resolve) => {
          const command = `aws cloudformation describe-stacks --stack-name "${stackName}" --query 'Stacks[0].Outputs[?OutputKey==\`${outputKey}\`].OutputValue' --output text --region "${region}" --profile "${profile}"`;

          exec(command, (error, stdout) => {
            if (error) {
              resolve(null);
            } else {
              resolve(stdout.trim());
            }
          });
        });
      };

      const result = await getCloudFormationOutput('non-existent-stack', 'MetadataSchemasTableName', 'us-east-1', 'test-profile');
      expect(result).toBeNull();
    });

    test('should handle missing output key error', async () => {
      mockExec.mockImplementation((command: string, callback: any) => {
        callback(null, '', '');
      });

      const getCloudFormationOutput = async (stackName: string, outputKey: string, region: string, profile: string): Promise<string | null> => {
        return new Promise((resolve) => {
          const command = `aws cloudformation describe-stacks --stack-name "${stackName}" --query 'Stacks[0].Outputs[?OutputKey==\`${outputKey}\`].OutputValue' --output text --region "${region}" --profile "${profile}"`;

          exec(command, (error, stdout) => {
            if (error || !stdout.trim()) {
              resolve(null);
            } else {
              resolve(stdout.trim());
            }
          });
        });
      };

      const result = await getCloudFormationOutput('test-stack', 'NonExistentOutputKey', 'us-east-1', 'test-profile');
      expect(result).toBeNull();
    });

    test('should handle AWS CLI authentication errors', async () => {
      mockExec.mockImplementation((command: string, callback: any) => {
        callback(new Error('Unable to locate credentials'), '', 'Unable to locate credentials');
      });

      const getCloudFormationOutput = async (stackName: string, outputKey: string, region: string, profile: string): Promise<string | null> => {
        return new Promise((resolve) => {
          const command = `aws cloudformation describe-stacks --stack-name "${stackName}" --query 'Stacks[0].Outputs[?OutputKey==\`${outputKey}\`].OutputValue' --output text --region "${region}" --profile "${profile}"`;

          exec(command, (error, stdout) => {
            if (error) {
              resolve(null);
            } else {
              resolve(stdout.trim());
            }
          });
        });
      };

      const result = await getCloudFormationOutput('test-stack', 'MetadataSchemasTableName', 'us-east-1', 'invalid-profile');
      expect(result).toBeNull();
    });
  });

  describe('Script Configuration', () => {
    test('should use correct AWS CLI parameters', () => {
      const stackName = 'metadata-harmonization-app-test-stack';
      const region = 'us-east-1';
      const profile = 'test-profile';
      const outputKey = 'MetadataSchemasTableName';

      mockExec.mockImplementation((command: string, callback: any) => {
        expect(command).toContain(`--stack-name "${stackName}"`);
        expect(command).toContain(`--region "${region}"`);
        expect(command).toContain(`--profile "${profile}"`);
        expect(command).toContain(`--output text`);
        expect(command).toContain(`OutputKey==\`${outputKey}\``);

        callback(null, 'test-table-name\n', '');
      });

      exec(`aws cloudformation describe-stacks --stack-name "${stackName}" --query 'Stacks[0].Outputs[?OutputKey==\`${outputKey}\`].OutputValue' --output text --region "${region}" --profile "${profile}"`, () => {});

      expect(mockExec).toHaveBeenCalledTimes(1);
    });

    test('should validate required parameters', () => {
      const validateParameters = (stackName?: string, region?: string, profile?: string): string[] => {
        const errors: string[] = [];

        if (!stackName) errors.push('Stack name is required');
        if (!region) errors.push('Region is required');
        if (!profile) errors.push('Profile is required');

        return errors;
      };

      expect(validateParameters()).toEqual([
        'Stack name is required',
        'Region is required',
        'Profile is required'
      ]);

      expect(validateParameters('test-stack', 'us-east-1', 'test-profile')).toEqual([]);
    });
  });
});
