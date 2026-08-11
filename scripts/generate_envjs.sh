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
ENV_JS_FILE="projects/frontend/public/env.js"

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

# Create directory if it doesn't exist
mkdir -p "frontend/public"

# Delete existing file if it exists
if [ -f "$ENV_JS_FILE" ]; then
  echo "Existing env.js file found. Deleting it..."
  rm "$ENV_JS_FILE"
fi

echo "Generating new env.js file for the stack $STACK_NAME in region $REGION"

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

# Extract values from stack
DOMAIN_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreCognitoDomainUrl")) | .OutputValue')
CLIENT_ID=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey | startswith("CoreCognitoClientId")) | .OutputValue')

# Check if required Cognito values are missing
MISSING_VALUES=()
if [ -z "$DOMAIN_URL" ] || [ "$DOMAIN_URL" = "null" ]; then
  MISSING_VALUES+=("DOMAIN_URL")
fi
if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" = "null" ]; then
  MISSING_VALUES+=("CLIENT_ID")
fi

# Error out if authentication values are missing
if [ ${#MISSING_VALUES[@]} -gt 0 ]; then
  echo ""
  echo "❌ ERROR: Missing Cognito authentication configuration!"
  echo "   Missing values: ${MISSING_VALUES[*]}"
  echo ""
  echo "   This typically happens when:"
  echo "   • The CDK stack hasn't been deployed yet"
  echo "   • Cognito resources haven't been created"
  echo "   • The stack deployment is incomplete or failed"
  echo ""
  echo "   Without these values, authentication will NOT work and you will see:"
  echo "   • Login failures"
  echo "   • API authentication errors"
  echo "   • 401 Unauthorized responses"
  echo "   • Frontend unable to authenticate users"
  echo ""
  echo "   To fix this:"
  echo "   1. Deploy the CDK stack first: 'make deploy'"
  echo "   2. Wait for Cognito resources to be created"
  echo "   3. Re-run this script to generate proper env.js"
  echo ""
  echo "   Aborting. Please deploy the stack first and try again."
  exit 1
fi

# Create the runtime config JSON
cat > "$ENV_JS_FILE" << EOL
window.env = {
  "API_URI": "http://localhost:8080",
  "COGNITO": {
    "authority": "${DOMAIN_URL}",
    "client_id": "${CLIENT_ID}",
    "redirect_uri": "http://localhost:3000",
    "post_logout_redirect_uri": "http://localhost:3000",
    "scope": "openid",
    "response_type": "code",
    "loadUserInfo": true,
    "metadata": {
      "authorization_endpoint": "${DOMAIN_URL}/oauth2/authorize",
      "token_endpoint": "${DOMAIN_URL}/oauth2/token",
      "userinfo_endpoint": "${DOMAIN_URL}/oauth2/userInfo",
      "end_session_endpoint": "${DOMAIN_URL}/logout"
    }
  }
};
EOL

echo "New env.js file created at: $ENV_JS_FILE"

# Show final status
echo ""
echo "✅ Authentication configuration complete!"
echo "   DOMAIN_URL: $DOMAIN_URL"
echo "   CLIENT_ID: $CLIENT_ID"
echo "   Local development should work with authentication."
echo ""
