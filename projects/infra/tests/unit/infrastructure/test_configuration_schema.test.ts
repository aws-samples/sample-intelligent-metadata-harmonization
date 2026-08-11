/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for configuration schema validation
 */

import { z } from 'zod';
import { TEST_CONFIG } from '../../fixtures/test-config';

// Mock the configuration schema based on the design document
const MetadataConfigSchema = z.object({
  validationResultsBucketName: z.string().optional(),
  schemaStorageBucketName: z.string().optional(),
  metadataSchemasTableName: z.string().optional(),
  metadataUploadJobTableName: z.string().optional(),
  metadataConfigDir: z.string().optional(),
});

const RawConfigSchema = z.object({
  appName: z
    .string()
    .default('metadata-harmonization-app')
    .transform((value) => value.toLowerCase()),
  region: z.string(),
  deploymentStage: z.string(),
  logLevel: z.string(),
  removalPolicy: z.string(),
  metadataConfig: MetadataConfigSchema.optional(),
  cognito: z.object({
    userPoolId: z.string(),
    userPoolClientId: z.string(),
    userPoolDomain: z.string()
  }),
  cloudFront: z.object({
    certificateArn: z.string(),
    domainName: z.string(),
    hostedZoneId: z.string(),
    hostedZoneName: z.string()
  })
});

describe('Configuration Schema Validation', () => {
  describe('MetadataConfigSchema', () => {
    test('should validate valid metadata configuration', () => {
      const validConfig = {
        validationResultsBucketName: 'test-validation-results',
        schemaStorageBucketName: 'test-schema-storage',
        metadataSchemasTableName: 'test-metadata-schemas',
        metadataUploadJobTableName: 'test-metadata-upload-job',
        metadataConfigDir: '/test/config'
      };

      const result = MetadataConfigSchema.safeParse(validConfig);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data).toEqual(validConfig);
      }
    });

    test('should allow optional properties to be undefined', () => {
      const minimalConfig = {};

      const result = MetadataConfigSchema.safeParse(minimalConfig);
      expect(result.success).toBe(true);
    });

    test('should validate partial metadata configuration', () => {
      const partialConfig = {
        validationResultsBucketName: 'test-validation-results',
        metadataSchemasTableName: 'test-metadata-schemas'
      };

      const result = MetadataConfigSchema.safeParse(partialConfig);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.validationResultsBucketName).toBe('test-validation-results');
        expect(result.data.metadataSchemasTableName).toBe('test-metadata-schemas');
        expect(result.data.schemaStorageBucketName).toBeUndefined();
      }
    });

    test('should reject invalid property types', () => {
      const invalidConfig = {
        validationResultsBucketName: 123, // Should be string
        metadataSchemasTableName: true     // Should be string
      };

      const result = MetadataConfigSchema.safeParse(invalidConfig);
      expect(result.success).toBe(false);
    });
  });

  describe('RawConfigSchema', () => {
    test('should validate complete configuration', () => {
      const config = TEST_CONFIG.dev;

      const result = RawConfigSchema.safeParse(config);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.appName).toBe('metadata-harmonization-app-test');
        expect(result.data.region).toBe('us-east-1');
        expect(result.data.metadataConfig).toBeDefined();
        expect(result.data.metadataConfig?.validationResultsBucketName).toBe('test-validation-results');
      }
    });

    test('should transform appName to lowercase', () => {
      const config = {
        ...TEST_CONFIG.dev,
        appName: 'METADATA-HARMONIZATION-APP-TEST'
      };

      const result = RawConfigSchema.safeParse(config);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.appName).toBe('metadata-harmonization-app-test');
      }
    });

    test('should use default appName when not provided', () => {
      const config = {
        ...TEST_CONFIG.dev
      };
      delete (config as any).appName;

      const result = RawConfigSchema.safeParse(config);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.appName).toBe('metadata-harmonization-app');
      }
    });

    test('should validate staging configuration', () => {
      const config = TEST_CONFIG.staging;

      const result = RawConfigSchema.safeParse(config);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.deploymentStage).toBe('staging');
        expect(result.data.removalPolicy).toBe('RETAIN');
        expect(result.data.metadataConfig?.validationResultsBucketName).toBe('staging-validation-results');
      }
    });

    test('should require essential properties', () => {
      const incompleteConfig = {
        appName: 'test-app'
        // Missing required properties
      };

      const result = RawConfigSchema.safeParse(incompleteConfig);
      expect(result.success).toBe(false);

      if (!result.success) {
        const errors = result.error.errors;
        const missingFields = errors.map(e => e.path[0]);

        expect(missingFields).toContain('region');
        expect(missingFields).toContain('deploymentStage');
        expect(missingFields).toContain('cognito');
        expect(missingFields).toContain('cloudFront');
      }
    });

    test('should validate nested objects', () => {
      const configWithInvalidNested = {
        ...TEST_CONFIG.dev,
        cognito: {
          userPoolId: 'valid-pool-id'
          // Missing required properties
        }
      };

      const result = RawConfigSchema.safeParse(configWithInvalidNested);
      expect(result.success).toBe(false);

      if (!result.success) {
        const errors = result.error.errors;
        const cognitoErrors = errors.filter(e => e.path[0] === 'cognito');
        expect(cognitoErrors.length).toBeGreaterThan(0);
      }
    });
  });


  describe('Environment-specific Configuration', () => {
    test('should validate development environment configuration', () => {
      const devConfig = TEST_CONFIG.dev;

      const result = RawConfigSchema.safeParse(devConfig);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.deploymentStage).toBe('dev');
        expect(result.data.logLevel).toBe('DEBUG');
        expect(result.data.removalPolicy).toBe('DESTROY');
      }
    });

    test('should validate staging environment configuration', () => {
      const stagingConfig = TEST_CONFIG.staging;

      const result = RawConfigSchema.safeParse(stagingConfig);
      expect(result.success).toBe(true);

      if (result.success) {
        expect(result.data.deploymentStage).toBe('staging');
        expect(result.data.logLevel).toBe('INFO');
        expect(result.data.removalPolicy).toBe('RETAIN');
      }
    });

    test('should validate different resource naming per environment', () => {
      const devConfig = TEST_CONFIG.dev;
      const stagingConfig = TEST_CONFIG.staging;

      const devResult = RawConfigSchema.safeParse(devConfig);
      const stagingResult = RawConfigSchema.safeParse(stagingConfig);

      expect(devResult.success).toBe(true);
      expect(stagingResult.success).toBe(true);

      if (devResult.success && stagingResult.success) {
        // Verify different resource names per environment
        expect(devResult.data.metadataConfig?.validationResultsBucketName).toBe('test-validation-results');
        expect(stagingResult.data.metadataConfig?.validationResultsBucketName).toBe('staging-validation-results');

        expect(devResult.data.metadataConfig?.metadataSchemasTableName).toBe('test-metadata-schemas');
        expect(stagingResult.data.metadataConfig?.metadataSchemasTableName).toBe('staging-metadata-schemas');
      }
    });
  });
});
