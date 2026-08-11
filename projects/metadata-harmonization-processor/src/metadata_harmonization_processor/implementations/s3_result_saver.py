# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
S3 implementation of ResultSaver for production environments.

This module provides S3-based storage for CombinedResults using single results.json
file storage with proper error handling, multipart upload support, and AWS authentication.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger

from ..interfaces.result_saver import ResultSaver
from ..models.combined_results import CombinedResults
from ..models.job import JobResults


class S3ResultSaver(ResultSaver):
    """S3 implementation of ResultSaver for production environments.

    Stores CombinedResults in S3 using single results.json file storage approach.
    The entire CombinedResults instance is serialized to JSON and stored as a single
    file, eliminating the need for separate artifact files. Supports multipart uploads
    for large results and provides proper error handling for AWS operations.
    """

    def __init__(
        self,
        bucket_name: str,
        key_prefix: str = "validation-results/",
        region: str = "us-east-1",
        multipart_threshold: int = 100 * 1024 * 1024,  # 100MB
    ):
        """Initialize S3ResultSaver with configuration.

        Args:
            bucket_name: S3 bucket for storing results
            key_prefix: S3 key prefix for organization (should end with /)
            region: AWS region for S3 operations
            multipart_threshold: Size threshold for multipart uploads in bytes

        Raises:
            ValueError: If bucket_name is empty or key_prefix is invalid
            NoCredentialsError: If AWS credentials are not available
        """
        if not bucket_name:
            raise ValueError("bucket_name cannot be empty")

        if not key_prefix.endswith("/"):
            key_prefix += "/"

        self.bucket_name = bucket_name
        self.key_prefix = key_prefix
        self.region = region
        self.multipart_threshold = multipart_threshold

        # Configure S3 client with retry settings
        config = Config(region_name=region, retries={"max_attempts": 3, "mode": "adaptive"})

        try:
            self.s3_client = boto3.client("s3", config=config)
            # Test credentials by checking access to the specific bucket we'll use
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully verified access to S3 bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.error(f"S3 bucket '{self.bucket_name}' not found or not accessible.")
            else:
                logger.error(f"Failed to access S3 bucket '{self.bucket_name}': {e}")
            raise

    def _generate_s3_key(self, job_id: str, version: int, artifact_name: str) -> str:
        """Generate S3 key for storing result artifacts.

        Args:
            job_id: Unique job identifier
            version: Version number for this result set
            artifact_name: Name of the artifact (e.g., 'results.json', 'original_data.csv')

        Returns:
            S3 key path in format: {prefix}{job_id}/v{version}/{artifact_name}
        """
        return f"{self.key_prefix}{job_id}/v{version}/{artifact_name}"

    async def save_results(
        self,
        job_id: str,
        version: int,
        combined_results: CombinedResults,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JobResults:
        """Save CombinedResults to single results.json file in S3.

        The entire CombinedResults instance is serialized using combined_results.to_dict()
        and stored as a single JSON file at:
        - validation-results/{job_id}/v{version}/results.json

        Args:
            job_id: Unique identifier for the processing job
            version: Version number for this result set
            combined_results: CombinedResults instance containing both validation and schema alignment data
            metadata: Optional metadata about the processing

        Returns:
            JobResults with S3 storage location information

        Raises:
            ClientError: If S3 operations fail
            ValueError: If job_id is empty or version is invalid
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")
        if version < 1:
            raise ValueError("version must be >= 1")

        try:
            # Generate S3 key for results.json
            s3_key = self._generate_s3_key(job_id, version, "results.json")

            # Prepare data for storage using single file approach
            storage_data = {
                "job_id": job_id,
                "version": version,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "combined_results": combined_results.to_dict(),
                "metadata": metadata or {},
            }

            # Convert to JSON string
            json_data = json.dumps(storage_data, indent=2)
            json_bytes = json_data.encode("utf-8")

            # Use multipart upload for large files
            if len(json_bytes) > self.multipart_threshold:
                logger.info(f"Using multipart upload for large combined results: {len(json_bytes)} bytes")
                await self._multipart_upload(s3_key, json_bytes)
            else:
                # Standard upload for smaller files
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=json_bytes,
                    ContentType="application/json",
                    Metadata={
                        "job-id": job_id,
                        "version": str(version),
                        "content-type": "combined-results",
                    },
                )

            logger.info(f"Successfully saved combined results for job {job_id} version {version}")

            # Return JobResults pointing to the results.json file
            return JobResults(storage_type="s3", location=s3_key, bucket=self.bucket_name)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to save combined results to S3: {error_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving combined results to S3: {e}")
            raise

    async def _multipart_upload(self, s3_key: str, data: bytes) -> None:
        """Perform multipart upload for large files.

        Args:
            s3_key: S3 key for the object
            data: Bytes to upload

        Raises:
            ClientError: If multipart upload fails
        """
        try:
            # Initiate multipart upload
            response = self.s3_client.create_multipart_upload(
                Bucket=self.bucket_name, Key=s3_key, ContentType="application/json"
            )
            upload_id = response["UploadId"]

            # Upload parts (5MB minimum part size for S3)
            part_size = max(5 * 1024 * 1024, len(data) // 10000)  # 5MB or 1/10000 of file size
            parts = []

            for i in range(0, len(data), part_size):
                part_number = len(parts) + 1
                part_data = data[i : i + part_size]

                response = self.s3_client.upload_part(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data,
                )

                parts.append({"ETag": response["ETag"], "PartNumber": part_number})

            # Complete multipart upload
            self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=s3_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )

        except ClientError:
            # Abort multipart upload on failure
            try:
                self.s3_client.abort_multipart_upload(Bucket=self.bucket_name, Key=s3_key, UploadId=upload_id)
            except Exception:
                pass  # Best effort cleanup
            raise

    async def get_results(self, job_results: JobResults) -> Optional[CombinedResults]:
        """Retrieve CombinedResults from single results.json file in S3.

        Args:
            job_results: JobResults with S3 storage location information

        Returns:
            CombinedResults instance or None if not found

        Raises:
            ValueError: If job_results is not for S3 storage
            ClientError: If S3 operations fail
        """
        if job_results.storage_type != "s3":
            raise ValueError(f"Expected S3 storage type, got: {job_results.storage_type}")

        if not job_results.bucket:
            raise ValueError("bucket is required for S3 storage type")

        try:
            # Get results from single results.json file
            results_key = job_results.location

            # Handle both directory and file paths for backward compatibility
            if not results_key.endswith("results.json"):
                if results_key.endswith("/"):
                    results_key = f"{results_key}results.json"
                else:
                    results_key = f"{results_key}/results.json"

            try:
                response = self.s3_client.get_object(Bucket=job_results.bucket, Key=results_key)

                # Read and parse JSON data
                json_data = response["Body"].read().decode("utf-8")
                storage_data = json.loads(json_data)

                # Extract CombinedResults from storage format
                combined_results_data = storage_data.get("combined_results")
                if not combined_results_data:
                    logger.warning(f"No combined_results data found in S3 object: {results_key}")
                    return None

                # Reconstruct CombinedResults using from_dict method
                return CombinedResults.from_dict(combined_results_data)

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "NoSuchKey":
                    logger.warning(f"Results file not found in S3: {results_key}")
                    return None
                else:
                    logger.error(f"Failed to retrieve combined results from S3: {error_code} - {e}")
                    raise
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from S3 object: {e}")
                raise

        except Exception as e:
            logger.error(f"Unexpected error retrieving combined results from S3: {e}")
            raise

    async def list_results(self, job_id: str) -> List[JobResults]:
        """List all result versions for a job by listing S3 objects with job_id prefix.

        Args:
            job_id: Unique identifier for the processing job

        Returns:
            List of JobResults for all versions of this job, sorted by version

        Raises:
            ValueError: If job_id is empty
            ClientError: If S3 operations fail
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        job_prefix = f"{self.key_prefix}{job_id}/"
        results = []

        try:
            # List objects with job prefix
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=job_prefix)

            for page in page_iterator:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]

                    # Parse version from key pattern: {prefix}{job_id}/v{version}/results.json
                    if key.endswith("/results.json"):
                        try:
                            # Extract version from path
                            path_parts = key.replace(job_prefix, "").split("/")
                            if len(path_parts) >= 2 and path_parts[0].startswith("v"):
                                # Validate that the version segment parses as an int
                                int(path_parts[0][1:])

                                # Return full path to results.json file for single file storage
                                results.append(
                                    JobResults(
                                        storage_type="s3",
                                        location=key,
                                        bucket=self.bucket_name,
                                    )
                                )
                        except (ValueError, IndexError):
                            # Skip objects that don't match expected pattern
                            logger.debug(f"Skipping object with unexpected key pattern: {key}")
                            continue

            # Sort by version (extract from location path)
            def extract_version(job_result: JobResults) -> int:
                try:
                    # Extract version from location: {prefix}{job_id}/v{version}/results.json
                    path_parts = job_result.location.replace(job_prefix, "").split("/")
                    # Remove empty parts and find version part
                    path_parts = [p for p in path_parts if p]
                    for part in path_parts:
                        if part.startswith("v"):
                            return int(part[1:])
                except (ValueError, IndexError):
                    pass
                return 0

            results.sort(key=extract_version)

            logger.info(f"Found {len(results)} result versions for job {job_id}")
            return results

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to list results from S3: {error_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing results from S3: {e}")
            raise
