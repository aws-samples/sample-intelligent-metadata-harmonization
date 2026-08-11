# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""DynamoDB implementation of JobStatusSaver interface."""

from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger

from ..interfaces.job_status_saver import JobStatusSaver
from ..models.job import JobResults, MetadataUploadJob


class DynamodbJobStatusSaver(JobStatusSaver):
    """DynamoDB implementation of JobStatusSaver interface using Pydantic models.

    This implementation stores MetadataUploadJob information in a DynamoDB table
    with proper error handling and retry logic.
    """

    def __init__(
        self,
        table_name: str,
        region: str = "us-east-1",
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ):
        """Initialize DynamoDB job status saver.

        Args:
            table_name: Name of the DynamoDB table to use
            region: AWS region for DynamoDB operations
            max_retries: Maximum number of retry attempts for failed operations
            timeout_seconds: Timeout for DynamoDB operations
        """
        self.table_name = table_name
        self.region = region
        self.max_retries = max_retries

        # Configure boto3 with retry settings
        config = Config(
            region_name=region,
            retries={"max_attempts": max_retries, "mode": "adaptive"},
            read_timeout=timeout_seconds,
            connect_timeout=timeout_seconds,
        )

        self.dynamodb = boto3.resource("dynamodb", config=config)
        self.table = self.dynamodb.Table(table_name)

        logger.info(f"Initialized DynamoDB JobStatusSaver for table: {table_name}")

    async def save_job(self, job: MetadataUploadJob) -> None:
        """Save complete job information to DynamoDB.

        Args:
            job: MetadataUploadJob instance with all job data

        Raises:
            Exception: If job cannot be saved to DynamoDB
        """
        try:
            # Convert Pydantic model to DynamoDB item
            item = job.model_dump()

            # Convert results dict to DynamoDB format
            if item.get("results"):
                # Convert JobResults models to dicts
                results_dict = {}
                for version, job_results in item["results"].items():
                    if isinstance(job_results, JobResults):
                        results_dict[version] = job_results.model_dump()
                    else:
                        results_dict[version] = job_results
                item["results"] = results_dict

            self.table.put_item(Item=item)
            logger.debug(f"Saved job for job_id: {job.job_id}, status: {job.status}")

        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to save job for job_id: {job.job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error saving job for job_id: {job.job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def get_job(self, job_id: str) -> Optional[MetadataUploadJob]:
        """Retrieve job by ID from DynamoDB.

        Args:
            job_id: Unique identifier for the job

        Returns:
            MetadataUploadJob instance or None if not found

        Raises:
            Exception: If job cannot be retrieved from DynamoDB
        """
        try:
            response = self.table.get_item(Key={"job_id": job_id})

            if "Item" not in response:
                logger.debug(f"No job found for job_id: {job_id}")
                return None

            item = response["Item"]

            # Convert results dict back to JobResults models
            if item.get("results"):
                results_dict = {}
                for version, result_data in item["results"].items():
                    results_dict[version] = JobResults(**result_data)
                item["results"] = results_dict

            job = MetadataUploadJob(**item)
            logger.debug(f"Retrieved job for job_id: {job_id}, status: {job.status}")
            return job

        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to retrieve job for job_id: {job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error retrieving job for job_id: {job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status and optional fields in DynamoDB.

        Args:
            job_id: Unique identifier for the job
            status: New status for the job
            **kwargs: Optional fields to update (e.g., completed_at)

        Raises:
            Exception: If job status cannot be updated in DynamoDB
        """
        try:
            # Build update expression dynamically
            update_expression = "SET #status = :status"
            expression_attribute_names = {"#status": "status"}
            expression_attribute_values = {":status": status}

            # Add optional fields to update
            for key, value in kwargs.items():
                if value is not None:
                    attr_name = f"#{key}"
                    attr_value = f":{key}"
                    update_expression += f", {attr_name} = {attr_value}"
                    expression_attribute_names[attr_name] = key
                    expression_attribute_values[attr_value] = value

            self.table.update_item(
                Key={"job_id": job_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
            )

            logger.debug(f"Updated job status for job_id: {job_id}, status: {status}")

        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to update job status for job_id: {job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error updating job status for job_id: {job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def add_job_results(self, job_id: str, version: int, job_results: JobResults) -> None:
        """Add results for a specific version to the job in DynamoDB.

        Args:
            job_id: Unique identifier for the job
            version: Version number for these results
            job_results: JobResults instance with storage location info

        Raises:
            Exception: If results cannot be added to DynamoDB
        """
        try:
            version_str = str(version)
            results_data = job_results.model_dump()

            self.table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET results.#version = :results",
                ExpressionAttributeNames={"#version": version_str},
                ExpressionAttributeValues={":results": results_data},
            )

            logger.debug(f"Added results for job_id: {job_id}, version: {version}")

        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to add results for job_id: {job_id}, version: {version}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error adding results for job_id: {job_id}, version: {version}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e

    async def increment_job_version(self, job_id: str) -> int:
        """Increment the job version and return the new version number.

        This method atomically increments the current_version field in DynamoDB
        and returns the new version number.

        Args:
            job_id: Unique identifier for the job

        Returns:
            int: The new version number after incrementing

        Raises:
            Exception: If job version cannot be incremented or job not found
        """
        try:
            response = self.table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="ADD current_version :increment",
                ExpressionAttributeValues={":increment": 1},
                ReturnValues="UPDATED_NEW",
            )

            new_version = response["Attributes"]["current_version"]
            logger.debug(f"Incremented job version for job_id: {job_id}, new version: {new_version}")

            return int(new_version)

        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to increment job version for job_id: {job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error incrementing job version for job_id: {job_id}. Error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
