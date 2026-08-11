/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
// Utility functions.
import * as fs from "fs";
import * as path from "path";

import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";

const IAM_DIR = path.join(__dirname, "core", "iam");

/**
 * Extract policy statements from JSON file.
 *
 * @param {string} serviceName - AWS service name.
 * @returns {iam.PolicyStatement[]} - Extracted IAM policy statements.
 */
const extractPolicyStatementsFromJson = (
  serviceName: string,
): iam.PolicyStatement[] => {
  const statementData = fs.readFileSync(
    path.join(IAM_DIR, `${serviceName.toLowerCase()}.json`),
    "utf8",
  );
  const statements = JSON.parse(statementData).Statement;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  statements.forEach((statement: any) => {
    if (statement.Resource) {
      statement.Resource = []
        .concat(statement.Resource)
        .map((resource: string) => {
          return resource
            .replace(/\${AWS::AccountId}/gi, cdk.Aws.ACCOUNT_ID)
            .replace(/\${AWS::Region}/gi, cdk.Aws.REGION);
        });
    }
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return statements.map((statement: any) =>
    iam.PolicyStatement.fromJson(statement),
  );
};

/**
 * Wrapper to get IAM policy statements.
 * @param {string} serviceName - AWS service name.
 * @returns {iam.PolicyStatement[]} - Extracted IAM policy statements.
 */
export const getIamPolicyStatements = (
  serviceName: string,
): iam.PolicyStatement[] => {
  return extractPolicyStatementsFromJson(serviceName);
};

/**
 * Creates a unique CDK ID using configuration data. The CDK ID is used to uniquely identify resources in the AWS
 * Cloud Development Kit (CDK). The maximum length of the CDK ID is 64 characters.
 *
 * @param {string[]} idParts - Name of the resource.
 * @param {number} [maxLength==64] - Maximum length of CDK ID.
 * @throws {Error} - Throws an error if the generated CDK ID is longer than 64 characters.
 * @returns {string} - Generated CDK ID for the model resource.
 */
export function createCdkId(idParts: string[], maxLength: number = 64): string {
  let cdkId = idParts.join("-").toLowerCase();
  const length = cdkId.length;

  if (length > maxLength) {
    // Truncate the last part to ensure the total length doesn't exceed maxLength
    const lastPartIndex = idParts.length - 1;
    idParts[lastPartIndex] = idParts[lastPartIndex].slice(
      0,
      maxLength - (length - idParts[lastPartIndex].length),
    );
    cdkId = idParts.join("-").toLowerCase();
  }

  // Ensure the first character is a lowercase letter
  if (!/^[a-z]/.test(cdkId)) {
    cdkId = "a-" + cdkId.slice(1);
  }

  // Ensure the ID contains only lowercase letters, digits, and hyphens
  cdkId = cdkId.replace(/[^a-z0-9-]/g, "");

  return cdkId;
}
