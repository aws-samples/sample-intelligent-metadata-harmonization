#!/bin/bash
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

# Get project directory
PROJECT_DIR=$(dirname "$(dirname "$(realpath "$0")")")
cd "$PROJECT_DIR" || exit 1

# Function to cleanup processes on exit
cleanup() {
  echo "Stopping services..."
  kill $API_PID 2>/dev/null
  kill $UI_PID 2>/dev/null
  exit 0
}

# Setup trap for clean exit
trap cleanup SIGINT SIGTERM EXIT

# Verify config.yaml exists before attempting to load environment
if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
  echo "" >&2
  echo "ERROR: config.yaml not found at $PROJECT_DIR/config.yaml" >&2
  echo "" >&2
  echo "  This file is required for deployment and AWS-backed local development." >&2
  echo "  Create it from the example template:" >&2
  echo "" >&2
  echo "    cp config.yaml.example config.yaml" >&2
  echo "" >&2
  echo "  Then edit config.yaml to add your personal environment section." >&2
  echo "  See the README for configuration details." >&2
  echo "" >&2
  exit 1
fi

# Verify environment variables are set
if [ -z "$METADATA_SCHEMAS_TABLE" ] || [ -z "$METADATA_UPLOAD_JOB_TABLE" ]; then
  echo "Warning: DynamoDB table environment variables not set. Make sure to run 'make generateEnvironmentVariables' first."
fi

if [ -z "$VALIDATION_RESULTS_BUCKET" ] || [ -z "$SCHEMA_STORAGE_BUCKET" ]; then
  echo "Warning: S3 bucket environment variables not set. Make sure to run 'make generateEnvironmentVariables' first."
fi

# Start API service in background
echo "Starting metadata validation API service..."
echo "Using DynamoDB tables: $METADATA_SCHEMAS_TABLE, $METADATA_UPLOAD_JOB_TABLE"
echo "Using S3 buckets: $VALIDATION_RESULTS_BUCKET, $SCHEMA_STORAGE_BUCKET"
make runApiLocal &
API_PID=$!

# Wait for API to be ready (poll health endpoint)
echo "Waiting for metadata validation API to be ready..."
max_retries=30
retry_count=0
api_ready=false

while [ $retry_count -lt $max_retries ] && [ "$api_ready" = false ]; do
  if curl -s http://localhost:8080/api/health >/dev/null 2>&1; then
    api_ready=true
    echo "Metadata validation API service is ready!"
  else
    retry_count=$((retry_count + 1))
    echo "API not ready yet. Retrying in 2 seconds... ($retry_count/$max_retries)"
    sleep 2
  fi
done

if [ "$api_ready" = false ]; then
  echo "Error: Metadata validation API service failed to start within the expected timeframe."
  echo "Check that DynamoDB and S3 configuration is correct and AWS credentials are available."
  cleanup
  exit 1
fi

# Start UI in foreground
echo "Starting metadata validation UI service..."
make runUiLocal &
UI_PID=$!

# Wait for any child process to exit
wait
