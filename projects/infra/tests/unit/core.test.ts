/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Unit tests for the Core construct's ALB / CloudFront origin / WAF configuration.
 *
 * Covers the private-ALB + CloudFront VPC origin change: the ALB must not be
 * internet-facing, CloudFront must reach it via a VPC origin rather than a
 * public DNS name, and the ALB security group must stay locked down to the
 * CloudFront-managed prefix list rather than the open internet.
 *
 * Also covers the WAF WebACL: on by default (WebACL resource created and
 * associated with the distribution), can be explicitly disabled, and when
 * enabled, scoped to CLOUDFRONT with the standard managed rule groups and the
 * SizeRestrictions_BODY override needed to avoid blocking legitimate large
 * CSV uploads.
 */

import { Template, Match } from 'aws-cdk-lib/assertions';
import { createTestApp, getTemplate } from '../fixtures/test-utils';
import { Core } from '../../lib/core';
import { ConfigSchema, Config } from '../../lib/schema';

function buildTestConfig(overrides: Record<string, unknown> = {}): Config {
  return ConfigSchema.parse({
    deploymentName: 'core-test',
    accountNumber: '123456789012',
    region: 'us-east-1',
    deploymentStage: 'dev',
    removalPolicy: 'destroy',
    logLevel: 'INFO',
    targetPlatform: 'linux/amd64',
    cognitoAuthConfig: {
      userPoolName: 'core-test-users',
      userPoolClientId: '',
      userPoolDomainName: 'core-test-auth',
    },
    loadBalancerConfig: { idleTimeout: 300 },
    alarmConfig: {
      enable: false,
      period: 1,
      threshold: 1,
      evaluationPeriods: 1,
      loggingFilterPatterns: [],
      emailAddresses: [],
    },
    ...overrides,
    restApiConfig: {
      containerConfig: {
        cpuLimit: 1024,
        memoryLimit: 2048,
        minHealthyPercent: 50,
        healthCheckConfig: {
          command: ['CMD-SHELL', 'exit 0'],
          interval: 30,
          startPeriod: 60,
          timeout: 10,
          retries: 3,
        },
      },
      healthCheckConfig: {
        path: '/api/health',
        interval: 60,
        timeout: 30,
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 10,
      },
      autoScalingConfig: {
        minCapacity: 1,
        maxCapacity: 5,
        defaultInstanceWarmup: 120,
        cooldown: 300,
        metricConfig: {
          albMetricName: 'RequestCountPerTarget',
          targetValue: 100,
          duration: 60,
          estimatedInstanceWarmup: 60,
        },
      },
    },
  });
}

describe('Core construct', () => {
  let template: Template;

  beforeAll(() => {
    const { stack } = createTestApp('CoreTestStack');
    new Core(stack, 'Core', { config: buildTestConfig() });
    template = getTemplate(stack);
  });

  describe('Application Load Balancer', () => {
    test('is internal, not internet-facing', () => {
      template.hasResourceProperties('AWS::ElasticLoadBalancingV2::LoadBalancer', {
        Scheme: 'internal',
        Type: 'application',
      });
    });

    test('security group ingress is sourced from a prefix list, not the open internet', () => {
      template.hasResourceProperties('AWS::EC2::SecurityGroupIngress', {
        SourcePrefixListId: Match.anyValue(),
        FromPort: 80,
        ToPort: 80,
      });
      template.resourcePropertiesCountIs('AWS::EC2::SecurityGroupIngress', {
        CidrIp: '0.0.0.0/0',
        FromPort: 80,
      }, 0);
    });
  });

  describe('CloudFront origin', () => {
    test('creates a VPC origin backed by the ALB', () => {
      template.hasResourceProperties('AWS::CloudFront::VpcOrigin', {
        VpcOriginEndpointConfig: Match.objectLike({
          OriginProtocolPolicy: 'http-only',
        }),
      });
      template.resourceCountIs('AWS::CloudFront::VpcOrigin', 1);
    });

    test('the /api/* origin in the distribution references the VPC origin, not a plain ALB DNS name', () => {
      template.hasResourceProperties('AWS::CloudFront::Distribution', {
        DistributionConfig: Match.objectLike({
          Origins: Match.arrayWith([
            Match.objectLike({
              VpcOriginConfig: Match.objectLike({
                VpcOriginId: Match.anyValue(),
              }),
            }),
          ]),
        }),
      });

      const origins = template.findResources('AWS::CloudFront::Distribution');
      const distribution = Object.values(origins)[0] as {
        Properties: { DistributionConfig: { Origins: unknown[] } };
      };
      const albOrigins = distribution.Properties.DistributionConfig.Origins.filter(
        (origin) => (origin as Record<string, unknown>).VpcOriginConfig !== undefined,
      );
      expect(albOrigins).toHaveLength(1);
      albOrigins.forEach((origin) => {
        expect(origin).not.toHaveProperty('CustomOriginConfig');
      });
    });
  });

  describe('WAF WebACL', () => {
    test('is created by default (wafConfig.enable defaults to true)', () => {
      template.resourceCountIs('AWS::WAFv2::WebACL', 1);
      template.hasResourceProperties('AWS::CloudFront::Distribution', {
        DistributionConfig: Match.objectLike({
          WebACLId: Match.anyValue(),
        }),
      });
    });
  });
});

describe('Core construct with WAF explicitly disabled', () => {
  let template: Template;

  beforeAll(() => {
    const { stack } = createTestApp('CoreWafDisabledTestStack');
    new Core(stack, 'Core', {
      config: buildTestConfig({ wafConfig: { enable: false } }),
    });
    template = getTemplate(stack);
  });

  test('is not created when wafConfig.enable is explicitly false', () => {
    template.resourceCountIs('AWS::WAFv2::WebACL', 0);
    template.hasResourceProperties('AWS::CloudFront::Distribution', {
      DistributionConfig: Match.objectLike({
        WebACLId: Match.absent(),
      }),
    });
  });
});

describe('Core construct with WAF enabled', () => {
  let template: Template;

  beforeAll(() => {
    const { stack } = createTestApp('CoreWafTestStack');
    new Core(stack, 'Core', {
      config: buildTestConfig({ wafConfig: { enable: true } }),
    });
    template = getTemplate(stack);
  });

  test('creates a CLOUDFRONT-scoped WebACL with the standard managed rule groups', () => {
    template.resourceCountIs('AWS::WAFv2::WebACL', 1);
    template.hasResourceProperties('AWS::WAFv2::WebACL', {
      Scope: 'CLOUDFRONT',
      DefaultAction: { Allow: {} },
      AssociationConfig: Match.objectLike({
        RequestBody: {
          CLOUDFRONT: { DefaultSizeInspectionLimit: 'KB_64' },
        },
      }),
      Rules: Match.arrayWith([
        Match.objectLike({
          Name: 'AWS-AWSManagedRulesCommonRuleSet',
          Statement: Match.objectLike({
            ManagedRuleGroupStatement: Match.objectLike({
              VendorName: 'AWS',
              Name: 'AWSManagedRulesCommonRuleSet',
              RuleActionOverrides: Match.arrayWith([
                Match.objectLike({
                  Name: 'SizeRestrictions_BODY',
                  ActionToUse: { Count: {} },
                }),
              ]),
            }),
          }),
        }),
        Match.objectLike({
          Name: 'AWS-AWSManagedRulesKnownBadInputsRuleSet',
        }),
        Match.objectLike({
          Name: 'AWS-AWSManagedRulesAmazonIpReputationList',
        }),
      ]),
    });
  });

  test('the distribution references the WebACL by ARN', () => {
    const webAcls = template.findResources('AWS::WAFv2::WebACL');
    const webAclLogicalId = Object.keys(webAcls)[0];

    template.hasResourceProperties('AWS::CloudFront::Distribution', {
      DistributionConfig: Match.objectLike({
        WebACLId: {
          'Fn::GetAtt': [webAclLogicalId, 'Arn'],
        },
      }),
    });
  });
});
