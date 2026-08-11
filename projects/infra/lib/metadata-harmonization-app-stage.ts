/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Deploy application to different stages.
/* eslint-disable @typescript-eslint/no-empty-object-type */
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

import { MetadataHarmonizationAppApplicationStack } from "./metadata-harmonization-app-stack";
import { BaseProps } from "./schema";
import { createCdkId } from "./utils";

interface CustomMetadataHarmonizationAppProps extends BaseProps {}
type MetadataHarmonizationAppProps = CustomMetadataHarmonizationAppProps & cdk.StageProps;

/**
 * Metadata Harmonization App Application Stage.
 */
export class MetadataHarmonizationAppApplicationStage extends cdk.Stage {
  /**
   * @param {Construct} scope - Parent or owner of the construct.
   * @param {string} id - Unique identifier for the construct within its scope.
   * @param {MetadataHarmonizationAppProps} props - Properties of the stage.
   */
  constructor(scope: Construct, id: string, props: MetadataHarmonizationAppProps) {
    super(scope, id, props);

    const { config } = props;
    new MetadataHarmonizationAppApplicationStack(this, "MetadataHarmonizationApp", {
      config: config,
      stackName: createCdkId([
        config.deploymentName,
        config.appName,
        config.deploymentStage,
      ]),
      description: `MetadataHarmonizationApp: ${config.deploymentName}-${config.deploymentStage}`,
    });

    // Set resource tags
    for (const tag of config.tags ?? []) {
      cdk.Tags.of(this).add(tag["Key"], tag["Value"]);
    }
  }
}
