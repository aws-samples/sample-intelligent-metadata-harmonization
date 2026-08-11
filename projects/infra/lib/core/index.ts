/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Core construct.
/* eslint-disable @typescript-eslint/no-empty-object-type */
import * as cdk from "aws-cdk-lib";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as wafv2 from "aws-cdk-lib/aws-wafv2";

import { Construct } from "constructs";

import {
  BaseProps,
  DynamoDbTables,
  IamRoles,
  SecurityGroups,
  S3Buckets,
} from "../schema";
import { createCdkId, getIamPolicyStatements } from "../utils";

/**
 * Properties of Core Construct.
 */
interface CoreProps extends BaseProps { }

/**
 * Core construct.
 *
 * @property {ec2.Vpc} vpc - Virtual private cloud.
 * @property {SecurityGroups} securityGroups - Security groups for application.
 * @property {IamRoles} iamRoles - IAM roles for application.
 * @property {S3Buckets} s3Buckets - S3 buckets for application.
 * @property {DynamoDbTables} ddbTables - DynamoDB tables for application.
 * @property {elbv2.ApplicationListener} albListener - Application Load Balancer listener.
 * @property {cloudfront.Distribution} distribution - CloudFront distribution.
 * @property {string} applicationUri - Application URI.
 * @property {string} apiAuthority - Authority for authentication.
 * @property {string} clientId - Client ID for authentication.
 * @property {string} userPoolDomainUrl - Cognito hosted UI URL.
 */
export class Core extends Construct {
  public readonly vpc: ec2.Vpc;
  public readonly securityGroups: SecurityGroups;
  public readonly iamRoles: IamRoles;
  public readonly s3Buckets: S3Buckets;
  public readonly ddbTables: DynamoDbTables;
  public readonly albListener: elbv2.ApplicationListener;
  public readonly distribution: cloudfront.Distribution;
  public readonly applicationUri: string;
  public readonly apiAuthority: string;
  public readonly clientId: string;
  public readonly userPoolDomainUrl: string;
  /**
   * @param {Construct} scope - Parent or owner of the construct.
   * @param {string} id - Unique identifier for the construct within its scope.
   * @param {CoreProps} props - Properties for the construct.
   */
  constructor(scope: Construct, id: string, props: CoreProps) {
    super(scope, id);
    const { config } = props;

    // Create VPC
    let vpc;
    if (!config.vpcConfig?.vpcId) {
      vpc = new ec2.Vpc(this, "Vpc", {
        maxAzs: 2,
        ipAddresses: ec2.IpAddresses.cidr("10.0.0.0/16"),
        natGatewayProvider: ec2.NatProvider.gateway(),
        natGateways: 1,
        subnetConfiguration: [
          {
            subnetType: ec2.SubnetType.PUBLIC,
            name: "public",
            cidrMask: 24,
          },
          {
            subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
            name: "privateIsolated",
            cidrMask: 24,
          },
          {
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
            name: "private",
            cidrMask: 24,
          },
        ],
      });
    } else {
      vpc = ec2.Vpc.fromLookup(this, "Vpc", {
        vpcId: config.vpcConfig.vpcId,
      }) as ec2.Vpc;
    }

    // Create a log group for VPC Flow Logs
    const flowLogsGroup = new logs.LogGroup(this, "VpcFlowLogsGroup", {
      retention:
        config.deploymentStage === "dev"
          ? logs.RetentionDays.ONE_WEEK
          : logs.RetentionDays.INFINITE,
      removalPolicy: config.removalPolicy,
    });

    // Add Flow Logs to VPC
    new ec2.FlowLog(this, "VpcFlowLogs", {
      resourceType: ec2.FlowLogResourceType.fromVpc(vpc),
      destination: ec2.FlowLogDestination.toCloudWatchLogs(flowLogsGroup),
      trafficType: ec2.FlowLogTrafficType.ALL,
    });

    // Create VPC endpoints
    if (!config.vpcConfig?.vpcGatewayEndpointS3Id) {
      // Create the S3 Gateway Endpoint if not already deployed
      vpc.addGatewayEndpoint("GatewayEndpointS3", {
        service: ec2.GatewayVpcEndpointAwsService.S3,
      });
    }

    // Create the DDB Gateway Endpoint if not already deployed
    if (!config.vpcConfig?.vpcGatewayEndpointDdbId) {
      vpc.addGatewayEndpoint("GatewayEndpointDdb", {
        service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
      });
    }

    // Create security groups
    const albSg = new ec2.SecurityGroup(this, "AlbSg", {
      vpc: vpc,
      description: "Security group for the application load balancer",
      allowAllOutbound: true,
    });

    const fastApiServiceSg = new ec2.SecurityGroup(this, "FastApiServiceSg", {
      vpc: vpc,
      description: "Security group for the FastAPI Fargate service",
    });



    // Get CloudFront prefix list from specified region
    const cloudFrontPrefixList = ec2.PrefixList.fromLookup(
      this,
      "CloudFrontPrefixList",
      {
        prefixListName: "com.amazonaws.global.cloudfront.origin-facing",
      },
    );

    albSg.addIngressRule(
      ec2.Peer.prefixList(cloudFrontPrefixList.prefixListId),
      ec2.Port.tcp(80),
      `Allow HTTP inbound from CloudFront (${config.region})`,
    );

    // Allow traffic from within VPC for dev deployments
    if (config.deploymentStage === "dev") {
      albSg.addIngressRule(
        ec2.Peer.ipv4(vpc.vpcCidrBlock),
        ec2.Port.tcp(80),
        "Allow traffic from within VPC",
      );
    }

    // Create IAM roles
    let prefix = "RestApi";
    const statements = getIamPolicyStatements("ecs");
    const fastApiTaskRole = new iam.Role(this, createCdkId([prefix, "Role"]), {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: `Allow REST API ECS tasks access to AWS resources`,
      inlinePolicies: {
        [createCdkId([prefix, "RoleInlinePolicy"])]: new iam.PolicyDocument({
          statements: statements,
        }),
      },
    });

    // Create S3 buckets
    const accessLogsBucket = new s3.Bucket(this, "AccessLogsBucket", {
      removalPolicy: config.removalPolicy,
      autoDeleteObjects: config.deploymentStage === "dev",
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      accessControl: s3.BucketAccessControl.LOG_DELIVERY_WRITE,
    });

    const websiteBucket = new s3.Bucket(this, "WebsiteBucket", {
      removalPolicy: config.removalPolicy,
      autoDeleteObjects: config.deploymentStage === "dev",
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      serverAccessLogsBucket: accessLogsBucket,
      serverAccessLogsPrefix: "website-bucket-logs/",
    });

    // Create validation results bucket
    const validationResultsBucket = new s3.Bucket(this, "ValidationResults", {
      removalPolicy: config.removalPolicy,
      autoDeleteObjects: config.deploymentStage === "dev",
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      serverAccessLogsBucket: accessLogsBucket,
      serverAccessLogsPrefix: "validation-results-logs/",
    });

    // Create schema storage bucket
    const schemaStorageBucket = new s3.Bucket(this, "SchemaStorage", {
      removalPolicy: config.removalPolicy,
      autoDeleteObjects: config.deploymentStage === "dev",
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      serverAccessLogsBucket: accessLogsBucket,
      serverAccessLogsPrefix: "schema-storage-logs/",
    });

    const feedbackTable = new dynamodb.Table(this, "Feedback", {
      partitionKey: {
        name: "feedback_id",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: config.removalPolicy,
    });
    feedbackTable.addGlobalSecondaryIndex({
      indexName: "by_model_id",
      partitionKey: {
        name: "model_id",
        type: dynamodb.AttributeType.STRING,
      },
    });
    feedbackTable.grantReadWriteData(fastApiTaskRole);

    // Create METADATA_SCHEMAS_TABLE
    const metadataSchemasTable = new dynamodb.Table(this, "MetadataSchemas", {
      partitionKey: {
        name: "core_schema_id",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: config.removalPolicy,
    });
    metadataSchemasTable.grantReadWriteData(fastApiTaskRole);

    // Create METADATA_UPLOAD_JOB table
    const metadataUploadJobTable = new dynamodb.Table(this, "MetadataUploadJob", {
      partitionKey: {
        name: "job_id",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: config.removalPolicy,
    });

    // Add GSI for user queries
    metadataUploadJobTable.addGlobalSecondaryIndex({
      indexName: "user-id-index",
      partitionKey: {
        name: "user_id",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "created_at",
        type: dynamodb.AttributeType.STRING,
      },
    });
    metadataUploadJobTable.grantReadWriteData(fastApiTaskRole);

    // Grant S3 permissions
    validationResultsBucket.grantReadWrite(fastApiTaskRole);
    schemaStorageBucket.grantRead(fastApiTaskRole);


    // Create application load balancer
    const alb = new elbv2.ApplicationLoadBalancer(this, "Alb", {
      vpc: vpc,
      securityGroup: albSg,
      internetFacing: false,
      idleTimeout: cdk.Duration.seconds(config.loadBalancerConfig.idleTimeout),
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
    });
    alb.logAccessLogs(accessLogsBucket, "alb-logs");

    // Add listener
    const albListener = alb.addListener("AlbListener", {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      open: false,
    });

    // Add default action
    albListener.addAction("IngressAlbDefaultAction", {
      action: elbv2.ListenerAction.fixedResponse(404, {
        contentType: "text/plain",
        messageBody: "Cannot route your request; no matching target found.",
      }),
    });

    // Create CloudFront distribution
    prefix = config.deploymentPrefix.replace("/", "-");

    // Create WAF WebACL, if enabled. Scope must be CLOUDFRONT, which requires
    // this construct to be declared in us-east-1 -- true for every deployment
    // stage in config.yaml today.
    let webAcl: wafv2.CfnWebACL | undefined;
    if (config.wafConfig.enable) {
      webAcl = new wafv2.CfnWebACL(this, "WebAcl", {
        defaultAction: { allow: {} },
        scope: "CLOUDFRONT",
        visibilityConfig: {
          sampledRequestsEnabled: true,
          cloudWatchMetricsEnabled: true,
          metricName: createCdkId([prefix, "WebAcl"]),
        },
        associationConfig: {
          // CloudFront forwards at most this much of the request body to WAF
          // for inspection, regardless of any per-path rule. KB_64 is the max
          // allowed. Uploads here go up to 50MB (api/config.py max_file_size_mb),
          // so SizeRestrictions_BODY below is overridden to Count rather than
          // Block -- inspecting only the first 64KB of a legitimate large CSV
          // upload would otherwise flag and block every one of them.
          requestBody: {
            CLOUDFRONT: { defaultSizeInspectionLimit: "KB_64" },
          },
        },
        rules: [
          {
            name: "AWS-AWSManagedRulesCommonRuleSet",
            priority: 0,
            overrideAction: { none: {} },
            statement: {
              managedRuleGroupStatement: {
                vendorName: "AWS",
                name: "AWSManagedRulesCommonRuleSet",
                ruleActionOverrides: [
                  {
                    name: "SizeRestrictions_BODY",
                    actionToUse: { count: {} },
                  },
                ],
              },
            },
            visibilityConfig: {
              sampledRequestsEnabled: true,
              cloudWatchMetricsEnabled: true,
              metricName: createCdkId([prefix, "CommonRuleSet"]),
            },
          },
          {
            name: "AWS-AWSManagedRulesKnownBadInputsRuleSet",
            priority: 1,
            overrideAction: { none: {} },
            statement: {
              managedRuleGroupStatement: {
                vendorName: "AWS",
                name: "AWSManagedRulesKnownBadInputsRuleSet",
              },
            },
            visibilityConfig: {
              sampledRequestsEnabled: true,
              cloudWatchMetricsEnabled: true,
              metricName: createCdkId([prefix, "KnownBadInputs"]),
            },
          },
          {
            name: "AWS-AWSManagedRulesAmazonIpReputationList",
            priority: 2,
            overrideAction: { none: {} },
            statement: {
              managedRuleGroupStatement: {
                vendorName: "AWS",
                name: "AWSManagedRulesAmazonIpReputationList",
              },
            },
            visibilityConfig: {
              sampledRequestsEnabled: true,
              cloudWatchMetricsEnabled: true,
              metricName: createCdkId([prefix, "IpReputation"]),
            },
          },
        ],
      });
    }

    const distribution = new cloudfront.Distribution(this, "Distribution", {
      webAclId: webAcl?.attrArn,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(websiteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        compress: true,
        cachePolicy: new cloudfront.CachePolicy(
          this,
          createCdkId([prefix, "CachePolicy"]),
          {
            defaultTtl: cdk.Duration.seconds(86400),
            minTtl: cdk.Duration.seconds(0),
            maxTtl: cdk.Duration.seconds(31536000),
            enableAcceptEncodingBrotli: true,
            enableAcceptEncodingGzip: true,
          },
        ),
      },
      defaultRootObject: "index.html",
      additionalBehaviors: {
        "/api/*": {
          origin: origins.VpcOrigin.withApplicationLoadBalancer(alb, {
            protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
            readTimeout: cdk.Duration.seconds(90),
          }),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: new cloudfront.OriginRequestPolicy(
            this,
            createCdkId([prefix, "ApiOriginRequestPolicy"]),
            {
              originRequestPolicyName: createCdkId([
                prefix,
                `api-origin-request-policy-${config.region}`,
              ]),
              headerBehavior: cloudfront.OriginRequestHeaderBehavior.all(),
              queryStringBehavior:
                cloudfront.OriginRequestQueryStringBehavior.all(),
              cookieBehavior: cloudfront.OriginRequestCookieBehavior.all(),
            },
          ),
        },
      },
      comment: "CloudFront distribution to serve content from S3 and to ALB",
      enableLogging: true,
      logBucket: accessLogsBucket,
      logIncludesCookies: true,
      logFilePrefix: "cloudfront-logs",
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
    });
    const applicationUri = `https://${distribution.distributionDomainName}`;

    // Get or create user pool
    let userPool;
    const cognitoAuthConfig = config.cognitoAuthConfig;
    if (!cognitoAuthConfig.userPoolId) {
      // Create a new User Pool
      userPool = new cognito.UserPool(this, "UserPool", {
        userPoolName: cognitoAuthConfig.userPoolName,
        selfSignUpEnabled: false,
        signInAliases: {
          email: true,
          username: false,
          phone: false,
        },
        accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
        passwordPolicy: {
          minLength: 8,
          requireLowercase: true,
          requireUppercase: true,
          requireDigits: true,
          requireSymbols: true,
        },
        removalPolicy: config.removalPolicy,
      });
    } else {
      // Use existing User Pool
      userPool = cognito.UserPool.fromUserPoolId(
        this,
        "UserPool",
        cognitoAuthConfig.userPoolId,
      );
    }

    // Create or use an existing User Pool client
    let userPoolClient;
    if (!cognitoAuthConfig.userPoolClientId) {
      userPoolClient = userPool.addClient("CognitoUserPoolClient", {
        generateSecret: false,
        authFlows: {
          adminUserPassword: true,
          userPassword: true,
        },
        oAuth: {
          flows: {
            authorizationCodeGrant: true,
          },
          scopes: [cognito.OAuthScope.OPENID],
          callbackUrls: [applicationUri, "http://localhost:3000", "http://localhost:3001"], // Both localhost 3000 and 3001 to support if 3000 is used by another application during development
          logoutUrls: [applicationUri, "http://localhost:3000", "http://localhost:3001"],
        },
        supportedIdentityProviders: [
          cognito.UserPoolClientIdentityProvider.COGNITO,
        ],
        preventUserExistenceErrors: true,
        accessTokenValidity: cdk.Duration.days(1),
        idTokenValidity: cdk.Duration.days(1),
        refreshTokenValidity: cdk.Duration.days(30),
      });
    } else {
      userPoolClient = cognito.UserPoolClient.fromUserPoolClientId(
        this,
        "UserPoolClientId",
        cognitoAuthConfig.userPoolClientId,
      );
    }

    // If it's a new User Pool, create the domain
    if (!cognitoAuthConfig.userPoolId) {
      userPool.addDomain("CognitoUserPoolDomain", {
        cognitoDomain: {
          domainPrefix: cognitoAuthConfig.userPoolDomainName,
        },
      });
    }

    // Update
    this.vpc = vpc;
    this.securityGroups = {
      alb: albSg,
      fastApiService: fastApiServiceSg,
    };
    this.ddbTables = {
      feedback: feedbackTable,
      metadataSchemas: metadataSchemasTable,
      metadataUploadJob: metadataUploadJobTable,
    };
    this.iamRoles = {
      fastApiTask: fastApiTaskRole,
    };
    this.s3Buckets = {
      website: websiteBucket,
      validationResults: validationResultsBucket,
      schemaStorage: schemaStorageBucket,
    };
    this.albListener = albListener;
    this.distribution = distribution;
    this.applicationUri = applicationUri;
    this.clientId = userPoolClient.userPoolClientId;
    this.apiAuthority = `https://cognito-idp.${config.region}.amazonaws.com/${userPool.userPoolId}`;
    this.userPoolDomainUrl = `https://${cognitoAuthConfig.userPoolDomainName}.auth.${config.region}.amazoncognito.com`;

    // CFN outputs
    new cdk.CfnOutput(this, "ApplicationUri", { value: this.applicationUri });
    new cdk.CfnOutput(this, "FeedbackTableName", {
      value: feedbackTable.tableName,
    });
    new cdk.CfnOutput(this, "MetadataSchemasTableName", {
      value: metadataSchemasTable.tableName,
    });
    new cdk.CfnOutput(this, "MetadataUploadJobTableName", {
      value: metadataUploadJobTable.tableName,
    });
    new cdk.CfnOutput(this, "ValidationResultsBucketName", {
      value: validationResultsBucket.bucketName,
    });
    new cdk.CfnOutput(this, "SchemaStorageBucketName", {
      value: schemaStorageBucket.bucketName,
    });
    new cdk.CfnOutput(this, "CognitoApiAuthorityUrl", {
      value: this.apiAuthority,
    });
    new cdk.CfnOutput(this, "CognitoUserPoolId", {
      value: userPool.userPoolId,
    });
    new cdk.CfnOutput(this, "CognitoClientId", { value: this.clientId });
    new cdk.CfnOutput(this, "CognitoDomainUrl", {
      value: this.userPoolDomainUrl,
    });
    new cdk.CfnOutput(this, "StackName", {
      value: cdk.Stack.of(this).stackName,
    });
  }
}
