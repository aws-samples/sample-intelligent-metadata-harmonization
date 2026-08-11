#!/usr/bin/env node

// Main app.
import * as fs from "fs";
import * as path from "path";

import * as cdk from "aws-cdk-lib";
import { Aspects } from "aws-cdk-lib";
import { AwsSolutionsChecks } from "cdk-nag";
import * as yaml from "js-yaml";

import { MetadataHarmonizationAppApplicationStage } from "../lib/metadata-harmonization-app-stage";
import { Config, ConfigSchema } from "../lib/schema";

// Read configuration file
const configFilePath = path.join(__dirname, "..", "..", "..", "config.yaml");
// eslint-disable-next-line
const configFile = yaml.load(fs.readFileSync(configFilePath, "utf8")) as any;
let configEnv = configFile.env || "dev";

// Select configuration environment
if (process.env.ENV) {
  configEnv = process.env.ENV;
}
const configData = configFile[configEnv];
if (!configData) {
  throw new Error(`Configuration for environment "${configEnv}" not found.`);
}

// Other command line argument overrides
type EnvMapping = [string, keyof Config];
const mappings: EnvMapping[] = [
  ["PROFILE", "profile"],
  ["DEPLOYMENT_NAME", "deploymentName"],
  ["ACCOUNT_NUMBER", "accountNumber"],
  ["REGION", "region"],
];
mappings.forEach(([envVar, configVar]) => {
  const envValue = process.env[envVar];
  if (envValue) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (configData as any)[configVar] = envValue;
  }
});

// Validate and parse configuration
let config: Config;
try {
  config = ConfigSchema.parse(configData);
} catch (error) {
  if (error instanceof Error) {
    console.error("Error parsing the configuration:", error.message);
  } else {
    console.error("An unexpected error occurred:", error);
  }
  process.exit(1);
}

// Define environment
const env: cdk.Environment = {
  account: config.accountNumber,
  region: config.region,
};

// Application
const app = new cdk.App();

// Run CDK-nag on app if specified
if (config.runCdkNag) {
  Aspects.of(app).add(new AwsSolutionsChecks({ reports: true, verbose: true }));
}

new MetadataHarmonizationAppApplicationStage(app, config.deploymentStage, {
  env: env,
  config: config,
});

app.synth();
