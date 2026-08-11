/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Shared CDK resources.
import * as cdk from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchactions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import { Construct } from "constructs";

import { Core } from "./core";
import { AlarmConfig, Config, EcsTargetGroupConfig } from "./schema";
import { createCdkId } from "./utils";

/**
 * Configuration properties for setting up an ECS Fargate cluster and service.
 *
 * @property {Construct} scope - Parent or owner of the construct.
 * @property {string} prefix - Prefix used for naming the CDK resources.
 * @property {ec2.Vpc} vpc - Virtual private cloud (VPC).
 * @property {iam.Role} taskRole - IAM role for the Fargate tasks.
 * @property {ec2.SecurityGroup} serviceSg - Security group for the Fargate service.
 * @property {ecs.ContainerImage} dockerImage - Docker image to be used for the container within the Fargate task.
 * @property {number} containerPort - Port that the containerized process listens on.
 * @property {Record<string, string>} containerEnvironment - Environment variables for the container.
 * @property {boolean} readonlyRootFilesystem - Whether or not the container filesystem is readonly.
 * @property {elbv2.ApplicationListener} albListener - Application Load Balancer listener.
 * @property {string[]} pathPatterns - Path patterns for ALB.
 * @property {number} priority - Priority for ALB path patterns.
 * @property {Config} config - Application configuration.
 * @property {EcsTargetGroupConfig} targetGroupConfig - Target group configuration.
 * @property {Core} core - Core construct.
 */
export interface EcsFargateClusterAndServiceConfig {
  readonly scope: Construct;
  readonly prefix: string;
  readonly vpc: ec2.Vpc;
  readonly taskRole: iam.IRole;
  readonly serviceSg: ec2.SecurityGroup;
  readonly dockerImage: ecs.ContainerImage;
  readonly containerPort: number;
  readonly containerEnvironment: Record<string, string>;
  readonly readonlyRootFilesystem: boolean;
  readonly albListener: elbv2.ApplicationListener;
  readonly pathPatterns: string[];
  readonly priority: number;
  readonly config: Config;
  readonly targetGroupConfig: EcsTargetGroupConfig;
  readonly core: Core;
}

/**
 * Creates and configures an ECS Fargate cluster and service based on provided configuration settings.
 *
 * @param {EcsFargateClusterAndServiceConfig} params - Parameters for creating the ECS Fargate cluster and service.
 * @returns {void}
 */
export function createEcsFargateClusterAndService(
  params: EcsFargateClusterAndServiceConfig,
): void {
  // Unpack configs
  const config = params.config;
  const targetGroupConfig = params.targetGroupConfig;
  const alarmConfig = config.alarmConfig;

  // Create ECS cluster
  const cluster = new ecs.Cluster(
    params.scope,
    createCdkId([params.prefix, "Cluster"]),
    {
      vpc: params.vpc,
      containerInsights: true,
    },
  );

  // Create ECS task definition
  const taskDefinition = new ecs.FargateTaskDefinition(
    params.scope,
    createCdkId([params.prefix, "FargateTaskDefinition"]),
    {
      taskRole: params.taskRole,
      cpu: targetGroupConfig.containerConfig.cpuLimit,
      memoryLimitMiB: targetGroupConfig.containerConfig.memoryLimit,
    },
  );

  // Create CloudWatch log group
  const logGroup = new logs.LogGroup(
    params.scope,
    createCdkId([params.prefix, "LogGroup"]),
    {
      retention:
        config.deploymentStage === "dev"
          ? logs.RetentionDays.ONE_WEEK
          : logs.RetentionDays.INFINITE,
      removalPolicy: config.removalPolicy,
    },
  );

  // Add container to task definition
  const containerHealthCheckConfig =
    targetGroupConfig.containerConfig.healthCheckConfig;
  taskDefinition.addContainer(
    createCdkId([params.prefix, "ContainerDefinition"]),
    {
      image: params.dockerImage,
      environment: params.containerEnvironment,
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: params.prefix,
        logGroup: logGroup,
      }),
      portMappings: [
        { containerPort: params.containerPort, protocol: ecs.Protocol.TCP },
      ],
      healthCheck: {
        command: containerHealthCheckConfig.command,
        interval: cdk.Duration.seconds(containerHealthCheckConfig.interval),
        startPeriod: cdk.Duration.seconds(
          containerHealthCheckConfig.startPeriod,
        ),
        timeout: cdk.Duration.seconds(containerHealthCheckConfig.timeout),
        retries: containerHealthCheckConfig.retries,
      },
      readonlyRootFilesystem: params.readonlyRootFilesystem,
    },
  );

  // Create ECS service
  const service = new ecs.FargateService(
    params.scope,
    createCdkId([params.prefix, "FargateService"]),
    {
      cluster: cluster,
      taskDefinition: taskDefinition,
      circuitBreaker: { rollback: true },
      securityGroups: [params.serviceSg],
      minHealthyPercent: config.restApiConfig.containerConfig.minHealthyPercent,
    },
  );

  // Add targets
  const targetGroup = new elbv2.ApplicationTargetGroup(
    params.scope,
    createCdkId([params.prefix, "ApplicationTargetGroup"]),
    {
      vpc: params.vpc,
      healthCheck: {
        path: targetGroupConfig.healthCheckConfig.path,
        interval: cdk.Duration.seconds(
          targetGroupConfig.healthCheckConfig.interval,
        ),
        timeout: cdk.Duration.seconds(
          targetGroupConfig.healthCheckConfig.timeout,
        ),
        healthyThresholdCount:
          targetGroupConfig.healthCheckConfig.healthyThresholdCount,
        unhealthyThresholdCount:
          targetGroupConfig.healthCheckConfig.unhealthyThresholdCount,
      },
      port: 80,
      targets: [service],
    },
  );

  // Add action for target group based on path patterns
  const action = elbv2.ListenerAction.forward([targetGroup]);
  params.albListener.addAction(`${params.prefix}Action`, {
    action: action,
    conditions: [elbv2.ListenerCondition.pathPatterns(params.pathPatterns)],
    priority: params.priority,
  });

  // Add autoscaling
  const autoscalingConfig = targetGroupConfig.autoScalingConfig;
  const scalableTarget = service.autoScaleTaskCount({
    minCapacity: targetGroupConfig.autoScalingConfig.minCapacity,
    maxCapacity: targetGroupConfig.autoScalingConfig.maxCapacity,
  });

  // Create scaling policy with unique name to avoid conflicts
  scalableTarget.scaleOnRequestCount(`${params.prefix}RequestCountScaling`, {
    requestsPerTarget: autoscalingConfig.metricConfig.targetValue,
    targetGroup: targetGroup,
    scaleInCooldown: cdk.Duration.seconds(autoscalingConfig.cooldown),
    scaleOutCooldown: cdk.Duration.seconds(autoscalingConfig.cooldown),
  });

  // Create CloudWatch Alarm with SNS hook
  if (alarmConfig.enable) {
    createCloudWatchAlarmAndSnsHook({
      scope: params.scope,
      prefix: params.prefix,
      logGroup: logGroup,
      config: params.config,
      alarmConfig: alarmConfig,
    });
  }
}

/**
 * Configuration properties for setting up CloudWatch Alarms with a SNS hook.
 *
 * @property {Construct} scope - Parent or owner of the construct.
 * @property {string} prefix - A prefix used for naming the CDK resources.
 * @property {logs.LogGroup} logGroup - CloudWatch Logs log group associated with the target group service.
 * @property {Config} config - Application configuration.
 * @property {AlarmConfig} alarmConfig - Configuration for the CloudWatch Alarm.
 */
export interface CloudWatchAlarmsAndSnsHookConfig {
  readonly scope: Construct;
  readonly prefix: string;
  readonly logGroup: logs.LogGroup;
  readonly config: Config;
  readonly alarmConfig: AlarmConfig;
}

/**
 * Creates and configures CloudWatch Alarms with an SNS hook based on provided configuration settings.
 *
 * @param {CloudWatchAlarmsAndSnsHookConfig} params - Parameters for creating CloudWatch Alarms with an SNS hook.
 * @returns {void}
 */
export function createCloudWatchAlarmAndSnsHook(
  params: CloudWatchAlarmsAndSnsHookConfig,
): void {
  // Unpack configs
  const config = params.config;
  const alarmConfig = params.alarmConfig;

  const errorMetricFilter = new logs.MetricFilter(
    params.scope,
    createCdkId([params.prefix, "MetricFilter"]),
    {
      logGroup: params.logGroup,
      metricNamespace: `${config.deploymentPrefix}/${params.prefix}Errors`,
      metricName: `${params.prefix}ErrorCount`,
      filterPattern: logs.FilterPattern.anyTerm(
        ...alarmConfig.loggingFilterPatterns,
      ),
      metricValue: "1",
    },
  );

  const metric = errorMetricFilter.metric({
    period: cdk.Duration.minutes(alarmConfig.period),
  });

  const topic = new sns.Topic(
    params.scope,
    createCdkId([params.prefix, "Topic"]),
    {
      displayName: `${params.prefix} Alarm: ${config.deploymentPrefix}`,
    },
  );

  (alarmConfig.emailAddresses as string[]).forEach((email: string) => {
    topic.addSubscription(new subscriptions.EmailSubscription(email));
  });

  const alarm = new cloudwatch.Alarm(
    params.scope,
    createCdkId([params.prefix, "Alarm"]),
    {
      metric: metric,
      threshold: alarmConfig.threshold,
      evaluationPeriods: alarmConfig.evaluationPeriods,
      alarmDescription: "Alarm when the error count exceeds 1 within a period",
      actionsEnabled: true,
      comparisonOperator:
        cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
    },
  );
  alarm.addAlarmAction(new cloudwatchactions.SnsAction(topic));
  alarm.addOkAction(new cloudwatchactions.SnsAction(topic));
  alarm.addInsufficientDataAction(new cloudwatchactions.SnsAction(topic));
}

export const enum ListenerRulePriority {
  // Priority must start at 1 and be less than 50000
  RestApi = 1,
}
