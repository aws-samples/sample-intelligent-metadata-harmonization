#!/bin/bash
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <stack-name> <region> <profile> <log-level>"
  exit 1
fi

STACK_NAME=$1
REGION=$2
PROFILE=$3
LOG_LEVEL=$4
ENV_FILE=".env"

# Check if PROFILE is null or empty and use AWS_PROFILE if available
if [ "$PROFILE" = "null" ] || [ -z "$PROFILE" ]; then
  if [ -n "$AWS_PROFILE" ]; then
    PROFILE=$AWS_PROFILE
    echo "Using AWS_PROFILE: $PROFILE"
  else
    echo "Warning: Profile not provided or set to null, and AWS_PROFILE not set. AWS CLI will use default credentials."
    PROFILE="default"
  fi
fi

# Delete existing files if they exist
if [ -f "$ENV_FILE" ]; then
  echo "Existing .env file found. Deleting it..."
  rm "$ENV_FILE"
fi

echo "Generating new environment files for the stack $STACK_NAME in region $REGION"

# Fetch the CloudFormation stack outputs with or without profile
if [ -n "$PROFILE" ]; then
  OUTPUTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --profile $PROFILE --query "Stacks[0].Outputs" --output json)
else
  OUTPUTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query "Stacks[0].Outputs" --output json)
fi

# Check if outputs were retrieved
if [ -z "$OUTPUTS" ]; then
  echo "No outputs found for the stack."
  exit 1
fi

# Map the outputs to the specified environment variables
echo "AWS_REGION=$REGION" >> $ENV_FILE
if [ -n "$PROFILE" ]; then
  echo "AWS_DEFAULT_PROFILE=$PROFILE" >> $ENV_FILE
fi
echo "LOG_LEVEL=$LOG_LEVEL" >> $ENV_FILE

# Extract values from stack
API_AUTHORITY_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreCognitoApiAuthorityUrl")) | .OutputValue')
CLIENT_ID=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreCognitoClientId")) | .OutputValue')
USER_POOL_ID=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreCognitoUserPoolId")) | .OutputValue')

# Extract DynamoDB table names
METADATA_SCHEMAS_TABLE=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreMetadataSchemasTableName")) | .OutputValue')
METADATA_UPLOAD_JOB_TABLE=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreMetadataUploadJobTableName")) | .OutputValue')

# Extract S3 bucket names
VALIDATION_RESULTS_BUCKET=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreValidationResultsBucketName")) | .OutputValue')
SCHEMA_STORAGE_BUCKET=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreSchemaStorageBucketName")) | .OutputValue')

# Check if required values are missing
MISSING_VALUES=()
if [ -z "$API_AUTHORITY_URL" ] || [ "$API_AUTHORITY_URL" = "null" ]; then
  MISSING_VALUES+=("API_AUTHORITY_URL")
fi
if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" = "null" ]; then
  MISSING_VALUES+=("CLIENT_ID")
fi
if [ -z "$USER_POOL_ID" ] || [ "$USER_POOL_ID" = "null" ]; then
  MISSING_VALUES+=("USER_POOL_ID")
fi
if [ -z "$METADATA_SCHEMAS_TABLE" ] || [ "$METADATA_SCHEMAS_TABLE" = "null" ]; then
  MISSING_VALUES+=("METADATA_SCHEMAS_TABLE")
fi
if [ -z "$METADATA_UPLOAD_JOB_TABLE" ] || [ "$METADATA_UPLOAD_JOB_TABLE" = "null" ]; then
  MISSING_VALUES+=("METADATA_UPLOAD_JOB_TABLE")
fi
if [ -z "$VALIDATION_RESULTS_BUCKET" ] || [ "$VALIDATION_RESULTS_BUCKET" = "null" ]; then
  MISSING_VALUES+=("VALIDATION_RESULTS_BUCKET")
fi
if [ -z "$SCHEMA_STORAGE_BUCKET" ] || [ "$SCHEMA_STORAGE_BUCKET" = "null" ]; then
  MISSING_VALUES+=("SCHEMA_STORAGE_BUCKET")
fi

# Error out if required values are missing
if [ ${#MISSING_VALUES[@]} -gt 0 ]; then
  echo ""
  echo "❌ ERROR: Missing required AWS resources!"
  echo "   Missing values: ${MISSING_VALUES[*]}"
  echo ""
  echo "   This typically happens when:"
  echo "   • The CDK stack hasn't been deployed yet"
  echo "   • AWS resources haven't been created"
  echo "   • The stack deployment is incomplete or failed"
  echo ""
  echo "   Without these values, the application will NOT work and you will see:"
  echo "   • Database connection errors"
  echo "   • S3 access errors"
  echo "   • Authentication failures"
  echo "   • API startup failures"
  echo ""
  echo "   To fix this:"
  echo "   1. Deploy the CDK stack first: 'make deploy'"
  echo "   2. Wait for all AWS resources to be created"
  echo "   3. Re-run this script to generate proper .env"
  echo ""
  echo "   Aborting. Please deploy the stack first and try again."
  exit 1
fi

# Add to .env file
echo "AUTHORITY=$API_AUTHORITY_URL" >> $ENV_FILE
echo "CLIENT_ID=$CLIENT_ID" >> $ENV_FILE
echo "USER_POOL_ID=$USER_POOL_ID" >> $ENV_FILE

# Add DynamoDB table names
echo "METADATA_SCHEMAS_TABLE=$METADATA_SCHEMAS_TABLE" >> $ENV_FILE
echo "METADATA_UPLOAD_JOB_TABLE=$METADATA_UPLOAD_JOB_TABLE" >> $ENV_FILE

# Add S3 bucket names
echo "VALIDATION_RESULTS_BUCKET=$VALIDATION_RESULTS_BUCKET" >> $ENV_FILE
echo "SCHEMA_STORAGE_BUCKET=$SCHEMA_STORAGE_BUCKET" >> $ENV_FILE

echo "Environment file generated successfully with metadata validation configuration"
echo "DynamoDB tables: $METADATA_SCHEMAS_TABLE, $METADATA_UPLOAD_JOB_TABLE"
echo "S3 buckets: $VALIDATION_RESULTS_BUCKET, $SCHEMA_STORAGE_BUCKET"
