/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Models for schema validation.
/* eslint-disable @typescript-eslint/no-explicit-any */

import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import { z } from "zod";

const APP_VERSION: string = "v1";

const REMOVAL_POLICIES: Record<string, cdk.RemovalPolicy> = {
  destroy: cdk.RemovalPolicy.DESTROY,
  retain: cdk.RemovalPolicy.RETAIN,
};



/**
 * Custom security groups for application.
 *
 * @property {ec2.SecurityGroup} alb - Application load balancer security group.
 * @property {ec2.SecurityGroup} fastApiService - FastAPI Fargate service security group.
 */
export interface SecurityGroups {
  alb: ec2.SecurityGroup;
  fastApiService: ec2.SecurityGroup;
}

/**
 * Custom IAM roles for application.
 *
 * @property {iam.Role} fastApiTaskRole - FastApi ECS task role.
 */
export interface IamRoles {
  fastApiTask: iam.Role;
}

/**
 * Custom DynamoDB tables for application.
 *
 * @property {dynamodb.Table} feedback - DynamoDB table for feedback.
 * @property {dynamodb.Table} metadataSchemas - DynamoDB table for metadata schemas.
 * @property {dynamodb.Table} metadataUploadJob - DynamoDB table for metadata upload jobs.
 */
export interface DynamoDbTables {
  feedback: dynamodb.Table;
  metadataSchemas: dynamodb.Table;
  metadataUploadJob: dynamodb.Table;
}

/**
 * Custom S3 buckets for application.
 *
 * @property {s3.Bucket} website - Bucket for the website.
 * @property {s3.Bucket} validationResults - Bucket for validation results.
 * @property {s3.Bucket} schemaStorage - Bucket for schema storage.
 */
export interface S3Buckets {
  website: s3.Bucket;
  validationResults: s3.Bucket;
  schemaStorage: s3.Bucket;
}

/**
 * Configuration schema for VPC.
 *
 * @property {string} vpcId - VPC ID for application.
 * @property {string} vpcGatewayEndpointS3Id - VPC gateway endpoint S3 ID.
 * @property {string} vpcGatewayEndpointDdbId - VPC gateway endpoint DynamoDB ID.
 */
const VpcConfigSchema = z.object({
  vpcId: z
    .string()
    .optional()
    .nullable()
    .transform((value: any) => value ?? ""),
  vpcGatewayEndpointS3Id: z
    .string()
    .optional()
    .nullable()
    .transform((value: any) => value ?? ""),
  vpcGatewayEndpointDdbId: z
    .string()
    .optional()
    .nullable()
    .transform((value: any) => value ?? ""),
});

/**
 * Configuration schema for Cognito authorization.
 *
 * @property {string} userPoolName - Name of the Cognito user pool.
 * @property {string} userPoolId - ID of the Cognito user pool.
 * @property {string} userPoolClientId - ID of the Cognito user pool client.
 * @property {string} userPoolDomainName - Domain name of the Cognito user pool.
 */
const CognitoAuthConfigSchema = z
  .object({
    userPoolName: z.string().optional(),
    userPoolId: z.string().optional(),
    userPoolClientId: z.string().optional(),
    userPoolDomainName: z.string().nonempty("userPoolDomainName is required"),
  })
  .superRefine((data, ctx) => {
    if (data.userPoolName && data.userPoolId) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["userPoolId"],
        message:
          "Either `userPoolId` or `userPoolName` must be provided, but not both. \
          Set `userPoolId` to use an existing User Pool or `userPoolName` to create a new User Pool.",
      });
    }

    if (!(data.userPoolName || data.userPoolId)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["userPoolId"],
        message:
          "One of `userPoolId` or `userPoolName` must be provided. \
          Set `userPoolId` to use an existing User Pool or `userPoolName` to create a new User Pool.",
      });
    }
  });

/**
 * Configuration schema for the load balancer.
 *
 * @property {string} idleTimeout - Idle timeout in seconds.
 */
const LoadBalancerConfigSchema = z.object({
  idleTimeout: z.number().min(30).max(300).default(300),
});

/**
 * Configuration for ECS container health checks.
 *
 * @property {string[]} [command=['CMD-SHELL', 'exit 0']] - Command to run for health checks.
 * @property {number} [interval=10] - Time interval between health checks, in seconds.
 * @property {number} [startPeriod=30] - Time to wait before starting the first health check, in seconds.
 * @property {number} [timeout=5] - Maximum time allowed for each health check to complete, in seconds.
 * @property {number} [retries=3] - Number of times to retry a failed health check before considering the container
 *                                  as unhealthy.
 */
const EcsContainerHealthCheckConfigSchema = z.object({
  command: z.array(z.string()).default(["CMD-SHELL", "exit 0"]),
  interval: z.number().min(10).default(10),
  startPeriod: z.number().min(30).default(30),
  timeout: z.number().min(5).default(5),
  retries: z.number().min(3).default(3),
});

/**
 * Configuration for an ECS container.
 *
 * @property {number} [cpuLimit=1024] - CPU limit for container.
 * @property {number} [memoryLimit=2048] - Memory limit for container.
 * @property {number} [minHealthyPercent=50] - Minimum number of tasks, specified as a percentage of DesiredCount value
 *                                             that must continue to run and remain healthy during a deployment.
 * @property {EcsContainerHealthCheckConfigSchema} [healthCheckConfig={}] - Health check configuration for container.
 */
const EcsContainerConfigSchema = z.object({
  cpuLimit: z.number().default(1024),
  memoryLimit: z.number().default(2048),
  minHealthyPercent: z.number().min(25).max(100).default(50),
  healthCheckConfig: EcsContainerHealthCheckConfigSchema.default({}),
});

/**
 * Configuration schema for health checks on ECS.
 *
 * @property {string} path - Path for the health check.
 * @property {number} [interval=60] - Interval in seconds between health checks.
 * @property {number} [timeout=30] - Timeout in seconds for each health check.
 * @property {number} [healthyThresholdCount=2] - Number of consecutive successful health checks required to consider
 *                                                the target healthy.
 * @property {number} [unhealthyThresholdCount=10] - Number of consecutive failed health checks required to consider the
 *                                                  target unhealthy.
 */
const EcsHealthCheckConfigSchema = z.object({
  path: z.string(),
  interval: z.number().min(10).default(60),
  timeout: z.number().min(5).default(30),
  healthyThresholdCount: z.number().min(2).default(2),
  unhealthyThresholdCount: z.number().min(2).default(10),
});

/**
 * Configuration schema for ECS auto scaling metrics.
 *
 * @property {string} albMetricName - Name of the ALB metric.
 * @property {number} targetValue - Target value for the metric.
 * @property {number} [duration=60] - Duration in seconds for metric evaluation.
 * @property {number} [estimatedInstanceWarmup=60] - Estimated warm-up time in seconds until a newly launched instance
 *                                                    can send metrics to CloudWatch.
 *
 */
const EcsMetricConfigSchema = z.object({
  albMetricName: z.string(),
  targetValue: z.number().min(60),
  duration: z.number().min(60).default(60),
  estimatedInstanceWarmup: z.number().min(60).default(60),
});

/**
 * Configuration schema for ECS auto scaling settings.
 *
 * @property {number} [minCapacity=1] - Minimum capacity for auto scaling. Must be at least 1.
 * @property {number} [maxCapacity=5] - Maximum capacity for auto scaling. Must be at least 1.
 * @property {number} [defaultInstanceWarmup=120] - Default warm-up time in seconds until a newly launched instance can
 *                                                  send metrics to CloudWatch.
 * @property {number} [cooldown=300] - Cool down period in seconds between scaling activities.
 * @property {MetricConfig} metricConfig - Metric configuration for auto scaling.
 */
const EcsAutoScalingConfigSchema = z.object({
  minCapacity: z.number().min(1).default(1),
  maxCapacity: z.number().min(1).default(5),
  defaultInstanceWarmup: z.number().min(120).default(120),
  cooldown: z.number().min(300).default(300),
  metricConfig: EcsMetricConfigSchema,
});

/**
 * Configuration schema for REST API.
 *
 * @property {EcsContainerConfigSchema} containerConfig - Configuration for the container.
 * @property {EcsHealthCheckConfigSchema} healthCheckConfig - Health check configuration for the target group.
 * @property {EcsAutoScalingConfigSchema} autoScalingConfig - Configuration for auto scaling settings.
 */
const RestApiConfigSchema = z.object({
  containerConfig: EcsContainerConfigSchema,
  healthCheckConfig: EcsHealthCheckConfigSchema,
  autoScalingConfig: EcsAutoScalingConfigSchema,
});

/**
 * Configuration schema for CloudWatch alarms.
 *
 * @property {bool} [enable=false] - Whether to enable alarm.
 * @property {number} [period=1] - Duration in minutes to collect data.
 * @property {number} [threshold=1] - Value against which the statistic is compared.
 * @property {number} [evaluationPeriods=1] - Number of periods over which data is compared to the threshold.
 * @property {string[]} loggingFilterPatterns - Logging filter patterns to use to trigger alarm response.
 * @property {string[]} emailAddresses - Email addresses to send SNS notifications for alarm actions.
 */
const AlarmConfigSchema = z
  .object({
    enable: z.boolean().default(false),
    period: z.number().min(1).default(1),
    threshold: z.number().min(1).default(1),
    evaluationPeriods: z.number().min(1).default(1),
    loggingFilterPatterns: z.array(
      z.union([
        z.literal("WARNING"),
        z.literal("ERROR"),
        z.literal("CRITICAL"),
      ]),
    ),
    emailAddresses: z
      .array(z.string().email().or(z.null()))
      .optional()
      .nullable(),
  })
  .refine(
    (data) => {
      // If alarms are enabled, check that emailAddresses is provided and not empty
      if (
        data.enable &&
        (!data.emailAddresses || data.emailAddresses.length === 0)
      ) {
        return false;
      }
      return true;
    },
    {
      message:
        "Email addresses must be provided and not empty when the alarm is enabled.",
      path: ["emailAddresses"],
    },
  );

export type AlarmConfig = z.infer<typeof AlarmConfigSchema>;

/**
 * Configuration schema for the CloudFront WAF WebACL.
 *
 * @property {bool} [enable=false] - Whether to attach a WAF WebACL to the CloudFront distribution.
 */
const WafConfigSchema = z.object({
  enable: z.boolean().default(true),
});

export type WafConfig = z.infer<typeof WafConfigSchema>;

/**
 * Configuration schema for ECS Target Group.
 *
 * @property {EcsContainerConfigSchema} containerConfig - Configuration for the container.
 * @property {EcsHealthCheckConfigSchema} healthCheckConfig - Health check configuration for the target group.
 * @property {EcsAutoScalingConfigSchema} autoScalingConfig - Configuration for auto scaling settings.
 */
const EcsTargetGroupConfigSchema = z.object({
  containerConfig: EcsContainerConfigSchema,
  healthCheckConfig: EcsHealthCheckConfigSchema,
  autoScalingConfig: EcsAutoScalingConfigSchema,
});

export type EcsTargetGroupConfig = z.infer<typeof EcsTargetGroupConfigSchema>;

/**
 * Configuration schema for metadata validation.
 *
 * @property {string} [validationResultsBucketName] - S3 bucket for validation results.
 * @property {string} [schemaStorageBucketName] - S3 bucket for schema storage.
 * @property {string} [metadataSchemasTableName] - DynamoDB table for metadata schemas.
 * @property {string} [metadataUploadJobTableName] - DynamoDB table for upload jobs.
 * @property {string} [metadataConfigDir] - Directory containing metadata configuration files.
 */
export const MetadataConfigSchema = z.object({
  validationResultsBucketName: z.string().optional(),
  schemaStorageBucketName: z.string().optional(),
  metadataSchemasTableName: z.string().optional(),
  metadataUploadJobTableName: z.string().optional(),
  metadataConfigDir: z.string().optional(),
});

/**
 * Configuration schema for application.
 *
 * @property {string} [appName='metadata-harmonization-app'] - Name of the application.
 * @property {string} [profile=null] - AWS CLI profile for deployment.
 * @property {string} deploymentName - Name of the deployment.
 * @property {string} accountNumber - AWS account number for deployment. Must be 12 digits.
 * @property {string} region - AWS region for deployment.
 * @property {string} deploymentStage - Deployment stage for the application.
 * @property {string} removalPolicy - Removal policy for resources (destroy or retain).
 * @property {boolean} [runCdkNag=false] - Whether to run CDK Nag checks.
 * @property {string} logLevel - Log level for application.
 * @property {string} targetPlatform - Target platform for building Docker images.
 * @property {VpcConfigSchema} vpcConfig - VPC configuration.
 * @property {CognitoAuthConfigSchema} cognitoAuthConfig - Cognito auth configuration.
 * @property {LoadBalancerConfigSchema} loadBalancerConfig - Load balancer configuration.
 * @property {AlarmConfigSchema} alarmConfig - Alarm configuration.
 * @property {WafConfigSchema} wafConfig - WAF WebACL configuration.
 * @property {MetadataConfigSchema} metadataConfig - Metadata validation configuration.
 * @property {RestApiConfigSchema} restApiConfig - REST API configuration.
 * @property {Array<{ Key: string, Value: string }>} [tags=null] - Array of key-value pairs for tagging.
 * @property {string} [deploymentPrefix=null] - Prefix for deployment resources.
 */
const RawConfigSchema = z.object({
  appName: z
    .string()
    .default("metadata-harmonization-app")
    .transform((value) => value.toLowerCase()),
  profile: z
    .string()
    .optional()
    .nullable()
    .transform((value: any) => value ?? ""),
  deploymentName: z.string(),
  accountNumber: z
    .union([z.string(), z.number()])
    .transform((value) => {
      // Convert to string if it's a number
      const strValue = value.toString();

      // If it's a number, pad with leading zeros
      if (typeof value === "number") {
        return strValue.padStart(12, "0");
      }
      return strValue;
    })
    .refine((value) => value.length === 12, {
      message: "AWS account number should be 12 digits",
    }),
  region: z.string(),
  deploymentStage: z.string(),
  removalPolicy: z
    .union([z.literal("destroy"), z.literal("retain")])
    .transform((value) => REMOVAL_POLICIES[value]),
  runCdkNag: z.boolean().default(false),
  logLevel: z.union([
    z.literal("DEBUG"),
    z.literal("INFO"),
    z.literal("WARNING"),
    z.literal("ERROR"),
  ]),
  targetPlatform: z.string(),

  vpcConfig: VpcConfigSchema.optional(),
  cognitoAuthConfig: CognitoAuthConfigSchema,
  loadBalancerConfig: LoadBalancerConfigSchema,
  alarmConfig: AlarmConfigSchema,
  wafConfig: WafConfigSchema.default({}),
  metadataConfig: MetadataConfigSchema.optional(),
  restApiConfig: RestApiConfigSchema,
  tags: z
    .array(
      z.object({
        Key: z.string(),
        Value: z.string(),
      }),
    )
    .optional(),
});

/**
 * Apply transformations to the raw application configuration schema.
 *
 * @param {Object} rawConfig - Raw application configuration.
 * @returns {Object} Transformed application configuration.
 */
export const ConfigSchema = RawConfigSchema.transform((rawConfig) => {
  const deploymentPrefix = `/${rawConfig.deploymentStage}/${rawConfig.deploymentName}/${rawConfig.appName}`;

  // Initialize tags if not present; otherwise, shallow copy to prevent direct mutation
  const tags = rawConfig.tags ? [...rawConfig.tags] : [];

  // Function to check if a tag key exists and update its value or append a new tag
  const upsertTag = (key: string, value: string) => {
    const existingTagIndex = tags.findIndex((tag) => tag.Key === key);
    if (existingTagIndex !== -1) {
      tags[existingTagIndex].Value = value;
    } else {
      tags.push({ Key: key, Value: value });
    }
  };

  // Ensure essential tags are set or updated
  upsertTag("deploymentPrefix", deploymentPrefix);
  upsertTag("deploymentName", rawConfig.deploymentName);
  upsertTag("deploymentStage", rawConfig.deploymentStage);
  upsertTag("version", APP_VERSION);

  return {
    ...rawConfig,
    tags,
    deploymentPrefix,
  };
});

/**
 * Application configuration type.
 */
export type Config = z.infer<typeof ConfigSchema>;

/**
 * Basic properties required for a Construct or Stack definition in CDK.
 *
 * @property {Config} config - The application configuration.
 */
export interface BaseProps {
  config: Config;
}
