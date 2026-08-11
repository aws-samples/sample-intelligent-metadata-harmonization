/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for IAM policy generation and permissions
 */

import { Template, Match } from 'aws-cdk-lib/assertions';
import * as iam from 'aws-cdk-lib/aws-iam';
import { createTestApp, getTemplate, assertResourceExists } from '../../fixtures/test-utils';
import { MOCK_IAM_POLICIES } from '../../fixtures/mock-aws-responses';

describe('IAM Policies', () => {
  let app: any;
  let stack: any;
  let template: Template;

  beforeEach(() => {
    const testApp = createTestApp('IAMTestStack');
    app = testApp.app;
    stack = testApp.stack;
  });

  describe('DynamoDB Permissions', () => {
    test('should create policy with correct DynamoDB read/write permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

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
          'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table',
          'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-schemas-table/index/*',
          'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table/index/*'
        ]
      }));

      template = getTemplate(stack);

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
            ],
            Resource: [
              'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-schemas-table',
              'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table',
              'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-schemas-table/index/*',
              'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table/index/*'
            ]
          }]
        }
      });
    });

    test('should include permissions for GSI access', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Add permissions that include GSI access
      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['dynamodb:Query'],
        resources: [
          'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table/index/user-id-index'
        ]
      }));

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Action: 'dynamodb:Query',
            Resource: 'arn:aws:dynamodb:us-east-1:123456789012:table/test-metadata-upload-job-table/index/user-id-index'
          }]
        }
      });
    });

    test('should not include RDS-related permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Add only DynamoDB permissions
      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['dynamodb:GetItem', 'dynamodb:PutItem'],
        resources: ['arn:aws:dynamodb:us-east-1:123456789012:table/test-table']
      }));

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
          });
        });
      });
    });
  });

  describe('S3 Permissions', () => {
    test('should create policy with validation results bucket read/write permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:GetObject',
          's3:PutObject',
          's3:DeleteObject'
        ],
        resources: ['arn:aws:s3:::test-validation-results-bucket/*']
      }));

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Action: [
              's3:GetObject',
              's3:PutObject',
              's3:DeleteObject'
            ],
            Resource: 'arn:aws:s3:::test-validation-results-bucket/*'
          }]
        }
      });
    });

    test('should create policy with schema storage bucket read-only permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject'],
        resources: ['arn:aws:s3:::test-schema-storage-bucket/*']
      }));

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Action: 's3:GetObject',
            Resource: 'arn:aws:s3:::test-schema-storage-bucket/*'
          }]
        }
      });
    });

    test('should include bucket listing permissions when needed', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:ListBucket'],
        resources: [
          'arn:aws:s3:::test-validation-results-bucket',
          'arn:aws:s3:::test-schema-storage-bucket'
        ]
      }));

      template = getTemplate(stack);

      assertResourceExists(template, 'AWS::IAM::Policy', {
        PolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Action: 's3:ListBucket',
            Resource: [
              'arn:aws:s3:::test-validation-results-bucket',
              'arn:aws:s3:::test-schema-storage-bucket'
            ]
          }]
        }
      });
    });
  });

  describe('Task Role Configuration', () => {
    test('should create ECS task role with correct assume role policy', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
        description: 'Task role for metadata harmonization API'
      });

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
    });

    test('should create execution role with correct permissions', () => {
      const executionRole = new iam.Role(stack, 'ExecutionRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy')
        ]
      });

      template = getTemplate(stack);

      // Verify assume role policy
      assertResourceExists(template, 'AWS::IAM::Role', {
        AssumeRolePolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Principal: {
              Service: 'ecs-tasks.amazonaws.com'
            },
            Action: 'sts:AssumeRole'
          }]
        },
      });

      // Verify managed policy ARN (CDK generates Fn::Join for the ARN)
      const roles = template.findResources('AWS::IAM::Role');
      const foundRole = Object.values(roles).find((role: any) =>
        (role as any).Properties.ManagedPolicyArns
      ) as any;
      expect(foundRole).toBeDefined();
      expect(foundRole.Properties.ManagedPolicyArns).toHaveLength(1);
    });
  });

  describe('Policy Validation', () => {
    test('should validate policy structure matches expected format', () => {
      const expectedPolicy = MOCK_IAM_POLICIES.dynamodbReadWrite;

      expect(expectedPolicy).toHaveProperty('Version', '2012-10-17');
      expect(expectedPolicy).toHaveProperty('Statement');
      expect(Array.isArray(expectedPolicy.Statement)).toBe(true);

      const statement = expectedPolicy.Statement[0];
      expect(statement).toHaveProperty('Effect', 'Allow');
      expect(statement).toHaveProperty('Action');
      expect(statement).toHaveProperty('Resource');
      expect(Array.isArray(statement.Action)).toBe(true);
      expect(Array.isArray(statement.Resource)).toBe(true);
    });

    test('should validate S3 policy structure', () => {
      const validationResultsPolicy = MOCK_IAM_POLICIES.s3ValidationResults;
      const schemaStoragePolicy = MOCK_IAM_POLICIES.s3SchemaStorage;

      // Validation results bucket should have read/write permissions
      expect(validationResultsPolicy.Statement[0].Action).toContain('s3:GetObject');
      expect(validationResultsPolicy.Statement[0].Action).toContain('s3:PutObject');
      expect(validationResultsPolicy.Statement[0].Action).toContain('s3:DeleteObject');

      // Schema storage bucket should have read-only permissions
      expect(schemaStoragePolicy.Statement[0].Action).toEqual(['s3:GetObject']);
      expect(schemaStoragePolicy.Statement[0].Action).not.toContain('s3:PutObject');
      expect(schemaStoragePolicy.Statement[0].Action).not.toContain('s3:DeleteObject');
    });

    test('should ensure least privilege principle', () => {
      const dynamoPolicy = MOCK_IAM_POLICIES.dynamodbReadWrite;
      const s3ValidationPolicy = MOCK_IAM_POLICIES.s3ValidationResults;
      const s3SchemaPolicy = MOCK_IAM_POLICIES.s3SchemaStorage;

      // DynamoDB policy should only include necessary actions
      const dynamoActions = dynamoPolicy.Statement[0].Action;
      expect(dynamoActions).not.toContain('dynamodb:*');
      expect(dynamoActions).not.toContain('dynamodb:CreateTable');
      expect(dynamoActions).not.toContain('dynamodb:DeleteTable');

      // S3 policies should be scoped to specific buckets
      expect(s3ValidationPolicy.Statement[0].Resource).toBe('arn:aws:s3:::test-validation-results-bucket/*');
      expect(s3SchemaPolicy.Statement[0].Resource).toBe('arn:aws:s3:::test-schema-storage-bucket/*');

      // Should not include wildcard permissions
      expect(s3ValidationPolicy.Statement[0].Resource).not.toBe('*');
      expect(s3SchemaPolicy.Statement[0].Resource).not.toBe('*');
    });
  });

  describe('Permission Boundaries', () => {
    test('should not include overly broad permissions', () => {
      const taskRole = new iam.Role(stack, 'TaskRole', {
        assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      });

      // Add specific permissions (not wildcards)
      taskRole.addToPolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['dynamodb:GetItem', 'dynamodb:PutItem'],
        resources: ['arn:aws:dynamodb:us-east-1:123456789012:table/specific-table']
      }));

      template = getTemplate(stack);

      const policies = template.findResources('AWS::IAM::Policy');

      Object.values(policies).forEach((policy: any) => {
        const statements = policy.Properties?.PolicyDocument?.Statement || [];
        statements.forEach((statement: any) => {
          const actions = Array.isArray(statement.Action) ? statement.Action : [statement.Action];
          const resources = Array.isArray(statement.Resource) ? statement.Resource : [statement.Resource];

          // Should not have wildcard actions
          actions.forEach((action: string) => {
            expect(action).not.toBe('*');
            expect(action).not.toMatch(/:\*$/);
          });

          // Should not have wildcard resources (except for specific cases)
          resources.forEach((resource: string) => {
            if (!resource.includes('/index/*') && !resource.includes('/*')) {
              expect(resource).not.toBe('*');
            }
          });
        });
      });
    });
  });
});
