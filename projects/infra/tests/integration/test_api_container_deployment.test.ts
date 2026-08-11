/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
/**
 * Integration tests for API container deployment and health checks
 */

import { Template, Match } from 'aws-cdk-lib/assertions';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Alarm, TreatMissingData } from 'aws-cdk-lib/aws-cloudwatch';
import { createTestApp, getTemplate, createMockConfig } from '../fixtures/test-utils';

// Mock HTTP requests for health check testing
jest.mock('https', () => ({
  get: jest.fn()
}));

describe('API Container Deployment Integration Tests', () => {
  let app: any;
  let stack: any;
  let template: Template;
  let config: any;
  let mockHttps: any;

  beforeEach(() => {
    const testApp = createTestApp('ApiContainerTestStack');
    app = testApp.app;
    stack = testApp.stack;
    config = createMockConfig();
    mockHttps = require('https');

    jest.clearAllMocks();
  });

  describe('ECS Service Deployment', () => {
    test('should create complete ECS service with all required components', () => {
      // Create VPC
      const vpc = new ec2.Vpc(stack, 'Vpc', {
        maxAzs: 2,
        natGateways: 1,
      });

      // Create ECS cluster
      const cluster = new ecs.Cluster(stack, 'Cluster', {
        vpc: vpc,
      });

      // Create infrastructure resources
      const metadataSchemasTable = new dynamodb.Table(stack, 'MetadataSchemas', {
        partitionKey: {
          name: 'core_schema_id',
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      });

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      // Create task definition
      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      const container = taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        environment: {
          AWS_REGION: config.region,
          METADATA_SCHEMAS_TABLE: metadataSchemasTable.tableName,
          VALIDATION_RESULTS_BUCKET: validationResultsBucket.bucketName,
          LOG_LEVEL: config.logLevel,
          API_ENABLE_AUTH: 'true',
        },
        logging: ecs.LogDrivers.awsLogs({
          streamPrefix: 'metadata-api',
        }),
      });

      container.addPortMappings({
        containerPort: 8080,
        protocol: ecs.Protocol.TCP,
      });

      // Grant permissions
      metadataSchemasTable.grantReadWriteData(taskDefinition.taskRole);
      validationResultsBucket.grantReadWrite(taskDefinition.taskRole);

      // Create Fargate service
      const service = new ecs.FargateService(stack, 'Service', {
        cluster: cluster,
        taskDefinition: taskDefinition,
        desiredCount: 2,
        assignPublicIp: false,
        healthCheckGracePeriod: require('aws-cdk-lib').Duration.seconds(60),
      });

      template = getTemplate(stack);

      // Verify all components are created
      template.resourceCountIs('AWS::EC2::VPC', 1);
      template.resourceCountIs('AWS::ECS::Cluster', 1);
      template.resourceCountIs('AWS::ECS::TaskDefinition', 1);
      template.resourceCountIs('AWS::ECS::Service', 1);
      template.resourceCountIs('AWS::DynamoDB::Table', 1);
      template.resourceCountIs('AWS::S3::Bucket', 1);

      // Verify task definition configuration
      template.hasResourceProperties('AWS::ECS::TaskDefinition', {
        Family: Match.stringLikeRegexp('TaskDefinition'),
        NetworkMode: 'awsvpc',
        RequiresCompatibilities: ['FARGATE'],
        Cpu: '1024',
        Memory: '2048',
        ContainerDefinitions: [{
          Name: 'ApiContainer',
          Image: 'metadata-harmonization-api:latest',
          PortMappings: [{
            ContainerPort: 8080,
            Protocol: 'tcp'
          }],
          Environment: Match.arrayWith([
            Match.objectLike({ Name: 'AWS_REGION', Value: 'us-east-1' }),
            Match.objectLike({ Name: 'LOG_LEVEL', Value: 'DEBUG' }),
            Match.objectLike({ Name: 'API_ENABLE_AUTH', Value: 'true' }),
          ])
        }]
      });

      // Verify service configuration
      template.hasResourceProperties('AWS::ECS::Service', {
        DesiredCount: 2,
        LaunchType: 'FARGATE',
        NetworkConfiguration: {
          AwsvpcConfiguration: {
            AssignPublicIp: 'DISABLED',
          }
        }
      });
    });

    test('should configure container with correct environment variables', () => {
      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

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

      const validationResultsBucket = new s3.Bucket(stack, 'ValidationResults', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const schemaStorageBucket = new s3.Bucket(stack, 'SchemaStorage', {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      });

      const container = taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        environment: {
          AWS_REGION: config.region,
          LOG_LEVEL: config.logLevel,
          API_ENABLE_AUTH: 'true',

          // DynamoDB table names
          METADATA_SCHEMAS_TABLE: metadataSchemasTable.tableName,
          METADATA_UPLOAD_JOB_TABLE: metadataUploadJobTable.tableName,

          // S3 bucket names
          VALIDATION_RESULTS_BUCKET: validationResultsBucket.bucketName,
          SCHEMA_STORAGE_BUCKET: schemaStorageBucket.bucketName,

          // Authentication
          AUTHORITY: config.cognito.userPoolId,
          CLIENT_ID: config.cognito.userPoolClientId,
        },
      });

      template = getTemplate(stack);

      // Verify environment variables
      template.hasResourceProperties('AWS::ECS::TaskDefinition', {
        ContainerDefinitions: [{
          Environment: Match.arrayWith([
            Match.objectLike({ Name: 'AWS_REGION', Value: 'us-east-1' }),
            Match.objectLike({ Name: 'LOG_LEVEL', Value: 'DEBUG' }),
            Match.objectLike({ Name: 'API_ENABLE_AUTH', Value: 'true' }),
            Match.objectLike({ Name: 'AUTHORITY', Value: 'us-east-1_testpool' }),
            Match.objectLike({ Name: 'CLIENT_ID', Value: 'test-client-id' }),
          ])
        }]
      });

      // Verify no database-related environment variables
      const taskDef = template.findResources('AWS::ECS::TaskDefinition');
      const containerDef = Object.values(taskDef)[0] as any;
      const environment = containerDef.Properties.ContainerDefinitions[0].Environment;

      const envNames = environment.map((env: any) => env.Name);
      expect(envNames).not.toContain('DB_HOST');
      expect(envNames).not.toContain('DB_PORT');
      expect(envNames).not.toContain('DB_NAME');
      expect(envNames).not.toContain('DB_USERNAME');
      expect(envNames).not.toContain('DB_PASSWORD_SECRET_ARN');
    });

    test('should configure proper health checks', () => {
      const vpc = new ec2.Vpc(stack, 'Vpc', { maxAzs: 2 });
      const cluster = new ecs.Cluster(stack, 'Cluster', { vpc });

      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      const container = taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        healthCheck: {
          command: [
            'CMD-SHELL',
            'curl -f http://localhost:8080/api/v1/health || exit 1'
          ],
          interval: require('aws-cdk-lib').Duration.seconds(30),
          timeout: require('aws-cdk-lib').Duration.seconds(5),
          retries: 3,
          startPeriod: require('aws-cdk-lib').Duration.seconds(60),
        },
      });

      container.addPortMappings({
        containerPort: 8080,
        protocol: ecs.Protocol.TCP,
      });

      const service = new ecs.FargateService(stack, 'Service', {
        cluster,
        taskDefinition,
        healthCheckGracePeriod: require('aws-cdk-lib').Duration.seconds(120),
      });

      template = getTemplate(stack);

      // Verify health check configuration
      template.hasResourceProperties('AWS::ECS::TaskDefinition', {
        ContainerDefinitions: [{
          HealthCheck: {
            Command: [
              'CMD-SHELL',
              'curl -f http://localhost:8080/api/v1/health || exit 1'
            ],
            Interval: 30,
            Timeout: 5,
            Retries: 3,
            StartPeriod: 60
          }
        }]
      });

      // Verify service health check grace period
      template.hasResourceProperties('AWS::ECS::Service', {
        HealthCheckGracePeriodSeconds: 120
      });
    });
  });

  describe('Load Balancer Integration', () => {
    test('should integrate with Application Load Balancer', () => {
      const vpc = new ec2.Vpc(stack, 'Vpc', { maxAzs: 2 });
      const cluster = new ecs.Cluster(stack, 'Cluster', { vpc });

      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      const container = taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
      });

      container.addPortMappings({
        containerPort: 8080,
        protocol: ecs.Protocol.TCP,
      });

      const service = new ecs.FargateService(stack, 'Service', {
        cluster,
        taskDefinition,
      });

      // Create ALB
      const alb = new elbv2.ApplicationLoadBalancer(stack, 'ALB', {
        vpc,
        internetFacing: true,
      });

      const listener = alb.addListener('Listener', {
        port: 443,
        protocol: elbv2.ApplicationProtocol.HTTPS,
        certificates: [{
          certificateArn: config.cloudFront.certificateArn,
        }],
      });

      const targetGroup = listener.addTargets('ApiTargets', {
        port: 8080,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targets: [service],
        healthCheck: {
          enabled: true,
          path: '/api/health',
          protocol: elbv2.Protocol.HTTP,
          healthyHttpCodes: '200',
          interval: require('aws-cdk-lib').Duration.seconds(30),
          timeout: require('aws-cdk-lib').Duration.seconds(5),
          healthyThresholdCount: 2,
          unhealthyThresholdCount: 3,
        },
      });

      template = getTemplate(stack);

      // Verify ALB creation
      template.resourceCountIs('AWS::ElasticLoadBalancingV2::LoadBalancer', 1);
      template.resourceCountIs('AWS::ElasticLoadBalancingV2::Listener', 1);
      template.resourceCountIs('AWS::ElasticLoadBalancingV2::TargetGroup', 1);

      // Verify ALB configuration
      template.hasResourceProperties('AWS::ElasticLoadBalancingV2::LoadBalancer', {
        Scheme: 'internet-facing',
        Type: 'application'
      });

      // Verify listener configuration
      template.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
        Port: 443,
        Protocol: 'HTTPS',
        Certificates: [{
          CertificateArn: config.cloudFront.certificateArn
        }]
      });

      // Verify target group health check
      template.hasResourceProperties('AWS::ElasticLoadBalancingV2::TargetGroup', {
        Port: 8080,
        Protocol: 'HTTP',
        TargetType: 'ip',
        HealthCheckEnabled: true,
        HealthCheckPath: '/api/health',
        HealthCheckProtocol: 'HTTP',
        HealthCheckIntervalSeconds: 30,
        HealthCheckTimeoutSeconds: 5,
        HealthyThresholdCount: 2,
        UnhealthyThresholdCount: 3,
        Matcher: {
          HttpCode: '200'
        }
      });
    });

    test('should configure security groups for ALB and ECS service', () => {
      const vpc = new ec2.Vpc(stack, 'Vpc', { maxAzs: 2 });

      // Create security groups
      const albSecurityGroup = new ec2.SecurityGroup(stack, 'ALBSecurityGroup', {
        vpc,
        description: 'Security group for Application Load Balancer',
      });

      albSecurityGroup.addIngressRule(
        ec2.Peer.anyIpv4(),
        ec2.Port.tcp(443),
        'Allow HTTPS traffic from internet'
      );

      const ecsSecurityGroup = new ec2.SecurityGroup(stack, 'ECSSecurityGroup', {
        vpc,
        description: 'Security group for ECS service',
      });

      ecsSecurityGroup.addIngressRule(
        albSecurityGroup,
        ec2.Port.tcp(8080),
        'Allow traffic from ALB'
      );

      const cluster = new ecs.Cluster(stack, 'Cluster', { vpc });

      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        portMappings: [{
          containerPort: 8080,
          protocol: ecs.Protocol.TCP,
        }],
      });

      const service = new ecs.FargateService(stack, 'Service', {
        cluster,
        taskDefinition,
        securityGroups: [ecsSecurityGroup],
      });

      template = getTemplate(stack);

      // Verify security groups exist (VPC creates additional default SG)
      const securityGroups = template.findResources('AWS::EC2::SecurityGroup');
      expect(Object.keys(securityGroups).length).toBeGreaterThanOrEqual(2);

      // Verify ECS security group ingress rule from ALB
      template.hasResourceProperties('AWS::EC2::SecurityGroupIngress', {
        IpProtocol: 'tcp',
        FromPort: 8080,
        ToPort: 8080,
      });
    });
  });

  describe('Container Health Checks', () => {
    test('should perform health checks on metadata validation endpoints', async () => {
      // Mock successful health check response
      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        const mockResponse = {
          statusCode: 200,
          on: jest.fn((event: string, handler: Function) => {
            if (event === 'data') {
              handler(JSON.stringify({
                status: 'healthy',
                timestamp: '2024-01-01T00:00:00Z',
                services: {
                  dynamodb: 'healthy',
                  s3: 'healthy'
                }
              }));
            } else if (event === 'end') {
              handler();
            }
          })
        };
        callback(mockResponse);
        return { on: jest.fn() };
      });

      const performHealthCheck = async (endpoint: string): Promise<{
        status: string;
        services: Record<string, string>;
      }> => {
        return new Promise((resolve, reject) => {
          mockHttps.get(endpoint, (response: any) => {
            let data = '';

            response.on('data', (chunk: string) => {
              data += chunk;
            });

            response.on('end', () => {
              try {
                const result = JSON.parse(data);
                if (response.statusCode === 200) {
                  resolve(result);
                } else {
                  reject(new Error(`Health check failed with status ${response.statusCode}`));
                }
              } catch (error) {
                reject(error);
              }
            });
          }).on('error', reject);
        });
      };

      // Test health check
      const healthResult = await performHealthCheck('https://test-api.example.com/api/health');

      expect(healthResult.status).toBe('healthy');
      expect(healthResult.services.dynamodb).toBe('healthy');
      expect(healthResult.services.s3).toBe('healthy');
      expect(mockHttps.get).toHaveBeenCalledWith(
        'https://test-api.example.com/api/health',
        expect.any(Function)
      );
    });

    test('should check specific metadata validation endpoints', async () => {
      // Mock responses for different endpoints
      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        let responseData = {};

        if (url.includes('/api/v1/metadata/schema')) {
          responseData = { schemas: ['cyclospora_core_v1', 'flu_core_v1'] };
        } else if (url.includes('/api/v1/metadata/validate')) {
          responseData = { validation_service: 'available' };
        }

        const mockResponse = {
          statusCode: 200,
          on: jest.fn((event: string, handler: Function) => {
            if (event === 'data') {
              handler(JSON.stringify(responseData));
            } else if (event === 'end') {
              handler();
            }
          })
        };
        callback(mockResponse);
        return { on: jest.fn() };
      });

      const checkEndpoint = async (endpoint: string): Promise<any> => {
        return new Promise((resolve, reject) => {
          mockHttps.get(endpoint, (response: any) => {
            let data = '';

            response.on('data', (chunk: string) => {
              data += chunk;
            });

            response.on('end', () => {
              try {
                resolve(JSON.parse(data));
              } catch (error) {
                reject(error);
              }
            });
          }).on('error', reject);
        });
      };

      // Test schema endpoint
      const schemaResult = await checkEndpoint('https://test-api.example.com/api/v1/metadata/schema');
      expect(schemaResult.schemas).toContain('cyclospora_core_v1');

      // Test validation endpoint
      const validationResult = await checkEndpoint('https://test-api.example.com/api/v1/metadata/validate');
      expect(validationResult.validation_service).toBe('available');

      expect(mockHttps.get).toHaveBeenCalledTimes(2);
    });


    test('should handle health check failures gracefully', async () => {
      // Mock health check failure
      mockHttps.get.mockImplementation((url: string, callback: Function) => {
        const mockResponse = {
          statusCode: 503,
          on: jest.fn((event: string, handler: Function) => {
            if (event === 'data') {
              handler(JSON.stringify({
                status: 'unhealthy',
                error: 'DynamoDB connection failed'
              }));
            } else if (event === 'end') {
              handler();
            }
          })
        };
        callback(mockResponse);
        return { on: jest.fn() };
      });

      const performHealthCheck = async (endpoint: string): Promise<{
        healthy: boolean;
        error?: string;
      }> => {
        return new Promise((resolve) => {
          mockHttps.get(endpoint, (response: any) => {
            let data = '';

            response.on('data', (chunk: string) => {
              data += chunk;
            });

            response.on('end', () => {
              try {
                const result = JSON.parse(data);
                resolve({
                  healthy: response.statusCode === 200,
                  error: result.error
                });
              } catch (error) {
                resolve({
                  healthy: false,
                  error: 'Invalid response format'
                });
              }
            });
          }).on('error', () => {
            resolve({
              healthy: false,
              error: 'Connection failed'
            });
          });
        });
      };

      const healthResult = await performHealthCheck('https://test-api.example.com/api/health');

      expect(healthResult.healthy).toBe(false);
      expect(healthResult.error).toBe('DynamoDB connection failed');
    });
  });

  describe('Auto Scaling Configuration', () => {
    test('should configure auto scaling for ECS service', () => {
      const vpc = new ec2.Vpc(stack, 'Vpc', { maxAzs: 2 });
      const cluster = new ecs.Cluster(stack, 'Cluster', { vpc });

      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        portMappings: [{
          containerPort: 8080,
          protocol: ecs.Protocol.TCP,
        }],
      });

      const service = new ecs.FargateService(stack, 'Service', {
        cluster,
        taskDefinition,
        desiredCount: 2,
      });

      // Configure auto scaling
      const scaling = service.autoScaleTaskCount({
        minCapacity: 2,
        maxCapacity: 10,
      });

      scaling.scaleOnCpuUtilization('CpuScaling', {
        targetUtilizationPercent: 70,
        scaleInCooldown: require('aws-cdk-lib').Duration.seconds(300),
        scaleOutCooldown: require('aws-cdk-lib').Duration.seconds(60),
      });

      scaling.scaleOnMemoryUtilization('MemoryScaling', {
        targetUtilizationPercent: 80,
        scaleInCooldown: require('aws-cdk-lib').Duration.seconds(300),
        scaleOutCooldown: require('aws-cdk-lib').Duration.seconds(60),
      });

      template = getTemplate(stack);

      // Verify auto scaling target
      template.hasResourceProperties('AWS::ApplicationAutoScaling::ScalableTarget', {
        ServiceNamespace: 'ecs',
        ScalableDimension: 'ecs:service:DesiredCount',
        MinCapacity: 2,
        MaxCapacity: 10
      });

      // Verify CPU scaling policy
      template.hasResourceProperties('AWS::ApplicationAutoScaling::ScalingPolicy', {
        PolicyType: 'TargetTrackingScaling',
        TargetTrackingScalingPolicyConfiguration: {
          TargetValue: 70,
          PredefinedMetricSpecification: {
            PredefinedMetricType: 'ECSServiceAverageCPUUtilization'
          },
          ScaleInCooldown: 300,
          ScaleOutCooldown: 60
        }
      });

      // Verify memory scaling policy
      template.hasResourceProperties('AWS::ApplicationAutoScaling::ScalingPolicy', {
        PolicyType: 'TargetTrackingScaling',
        TargetTrackingScalingPolicyConfiguration: {
          TargetValue: 80,
          PredefinedMetricSpecification: {
            PredefinedMetricType: 'ECSServiceAverageMemoryUtilization'
          },
          ScaleInCooldown: 300,
          ScaleOutCooldown: 60
        }
      });
    });
  });

  describe('Logging and Monitoring', () => {
    test('should configure CloudWatch logging for containers', () => {
      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      const container = taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
        logging: ecs.LogDrivers.awsLogs({
          streamPrefix: 'metadata-api',
          logRetention: require('aws-cdk-lib/aws-logs').RetentionDays.ONE_MONTH,
        }),
      });

      template = getTemplate(stack);

      // Verify log group creation
      template.hasResourceProperties('AWS::Logs::LogGroup', {
        RetentionInDays: 30
      });

      // Verify container logging configuration
      template.hasResourceProperties('AWS::ECS::TaskDefinition', {
        ContainerDefinitions: [{
          LogConfiguration: {
            LogDriver: 'awslogs',
            Options: Match.objectLike({
              'awslogs-stream-prefix': 'metadata-api'
            })
          }
        }]
      });
    });

    test('should create CloudWatch alarms for service monitoring', () => {
      const vpc = new ec2.Vpc(stack, 'Vpc', { maxAzs: 2 });
      const cluster = new ecs.Cluster(stack, 'Cluster', { vpc });

      const taskDefinition = new ecs.FargateTaskDefinition(stack, 'TaskDefinition', {
        memoryLimitMiB: 2048,
        cpu: 1024,
      });

      taskDefinition.addContainer('ApiContainer', {
        image: ecs.ContainerImage.fromRegistry('metadata-harmonization-api:latest'),
      });

      const service = new ecs.FargateService(stack, 'Service', {
        cluster,
        taskDefinition,
      });

      // Create CloudWatch alarms
      const cpuAlarm = new Alarm(stack, 'HighCpuAlarm', {
        metric: service.metricCpuUtilization(),
        threshold: 80,
        evaluationPeriods: 2,
        treatMissingData: TreatMissingData.NOT_BREACHING,
      });

      const memoryAlarm = new Alarm(stack, 'HighMemoryAlarm', {
        metric: service.metricMemoryUtilization(),
        threshold: 85,
        evaluationPeriods: 2,
        treatMissingData: TreatMissingData.NOT_BREACHING,
      });

      template = getTemplate(stack);

      // Verify CloudWatch alarms
      template.resourceCountIs('AWS::CloudWatch::Alarm', 2);

      template.hasResourceProperties('AWS::CloudWatch::Alarm', {
        MetricName: 'CPUUtilization',
        Namespace: 'AWS/ECS',
        Threshold: 80,
        EvaluationPeriods: 2,
        TreatMissingData: 'notBreaching'
      });

      template.hasResourceProperties('AWS::CloudWatch::Alarm', {
        MetricName: 'MemoryUtilization',
        Namespace: 'AWS/ECS',
        Threshold: 85,
        EvaluationPeriods: 2,
        TreatMissingData: 'notBreaching'
      });
    });
  });
});
