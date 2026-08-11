/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Test utilities for infrastructure tests
 */

import { App, Stack } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';

/**
 * Create a test CDK app and stack
 */
export function createTestApp(stackName: string = 'TestStack'): { app: App; stack: Stack } {
  const app = new App();
  const stack = new Stack(app, stackName, {
    env: {
      account: '123456789012',
      region: 'us-east-1'
    }
  });

  return { app, stack };
}

/**
 * Get CloudFormation template from a stack
 */
export function getTemplate(stack: Stack): Template {
  return Template.fromStack(stack);
}

/**
 * Mock environment variables for testing
 */
export function mockEnvironmentVariables(vars: Record<string, string>): void {
  Object.entries(vars).forEach(([key, value]) => {
    process.env[key] = value;
  });
}

/**
 * Clean up environment variables after testing
 */
export function cleanupEnvironmentVariables(vars: string[]): void {
  vars.forEach(key => {
    delete process.env[key];
  });
}

/**
 * Create a mock configuration object
 */
export function createMockConfig(overrides: any = {}) {
  return {
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
    },
    ...overrides
  };
}

/**
 * Assert that a resource exists in the template
 */
export function assertResourceExists(template: Template, resourceType: string, properties?: any): void {
  if (properties) {
    template.hasResourceProperties(resourceType, properties);
  } else {
    template.resourceCountIs(resourceType, 1);
  }
}

/**
 * Assert that a resource does not exist in the template
 */
export function assertResourceDoesNotExist(template: Template, resourceType: string): void {
  template.resourceCountIs(resourceType, 0);
}

/**
 * Get all resources of a specific type from template
 */
export function getResourcesOfType(template: Template, resourceType: string): any[] {
  const resources = template.findResources(resourceType);
  return Object.values(resources);
}

/**
 * Mock AWS CLI command responses
 */
export function mockAwsCliResponse(command: string, response: any): jest.Mock {
  const mockExec = jest.fn();

  mockExec.mockImplementation((cmd: string, callback: Function) => {
    if (cmd.includes(command)) {
      callback(null, { stdout: JSON.stringify(response) });
    } else {
      callback(new Error(`Command not mocked: ${cmd}`));
    }
  });

  return mockExec;
}

/**
 * Create a temporary file for testing
 */
export function createTempFile(content: string, extension: string = '.tmp'): string {
  const fs = require('fs');
  const path = require('path');
  const os = require('os');

  const tempDir = os.tmpdir();
  const fileName = `test-${Date.now()}${extension}`;
  const filePath = path.join(tempDir, fileName);

  fs.writeFileSync(filePath, content);

  return filePath;
}

/**
 * Clean up temporary files
 */
export function cleanupTempFile(filePath: string): void {
  const fs = require('fs');

  try {
    fs.unlinkSync(filePath);
  } catch (error) {
    // Ignore errors if file doesn't exist
  }
}
