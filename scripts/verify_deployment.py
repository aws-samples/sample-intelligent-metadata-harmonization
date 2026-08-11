# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Verify CDK deployment for metadata validation infrastructure."""

import os
from pathlib import Path
import requests

import boto3
import yaml
from botocore.exceptions import ClientError

HERE = Path(__file__).resolve()
profile_name = os.getenv("PROFILE") or os.getenv("AWS_PROFILE")
if profile_name:
    boto3.setup_default_session(profile_name=profile_name)


def verify_dynamodb_tables(region: str) -> None:
    """Verify DynamoDB tables exist and are accessible."""
    dynamodb = boto3.client("dynamodb", region_name=region)

    # Get table names from environment variables
    metadata_schemas_table = os.getenv("METADATA_SCHEMAS_TABLE")
    metadata_upload_job_table = os.getenv("METADATA_UPLOAD_JOB_TABLE")

    tables_to_check = [
        ("METADATA_SCHEMAS_TABLE", metadata_schemas_table),
        ("METADATA_UPLOAD_JOB_TABLE", metadata_upload_job_table),
    ]

    for env_var_name, table_name in tables_to_check:
        if not table_name:
            print(f"Warning: {env_var_name} environment variable not set, skipping table verification")
            continue

        print(f"Checking DynamoDB table {table_name}...")
        try:
            response = dynamodb.describe_table(TableName=table_name)
            table_status = response["Table"]["TableStatus"]

            if table_status == "ACTIVE":
                print(f"\t- PASS: Table {table_name} is active")
            else:
                raise ValueError(f"Table {table_name} is not active (status: {table_status})")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise ValueError(f"DynamoDB table {table_name} not found") from e
            else:
                raise ValueError(f"Error accessing DynamoDB table {table_name}: {e}") from e


def verify_s3_buckets(region: str) -> None:
    """Verify S3 buckets exist and are accessible."""
    s3 = boto3.client("s3", region_name=region)

    # Get bucket names from environment variables
    validation_results_bucket = os.getenv("VALIDATION_RESULTS_BUCKET")
    schema_storage_bucket = os.getenv("SCHEMA_STORAGE_BUCKET")

    buckets_to_check = [
        ("VALIDATION_RESULTS_BUCKET", validation_results_bucket),
        ("SCHEMA_STORAGE_BUCKET", schema_storage_bucket),
    ]

    for env_var_name, bucket_name in buckets_to_check:
        if not bucket_name:
            print(f"Warning: {env_var_name} environment variable not set, skipping bucket verification")
            continue

        print(f"Checking S3 bucket {bucket_name}...")
        try:
            # Check if bucket exists and is accessible
            s3.head_bucket(Bucket=bucket_name)
            print(f"\t- PASS: Bucket {bucket_name} is accessible")

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                raise ValueError(f"S3 bucket {bucket_name} not found") from e
            elif error_code == "403":
                raise ValueError(f"Access denied to S3 bucket {bucket_name}") from e
            else:
                raise ValueError(f"Error accessing S3 bucket {bucket_name}: {e}") from e


def verify_api_endpoints() -> None:
    """Verify API endpoints are responding."""
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8080")

    # Check health endpoints
    health_urls = [f"{api_base_url}/api/health"]

    for health_url in health_urls:
        print(f"Checking API health endpoint: {health_url}")

        try:
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                print("\t- PASS: API health endpoint is responding")
                break  # If one works, we're good
            else:
                print(f"\t- WARNING: API health endpoint returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"\t- WARNING: Could not reach API health endpoint: {e}")
    else:
        print("\t- WARNING: None of the health endpoints responded successfully")

    # Check metadata schema endpoint
    schema_url = f"{api_base_url}/api/v1/metadata/schema"
    print(f"Checking metadata schema endpoint: {schema_url}")

    try:
        response = requests.get(schema_url, timeout=10)
        if response.status_code in [200, 401]:  # 401 is expected if auth is required
            print("\t- PASS: Metadata schema endpoint is responding")
        else:
            print(f"\t- WARNING: Metadata schema endpoint returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"\t- WARNING: Could not reach metadata schema endpoint: {e}")


def main() -> None:
    """Entrypoint for metadata validation deployment verification."""
    # Read YAML file
    config_path = HERE.parents[1] / "config.yaml"
    with open(config_path, "r") as file:
        config_full = yaml.safe_load(file)

    # Parse config
    env = config_full.get("env")
    if not env:
        raise ValueError("No 'env' specified in config.yaml")

    config_env = config_full.get(env)
    if not config_env:
        raise ValueError(f"No configuration found for environment '{env}' in config.yaml")

    region = config_env.get("region")
    if not region:
        raise ValueError("No 'region' specified in config.yaml")

    print(f"Verifying metadata validation deployment for environment '{env}' in region '{region}'")

    # Define AWS clients
    cognito_idp = boto3.client("cognito-idp", region_name=region)

    # Cognito auth config verification (unchanged)
    cognitoAuthConfig = config_env.get("cognitoAuthConfig", {})
    if not cognitoAuthConfig:
        raise ValueError(f"No '{env}.cognitoAuthConfig' found for environment '{env}' in config.yaml")

    user_pool_id = cognitoAuthConfig.get("userPoolId")
    user_pool_domain_name = cognitoAuthConfig.get("userPoolDomainName")

    # Preliminary check if only user_pool_domain_name is provided
    if user_pool_domain_name and not user_pool_id:
        print(
            f"Checking if Cognito user pool domain name "
            f"{env}.cognitoAuthConfig.userPoolDomainName={user_pool_domain_name} already exists, please wait..."
        )
        try:
            user_pool_desc = cognito_idp.describe_user_pool_domain(Domain=user_pool_domain_name)
            if not user_pool_desc.get("DomainDescription"):
                print("\t- PASS")
            else:
                print(
                    f"Cognito user pool domain name {env}.cognitoAuthConfig.userPoolDomainName="
                    f"{user_pool_domain_name} already exists. Skipping check."
                )
        except cognito_idp.exceptions.ResourceNotFoundException:
            print("\t- PASS")
        except Exception as e:
            raise ValueError(f"Error accessing Cognito: {e}") from e

    # Existing check if both user_pool_id and user_pool_domain_name are provided
    if user_pool_id and user_pool_domain_name:
        print(
            f"Checking existence of Cognito user pool domain name "
            f"{env}.cognitoAuthConfig.userPoolDomainName={user_pool_domain_name} for Cognito user pool ID "
            f"{env}.cognitoAuthConfig.userPoolId={user_pool_id}, please wait..."
        )
        try:
            user_pool_desc = cognito_idp.describe_user_pool_domain(Domain=user_pool_domain_name)
            if not user_pool_desc.get("DomainDescription"):
                raise ValueError(
                    f"Cognito user pool domain name {env}.cognitoAuthConfig.userPoolDomainName="
                    f"{user_pool_domain_name} not found"
                )
        except cognito_idp.exceptions.ResourceNotFoundException:
            print(
                f"Cognito user pool domain name {env}.cognitoAuthConfig.userPoolDomainName="
                f"{user_pool_domain_name} not found. Skipping check."
            )
            return
        except Exception as e:
            raise ValueError(f"Error accessing Cognito: {e}") from e

        existing_user_pool_id = user_pool_desc.get("DomainDescription", {}).get("user_pool_id")
        if not existing_user_pool_id:
            raise ValueError(
                f"Cognito user pool ID {env}.cognitoAuthConfig.userPoolId={user_pool_id} not found in the "
                "DomainDescription"
            )

        if existing_user_pool_id != user_pool_id:
            raise ValueError(
                f"The Cognito user pool domain name {env}.cognitoAuthConfig.userPoolDomainName="
                f"{user_pool_domain_name} is already associated with another user pool ID ({existing_user_pool_id}). "
                "Please ensure the domain name is unique."
            )

        print("\t- PASS")

    # Verify metadata validation infrastructure
    print("\nVerifying metadata validation infrastructure...")

    try:
        verify_dynamodb_tables(region)
        verify_s3_buckets(region)
        verify_api_endpoints()

        print("\nAll metadata validation infrastructure checks completed successfully!")

    except Exception as e:
        print(f"\nMetadata validation infrastructure verification failed: {e}")
        raise


if __name__ == "__main__":
    main()
