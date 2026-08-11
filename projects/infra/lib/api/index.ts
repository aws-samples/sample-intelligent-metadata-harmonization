/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// REST API construct.
import * as path from "path";

import * as ecs from "aws-cdk-lib/aws-ecs";
import { Construct } from "constructs";

import { Core } from "../core";
import { BaseProps } from "../schema";
import {
  createEcsFargateClusterAndService,
  ListenerRulePriority,
} from "../shared-resources";

/**
 * Properties of RestApi construct.
 *
 * @property {Core} core - Core Construct.
 */
interface RestApiProps extends BaseProps {
  readonly core: Core;
}

/**
 * RestApi construct.
 */
export class RestApi extends Construct {
  /**
   * @param {Construct} scope - Parent or owner of the construct.
   * @param {string} id - Unique identifier for the construct within its scope.
   * @param {RestApiProps} props - Properties of the construct.
   */
  constructor(scope: Construct, id: string, props: RestApiProps) {
    super(scope, id);

    const { config, core } = props;
    const prefix = "RestApi";
    // eslint-disable-next-line
    const targetGroupConfig = config.restApiConfig;
    const vpc = core.vpc;
    const taskRole = core.iamRoles.fastApiTask;
    const serviceSg = core.securityGroups.fastApiService;
    const projectRoot = path.resolve(process.cwd(), "../../");
    const dockerImage = ecs.ContainerImage.fromAsset(projectRoot, {
      file: "projects/infra/lib/api/Dockerfile",
    });
    const containerEnvironment = {
      // Basic AWS and API configuration
      AWS_REGION: config.region,
      LOG_LEVEL: config.logLevel,
      AUTHORITY: core.apiAuthority,
      CLIENT_ID: core.clientId,
      API_ENABLE_AUTH: true.toString(),

      // DynamoDB table names
      METADATA_SCHEMAS_TABLE: core.ddbTables.metadataSchemas.tableName,
      PROCESSOR_JOB_STATUS_TABLE_NAME: core.ddbTables.metadataUploadJob.tableName,

      // S3 bucket names
      PROCESSOR_RESULTS_S3_BUCKET: core.s3Buckets.validationResults.bucketName,
      PROCESSOR_SESSION_S3_BUCKET: core.s3Buckets.validationResults.bucketName,
      SCHEMA_BUCKET: core.s3Buckets.schemaStorage.bucketName,

      PROCESSOR_ENABLE_MEMORY_CACHE: "true",
      PROCESSOR_SCHEMA_DIRECTORY: "./data/schema",
      PROCESSOR_LOCAL_DEVELOPMENT_MODE: "false"
    };
    const albListener = core.albListener;
    const pathPatterns = ["/api/*"];
    const priority = ListenerRulePriority.RestApi;

    // Create ECS cluster and Fargate service
    createEcsFargateClusterAndService({
      scope: this,
      prefix: prefix,
      vpc: vpc,
      taskRole: taskRole,
      serviceSg: serviceSg,
      dockerImage: dockerImage,
      containerPort: 8080,
      containerEnvironment: containerEnvironment,
      readonlyRootFilesystem: false,
      albListener: albListener,
      pathPatterns: pathPatterns,
      priority: priority,
      config: config,
      targetGroupConfig: targetGroupConfig,
      core: core,
    });
  }
}
