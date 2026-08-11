/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Metadata Harmonization App stack.
/* eslint-disable @typescript-eslint/no-empty-object-type */
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

import { RestApi } from "./api";
import { Core } from "./core";
import { BaseProps } from "./schema";
import { UserInterface } from "./user-interface";
interface CustomMetadataHarmonizationAppProps extends BaseProps {}
type MetadataHarmonizationAppProps = CustomMetadataHarmonizationAppProps & cdk.StackProps;

/**
 * Metadata Harmonization App Application Stack.
 */
export class MetadataHarmonizationAppApplicationStack extends cdk.Stack {
  /**
   * @param {Construct} scope - Parent or owner of the construct.
   * @param {string} id - Unique identifier for the construct within its scope.
   * @param {MetadataHarmonizationAppProps} props - Properties of the Stack.
   */
  constructor(scope: Construct, id: string, props: MetadataHarmonizationAppProps) {
    super(scope, id, props);

    const { config } = props;

    // Create core infra
    const core = new Core(this, "Core", {
      config: config,
    });

    // Create REST API
    new RestApi(this, "RestApi", {
      config: config,
      core: core,
    });

    // Create UserInterface
    new UserInterface(this, "UserInterface", {
      config: config,
      core: core,
    });
  }
}
