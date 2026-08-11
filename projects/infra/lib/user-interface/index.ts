/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// User interface construct.
import * as path from "path";

import * as cdk from "aws-cdk-lib";
import * as s3deployment from "aws-cdk-lib/aws-s3-deployment";
import { Construct } from "constructs";

import { Core } from "../core";
import { BaseProps } from "../schema";

/**
 * Properties of UserInterface construct.
 *
 * @property {Core} core - Core Construct.
 */
interface UserInterfaceProps extends BaseProps {
  readonly core: Core;
}

/**
 * UserInterface construct.
 */
export class UserInterface extends Construct {
  /**
   * @param {Construct} scope - Parent or owner of the construct.
   * @param {string} id - Unique identifier for the construct within its scope.
   * @param {UserInterfaceProps} props - Properties of the construct.
   */
  constructor(scope: Construct, id: string, props: UserInterfaceProps) {
    super(scope, id);

    const { core } = props;
    const websiteBucket = core.s3Buckets.website;
    const projectRoot = path.resolve(process.cwd(), "../../");
    const frontendPath = path.join(projectRoot, "projects", "frontend");

    // Define deployment sources
    const runtimeConfig = {
      API_URI: core.applicationUri,
      COGNITO: {
        authority: core.userPoolDomainUrl,
        client_id: core.clientId,
        redirect_uri: core.applicationUri,
        post_logout_redirect_uri: core.applicationUri,
        scope: "openid",
        response_type: "code",
        loadUserInfo: true,
        metadata: {
          authorization_endpoint: `${core.userPoolDomainUrl}/oauth2/authorize`,
          token_endpoint: `${core.userPoolDomainUrl}/oauth2/token`,
          userinfo_endpoint: `${core.userPoolDomainUrl}/oauth2/userInfo`,
          end_session_endpoint: `${core.userPoolDomainUrl}/logout`,
        },
      },
    };

    // Create env.js file
    const envConfigSource = s3deployment.Source.data(
      "env.js",
      `window.env = ${JSON.stringify(runtimeConfig, null, 2)};`,
    );

    // Create webapp assets
    const webappAssets = s3deployment.Source.asset(frontendPath, {
      bundling: {
        image: cdk.DockerImage.fromRegistry("node:18"),
        command: [
          "bash",
          "-c",
          [
            "mkdir -p /.npm",
            "chmod -R 777 /.npm",
            "npm ci --include=dev",
            "rm -rf out .env.local ./public/env.js",
            "npm run build",
            "mkdir -p /asset-output",
            "cp -r out/* /asset-output/",
            "cp public/* /asset-output/",
            "chmod -R 755 /asset-output",
          ].join(" && "),
        ],
        environment: {
          NODE_ENV: "production",
          npm_config_cache: "/.npm",
        },
        workingDirectory: "/asset-input",
        user: "root",
      },
    });

    // Deploy both sources
    new s3deployment.BucketDeployment(this, "DeployWebsite", {
      sources: [webappAssets, envConfigSource],
      destinationBucket: websiteBucket,
      distribution: core.distribution,
      distributionPaths: ["/*"],
    });
  }
}
