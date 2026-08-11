#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Test script for infrastructure deployment in development environment.
This script performs comprehensive testing of the modernized infrastructure.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List

import boto3
import requests
import yaml
from botocore.exceptions import ClientError, NoCredentialsError

# Add project root to path for imports
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Set up AWS session with profile if provided
profile_name = os.getenv("PROFILE") or os.getenv("AWS_PROFILE")
if profile_name:
    boto3.setup_default_session(profile_name=profile_name)


class InfrastructureTestResult:
    """Container for test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.errors: List[str] = []
        self.warnings_list: List[str] = []

    def add_pass(self, message: str):
        """Add a passing test."""
        print(f"\t✓ PASS: {message}")
        self.passed += 1

    def add_fail(self, message: str):
        """Add a failing test."""
        print(f"\t✗ FAIL: {message}")
        self.failed += 1
        self.errors.append(message)

    def add_warning(self, message: str):
        """Add a warning."""
        print(f"\t⚠ WARNING: {message}")
        self.warnings += 1
        self.warnings_list.append(message)

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed + self.warnings
        print(f"\n{'='*60}")
        print("INFRASTRUCTURE DEPLOYMENT TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Warnings: {self.warnings}")

        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings_list:
            print("\nWarnings:")
            for warning in self.warnings_list:
                print(f"  - {warning}")

        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        if self.failed == 0:
            print("🎉 All critical tests passed!")
            return True
        else:
            print("❌ Some tests failed. Please review the errors above.")
            return False


def _find_output(outputs: Dict[str, str], logical_id: str) -> str | None:
    """Find a CloudFormation output value by CfnOutput logical ID.

    CDK synthesizes output keys as {ConstructPath}{LogicalId}{Hash} (e.g.
    the "ApplicationUri" CfnOutput inside the Core construct becomes
    "CoreApplicationUriE548207C" in the deployed template), so exact-key
    lookups against `outputs` never match. Match on substring containment
    instead, since the construct-path prefix and hash suffix both vary.
    """
    return next((v for k, v in outputs.items() if logical_id in k), None)


class InfrastructureTester:
    """Test infrastructure deployment."""

    def __init__(self, config: Dict, region: str):
        self.config = config
        self.region = region
        self.result = InfrastructureTestResult()

        # Initialize AWS clients
        try:
            self.dynamodb = boto3.client("dynamodb", region_name=region)
            self.s3 = boto3.client("s3", region_name=region)
            self.ecs = boto3.client("ecs", region_name=region)
            self.elbv2 = boto3.client("elbv2", region_name=region)
            self.cloudformation = boto3.client("cloudformation", region_name=region)
            self.cognito_idp = boto3.client("cognito-idp", region_name=region)
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Please configure your AWS credentials.")

    def get_stack_outputs(self, stack_name: str) -> Dict[str, str]:
        """Get CloudFormation stack outputs."""
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stacks = response.get("Stacks", [])

            if not stacks:
                raise ValueError(f"Stack {stack_name} not found")

            outputs = {}
            for output in stacks[0].get("Outputs", []):
                outputs[output["OutputKey"]] = output["OutputValue"]

            return outputs
        except ClientError as e:
            if e.response["Error"]["Code"] == "ValidationError":
                raise ValueError(f"Stack {stack_name} does not exist") from e
            raise

    def test_cloudformation_stack(self, stack_name: str) -> Dict[str, str]:
        """Test CloudFormation stack exists and is in good state."""
        print(f"Testing CloudFormation stack: {stack_name}")

        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stacks = response.get("Stacks", [])

            if not stacks:
                self.result.add_fail(f"Stack {stack_name} not found")
                return {}

            stack = stacks[0]
            stack_status = stack.get("StackStatus")

            if stack_status in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
                self.result.add_pass(f"Stack {stack_name} is in good state ({stack_status})")
            else:
                self.result.add_fail(f"Stack {stack_name} is in bad state ({stack_status})")
                return {}

            # Get stack outputs
            outputs = {}
            for output in stack.get("Outputs", []):
                outputs[output["OutputKey"]] = output["OutputValue"]

            self.result.add_pass(f"Retrieved {len(outputs)} stack outputs")
            return outputs

        except ClientError as e:
            self.result.add_fail(f"Error accessing stack {stack_name}: {e}")
            return {}

    def test_dynamodb_tables(self, outputs: Dict[str, str]) -> None:
        """Test DynamoDB tables are created correctly."""
        print("\nTesting DynamoDB tables...")

        # Expected tables and their output keys
        expected_tables = {
            "MetadataSchemasTableName": "METADATA_SCHEMAS_TABLE",
            "MetadataUploadJobTableName": "METADATA_UPLOAD_JOB_TABLE",
            "FeedbackTableName": "FEEDBACK_TABLE",
        }

        for output_key, table_purpose in expected_tables.items():
            table_name = _find_output(outputs, output_key)

            if not table_name:
                self.result.add_fail(f"Missing {output_key} in stack outputs")
                continue

            try:
                response = self.dynamodb.describe_table(TableName=table_name)
                table = response["Table"]

                # Check table status
                table_status = table["TableStatus"]
                if table_status == "ACTIVE":
                    self.result.add_pass(f"Table {table_name} is active")
                else:
                    self.result.add_fail(f"Table {table_name} is not active (status: {table_status})")
                    continue

                # Check billing mode
                billing_mode = table.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
                if billing_mode == "PAY_PER_REQUEST":
                    self.result.add_pass(f"Table {table_name} uses pay-per-request billing")
                else:
                    self.result.add_warning(f"Table {table_name} uses {billing_mode} billing mode")

                # Check encryption
                sse_description = table.get("SSEDescription", {})
                if sse_description.get("Status") == "ENABLED":
                    self.result.add_pass(f"Table {table_name} has encryption enabled")
                else:
                    self.result.add_warning(f"Table {table_name} encryption status unclear")

                # Check specific table configurations
                if table_purpose == "METADATA_SCHEMAS_TABLE":
                    self._test_metadata_schemas_table(table_name, table)
                elif table_purpose == "METADATA_UPLOAD_JOB_TABLE":
                    self._test_metadata_upload_job_table(table_name, table)

            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    self.result.add_fail(f"Table {table_name} not found")
                else:
                    self.result.add_fail(f"Error accessing table {table_name}: {e}")

    def _test_metadata_schemas_table(self, table_name: str, table: Dict) -> None:
        """Test METADATA_SCHEMAS_TABLE specific configuration."""
        # Check partition key
        key_schema = table.get("KeySchema", [])
        partition_key = next((k for k in key_schema if k["KeyType"] == "HASH"), None)

        if partition_key and partition_key["AttributeName"] == "core_schema_id":
            self.result.add_pass(f"Table {table_name} has correct partition key (core_schema_id)")
        else:
            self.result.add_fail(f"Table {table_name} has incorrect partition key")

    def _test_metadata_upload_job_table(self, table_name: str, table: Dict) -> None:
        """Test METADATA_UPLOAD_JOB_TABLE specific configuration."""
        # Check partition key
        key_schema = table.get("KeySchema", [])
        partition_key = next((k for k in key_schema if k["KeyType"] == "HASH"), None)

        if partition_key and partition_key["AttributeName"] == "job_id":
            self.result.add_pass(f"Table {table_name} has correct partition key (job_id)")
        else:
            self.result.add_fail(f"Table {table_name} has incorrect partition key")

        # Check GSI
        gsi_list = table.get("GlobalSecondaryIndexes", [])
        user_id_index = next((gsi for gsi in gsi_list if gsi["IndexName"] == "user-id-index"), None)

        if user_id_index:
            self.result.add_pass(f"Table {table_name} has user-id-index GSI")

            # Check GSI key schema
            gsi_key_schema = user_id_index.get("KeySchema", [])
            gsi_partition_key = next((k for k in gsi_key_schema if k["KeyType"] == "HASH"), None)
            gsi_sort_key = next((k for k in gsi_key_schema if k["KeyType"] == "RANGE"), None)

            if (
                gsi_partition_key
                and gsi_partition_key["AttributeName"] == "user_id"
                and gsi_sort_key
                and gsi_sort_key["AttributeName"] == "created_at"
            ):
                self.result.add_pass(f"Table {table_name} GSI has correct key schema")
            else:
                self.result.add_fail(f"Table {table_name} GSI has incorrect key schema")
        else:
            self.result.add_fail(f"Table {table_name} missing user-id-index GSI")

    def test_s3_buckets(self, outputs: Dict[str, str]) -> None:
        """Test S3 buckets are created with proper permissions."""
        print("\nTesting S3 buckets...")

        # Expected buckets and their output keys
        expected_buckets = {
            "ValidationResultsBucketName": "validation results",
            "SchemaStorageBucketName": "schema storage",
        }

        for output_key, bucket_purpose in expected_buckets.items():
            bucket_name = _find_output(outputs, output_key)

            if not bucket_name:
                self.result.add_fail(f"Missing {output_key} in stack outputs")
                continue

            try:
                # Check bucket exists
                self.s3.head_bucket(Bucket=bucket_name)
                self.result.add_pass(f"Bucket {bucket_name} exists and is accessible")

                # Check bucket encryption
                try:
                    encryption_response = self.s3.get_bucket_encryption(Bucket=bucket_name)
                    rules = encryption_response.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])

                    if rules:
                        self.result.add_pass(f"Bucket {bucket_name} has encryption enabled")
                    else:
                        self.result.add_warning(f"Bucket {bucket_name} encryption configuration unclear")

                except ClientError as e:
                    if e.response["Error"]["Code"] == "ServerSideEncryptionConfigurationNotFoundError":
                        self.result.add_warning(f"Bucket {bucket_name} has no encryption configuration")
                    else:
                        self.result.add_warning(f"Could not check encryption for bucket {bucket_name}: {e}")

                # Check public access block
                try:
                    pab_response = self.s3.get_public_access_block(Bucket=bucket_name)
                    pab_config = pab_response.get("PublicAccessBlockConfiguration", {})

                    if (
                        pab_config.get("BlockPublicAcls")
                        and pab_config.get("IgnorePublicAcls")
                        and pab_config.get("BlockPublicPolicy")
                        and pab_config.get("RestrictPublicBuckets")
                    ):
                        self.result.add_pass(f"Bucket {bucket_name} has public access blocked")
                    else:
                        self.result.add_warning(f"Bucket {bucket_name} public access block not fully configured")

                except ClientError as e:
                    self.result.add_warning(f"Could not check public access block for bucket {bucket_name}: {e}")

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "404":
                    self.result.add_fail(f"Bucket {bucket_name} not found")
                elif error_code == "403":
                    self.result.add_fail(f"Access denied to bucket {bucket_name}")
                else:
                    self.result.add_fail(f"Error accessing bucket {bucket_name}: {e}")

    def test_ecs_service(self, outputs: Dict[str, str]) -> None:
        """Test ECS service and container configuration."""
        print("\nTesting ECS service...")

        # Find ECS cluster and service
        try:
            clusters_response = self.ecs.list_clusters()
            clusters = clusters_response.get("clusterArns", [])

            if not clusters:
                self.result.add_fail("No ECS clusters found")
                return

            # Look for our cluster (should contain deployment name)
            deployment_name = self.config.get("deploymentName", "")
            target_cluster = None

            for cluster_arn in clusters:
                cluster_name = cluster_arn.split("/")[-1]
                if deployment_name.lower() in cluster_name.lower():
                    target_cluster = cluster_arn
                    break

            if not target_cluster:
                self.result.add_warning("Could not find ECS cluster matching deployment name")
                target_cluster = clusters[0]  # Use first available cluster

            cluster_name = target_cluster.split("/")[-1]
            self.result.add_pass(f"Found ECS cluster: {cluster_name}")

            # List services in cluster
            services_response = self.ecs.list_services(cluster=target_cluster)
            service_arns = services_response.get("serviceArns", [])

            if not service_arns:
                self.result.add_fail(f"No services found in cluster {cluster_name}")
                return

            # Check each service
            for service_arn in service_arns:
                service_name = service_arn.split("/")[-1]
                self._test_ecs_service_details(target_cluster, service_arn, service_name)

        except ClientError as e:
            self.result.add_fail(f"Error accessing ECS: {e}")

    def _test_ecs_service_details(self, cluster_arn: str, service_arn: str, service_name: str) -> None:
        """Test specific ECS service details."""
        try:
            services_response = self.ecs.describe_services(cluster=cluster_arn, services=[service_arn])

            services = services_response.get("services", [])
            if not services:
                self.result.add_fail(f"Service {service_name} not found")
                return

            service = services[0]

            # Check service status
            status = service.get("status")
            if status == "ACTIVE":
                self.result.add_pass(f"ECS service {service_name} is active")
            else:
                self.result.add_fail(f"ECS service {service_name} status is {status}")

            # Check running count
            running_count = service.get("runningCount", 0)
            desired_count = service.get("desiredCount", 0)

            if running_count == desired_count and running_count > 0:
                self.result.add_pass(f"ECS service {service_name} has {running_count}/{desired_count} tasks running")
            else:
                self.result.add_warning(f"ECS service {service_name} has {running_count}/{desired_count} tasks running")

            # Check task definition
            task_definition_arn = service.get("taskDefinition")
            if task_definition_arn:
                self._test_task_definition(task_definition_arn, service_name)

        except ClientError as e:
            self.result.add_fail(f"Error describing ECS service {service_name}: {e}")

    def _test_task_definition(self, task_definition_arn: str, service_name: str) -> None:
        """Test ECS task definition configuration."""
        try:
            td_response = self.ecs.describe_task_definition(taskDefinition=task_definition_arn)
            task_def = td_response.get("taskDefinition", {})

            # Check container definitions
            containers = task_def.get("containerDefinitions", [])
            if not containers:
                self.result.add_fail(f"No containers found in task definition for {service_name}")
                return

            # Check main container (should be first one)
            main_container = containers[0]
            container_name = main_container.get("name", "unknown")

            # Check environment variables
            environment = main_container.get("environment", [])
            env_vars = {env["name"]: env["value"] for env in environment}

            expected_env_vars = [
                "METADATA_SCHEMAS_TABLE",
                "METADATA_UPLOAD_JOB_TABLE",
                "VALIDATION_RESULTS_BUCKET",
                "SCHEMA_STORAGE_BUCKET",
                "AUTHORITY",
                "CLIENT_ID",
            ]

            missing_vars = []
            for var in expected_env_vars:
                if var not in env_vars:
                    missing_vars.append(var)

            if not missing_vars:
                self.result.add_pass(f"Container {container_name} has all required environment variables")
            else:
                self.result.add_fail(f"Container {container_name} missing environment variables: {missing_vars}")

            # Check that old database variables are not present
            old_db_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USERNAME", "DB_PASSWORD_SECRET_ARN"]
            found_old_vars = [var for var in old_db_vars if var in env_vars]

            if not found_old_vars:
                self.result.add_pass(f"Container {container_name} has no old database environment variables")
            else:
                self.result.add_fail(f"Container {container_name} still has old database variables: {found_old_vars}")

            # Check health check
            health_check = main_container.get("healthCheck")
            if health_check:
                self.result.add_pass(f"Container {container_name} has health check configured")
            else:
                self.result.add_warning(f"Container {container_name} has no health check configured")

        except ClientError as e:
            self.result.add_fail(f"Error describing task definition for {service_name}: {e}")

    def test_api_endpoints(self, outputs: Dict[str, str]) -> None:
        """Test API endpoints for basic functionality."""
        print("\nTesting API endpoints...")

        # Get application URI from outputs
        application_uri = _find_output(outputs, "ApplicationUri")
        if not application_uri:
            self.result.add_fail("Missing ApplicationUri in stack outputs")
            return

        # Test health endpoints
        health_url_v1 = f"{application_uri}/api/v1/health/"
        self._test_endpoint(health_url_v1, "Health endpoint (v1)", expected_status=[200])

        health_url_simple = f"{application_uri}/api/health"
        self._test_endpoint(health_url_simple, "Health endpoint (simple)", expected_status=[200])

        # Test metadata schema endpoint (may require auth)
        schema_url = f"{application_uri}/api/v1/metadata/schema"
        self._test_endpoint(schema_url, "Metadata schema endpoint", expected_status=[200, 401, 403])

        # Test root API endpoint
        api_root_url = f"{application_uri}/api/"
        self._test_endpoint(api_root_url, "API root endpoint", expected_status=[200, 404])

    def _test_endpoint(self, url: str, description: str, expected_status: List[int], timeout: int = 30) -> None:
        """Test a specific endpoint."""
        try:
            response = requests.get(url, timeout=timeout)

            if response.status_code in expected_status:
                self.result.add_pass(f"{description} responded with status {response.status_code}")

                # Try to parse JSON response if possible
                try:
                    json_data = response.json()
                    if isinstance(json_data, dict) and len(json_data) > 0:
                        self.result.add_pass(f"{description} returned valid JSON response")
                except (ValueError, json.JSONDecodeError):
                    # Not JSON, that's okay for some endpoints
                    pass

            else:
                self.result.add_warning(f"{description} returned unexpected status {response.status_code}")

        except requests.exceptions.Timeout:
            self.result.add_warning(f"{description} timed out after {timeout} seconds")
        except requests.exceptions.ConnectionError:
            self.result.add_warning(f"{description} connection failed - service may still be starting")
        except requests.exceptions.RequestException as e:
            self.result.add_warning(f"{description} request failed: {e}")

    def test_authentication_config(self, outputs: Dict[str, str]) -> None:
        """Test authentication configuration."""
        print("\nTesting authentication configuration...")

        # Check Cognito outputs
        cognito_outputs = ["CognitoApiAuthorityUrl", "CognitoUserPoolId", "CognitoClientId", "CognitoDomainUrl"]

        missing_outputs = []
        for output in cognito_outputs:
            if _find_output(outputs, output) is None:
                missing_outputs.append(output)

        if not missing_outputs:
            self.result.add_pass("All Cognito configuration outputs present")
        else:
            self.result.add_fail(f"Missing Cognito outputs: {missing_outputs}")
            return

        # Test Cognito user pool
        user_pool_id = _find_output(outputs, "CognitoUserPoolId")
        if user_pool_id:
            try:
                response = self.cognito_idp.describe_user_pool(UserPoolId=user_pool_id)
                user_pool = response.get("UserPool", {})

                pool_name = user_pool.get("Name", "")
                if "metadata-harmonization" in pool_name.lower():
                    self.result.add_pass(f"Cognito user pool has correct name: {pool_name}")
                else:
                    self.result.add_warning(f"Cognito user pool name may be incorrect: {pool_name}")

                # Check user pool configuration
                policies = user_pool.get("Policies", {})
                password_policy = policies.get("PasswordPolicy", {})

                if password_policy.get("MinimumLength", 0) >= 8:
                    self.result.add_pass("Cognito user pool has strong password policy")
                else:
                    self.result.add_warning("Cognito user pool password policy may be weak")

            except ClientError as e:
                self.result.add_fail(f"Error accessing Cognito user pool: {e}")

    def run_all_tests(self, stack_name: str) -> bool:
        """Run all infrastructure tests."""
        print(f"Starting infrastructure deployment tests for stack: {stack_name}")
        print(f"Region: {self.region}")
        print(f"{'='*60}")

        # Test CloudFormation stack and get outputs
        outputs = self.test_cloudformation_stack(stack_name)

        if not outputs:
            print("Cannot continue tests without stack outputs")
            return False

        # Run all tests
        self.test_dynamodb_tables(outputs)
        self.test_s3_buckets(outputs)
        self.test_ecs_service(outputs)
        self.test_authentication_config(outputs)

        # Wait a bit for services to be fully ready, then test API
        print("\nWaiting 30 seconds for services to be fully ready...")
        time.sleep(30)
        self.test_api_endpoints(outputs)

        # Print summary and return result
        return self.result.print_summary()


def main():
    """Main function to run infrastructure deployment tests."""
    # Read configuration
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        print("ERROR: config.yaml not found in project root")
        sys.exit(1)

    with open(config_path, "r") as file:
        config_full = yaml.safe_load(file)

    # Parse config
    env = config_full.get("env")
    if not env:
        print("ERROR: No 'env' specified in config.yaml")
        sys.exit(1)

    config_env = config_full.get(env)
    if not config_env:
        print(f"ERROR: No configuration found for environment '{env}' in config.yaml")
        sys.exit(1)

    region = config_env.get("region")
    if not region:
        print("ERROR: No 'region' specified in config.yaml")
        sys.exit(1)

    # Build stack name
    app_name = config_full.get("appName", "metadata-harmonization-app")
    deployment_name = config_env.get("deploymentName")
    deployment_stage = config_env.get("deploymentStage")

    if not deployment_name or not deployment_stage:
        print("ERROR: deploymentName and deploymentStage must be specified in config.yaml")
        sys.exit(1)

    stack_name = f"{deployment_name}-{app_name}-{deployment_stage}"

    # Run tests
    tester = InfrastructureTester(config_env, region)
    success = tester.run_all_tests(stack_name)

    if success:
        print("\n🎉 All infrastructure deployment tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Infrastructure deployment tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
