# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Local implementation of JobStatusSaver interface for development without cloud resources."""

import json
from pathlib import Path
from typing import Literal, Optional

from loguru import logger

from ..interfaces.job_status_saver import JobStatusSaver
from ..models.job import JobResults, MetadataUploadJob


class LocalJobStatusSaver(JobStatusSaver):
    """Local implementation of JobStatusSaver using Pydantic models for development without cloud resources.

    This implementation supports both in-memory and file-based storage modes:
    - memory: Stores job status in memory (lost when process ends)
    - file: Persists job status as JSON files in a configurable directory
    """

    def __init__(
        self,
        storage_type: Literal["memory", "file"] = "memory",
        storage_dir: Optional[str] = None,
    ):
        """Initialize local job status saver.

        Args:
            storage_type: Either "memory" for in-memory storage or "file" for JSON file persistence
            storage_dir: Directory for JSON files when using file storage (defaults to ./job_status)
        """
        self.storage_type = storage_type
        self.storage_dir = Path(storage_dir or "./job_status")
        self._memory_store: dict[str, MetadataUploadJob] = {}

        if storage_type == "file":
            # Create storage directory if it doesn't exist
            try:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Initialized LocalJobStatusSaver with file storage in: {self.storage_dir}")
            except OSError as e:
                error_msg = f"Failed to create storage directory {self.storage_dir}: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e
        else:
            logger.info("Initialized LocalJobStatusSaver with in-memory storage")

    async def save_job(self, job: MetadataUploadJob) -> None:
        """Save complete job information.

        Args:
            job: MetadataUploadJob instance with all job data

        Raises:
            Exception: If job cannot be saved
        """
        try:
            if self.storage_type == "memory":
                self._memory_store[job.job_id] = job
                logger.debug(f"Saved job in memory for job_id: {job.job_id}, status: {job.status}")
            else:  # file
                file_path = self.storage_dir / f"{job.job_id}.json"
                try:
                    # Use Pydantic's model_dump for serialization
                    data = job.model_dump()
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=2, default=str)
                    logger.debug(f"Saved job to file for job_id: {job.job_id}, status: {job.status}")
                except (OSError, IOError) as e:
                    error_msg = f"Failed to write job file for job_id: {job.job_id}. Error: {str(e)}"
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
                except TypeError as e:
                    error_msg = f"Failed to serialize job data for job_id: {job.job_id}. Error: {str(e)}"
                    logger.error(error_msg)
                    raise Exception(error_msg) from e

        except Exception as e:
            if not isinstance(e, Exception) or "Failed to" not in str(e):
                error_msg = f"Unexpected error saving job for job_id: {job.job_id}. Error: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e
            raise

    async def get_job(self, job_id: str) -> Optional[MetadataUploadJob]:
        """Retrieve job by ID.

        Args:
            job_id: Unique identifier for the job

        Returns:
            MetadataUploadJob instance or None if not found

        Raises:
            Exception: If job cannot be retrieved
        """
        try:
            if self.storage_type == "memory":
                result = self._memory_store.get(job_id)
                if result:
                    logger.debug(f"Retrieved job from memory for job_id: {job_id}")
                else:
                    logger.debug(f"No job found in memory for job_id: {job_id}")
                return result
            else:  # file
                file_path = self.storage_dir / f"{job_id}.json"
                if file_path.exists():
                    try:
                        with open(file_path, "r") as f:
                            data = json.load(f)

                        # Convert results dict back to JobResults models
                        if data.get("results"):
                            results_dict = {}
                            for version, result_data in data["results"].items():
                                results_dict[version] = JobResults(**result_data)
                            data["results"] = results_dict

                        # Use Pydantic's model_validate for deserialization
                        job = MetadataUploadJob(**data)
                        logger.debug(f"Retrieved job from file for job_id: {job_id}")
                        return job
                    except (OSError, IOError) as e:
                        error_msg = f"Failed to read job file for job_id: {job_id}. Error: {str(e)}"
                        logger.error(error_msg)
                        raise Exception(error_msg) from e
                    except json.JSONDecodeError as e:
                        error_msg = f"Failed to parse job file for job_id: {job_id}. Error: {str(e)}"
                        logger.error(error_msg)
                        raise Exception(error_msg) from e
                    except Exception as e:
                        error_msg = f"Failed to deserialize job data for job_id: {job_id}. Error: {str(e)}"
                        logger.error(error_msg)
                        raise Exception(error_msg) from e
                else:
                    logger.debug(f"No job file found for job_id: {job_id}")
                    return None

        except Exception as e:
            if not isinstance(e, Exception) or "Failed to" not in str(e):
                error_msg = f"Unexpected error retrieving job for job_id: {job_id}. Error: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e
            raise

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status and optional fields.

        Args:
            job_id: Unique identifier for the job
            status: New status for the job
            **kwargs: Optional fields to update (e.g., completed_at)

        Raises:
            Exception: If job status cannot be updated
        """
        try:
            # Get existing job
            job = await self.get_job(job_id)
            if job is None:
                error_msg = f"Job not found for job_id: {job_id}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Update status
            job.status = status

            # Update optional fields
            for key, value in kwargs.items():
                if hasattr(job, key) and value is not None:
                    setattr(job, key, value)

            # Save updated job
            await self.save_job(job)
            logger.debug(f"Updated job status for job_id: {job_id}, status: {status}")

        except Exception as e:
            if not isinstance(e, Exception) or "Job not found" not in str(e):
                error_msg = f"Unexpected error updating job status for job_id: {job_id}. Error: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e
            raise

    async def add_job_results(self, job_id: str, version: int, job_results: JobResults) -> None:
        """Add results for a specific version to the job.

        Args:
            job_id: Unique identifier for the job
            version: Version number for these results
            job_results: JobResults instance with storage location info

        Raises:
            Exception: If results cannot be added
        """
        try:
            # Get existing job
            job = await self.get_job(job_id)
            if job is None:
                error_msg = f"Job not found for job_id: {job_id}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Add results for the version
            version_str = str(version)
            job.results[version_str] = job_results

            # Save updated job
            await self.save_job(job)
            logger.debug(f"Added results for job_id: {job_id}, version: {version}")

        except Exception as e:
            if not isinstance(e, Exception) or "Job not found" not in str(e):
                error_msg = f"Unexpected error adding results for job_id: {job_id}, version: {version}. Error: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e
            raise

    async def increment_job_version(self, job_id: str) -> int:
        """Increment the job version and return the new version number.

        This method is used when updating an existing validation job with new data.
        It atomically increments the current_version field and returns the new version.

        Args:
            job_id: Unique identifier for the job

        Returns:
            int: The new version number after incrementing

        Raises:
            Exception: If job version cannot be incremented or job not found
        """
        try:
            # Get existing job
            job = await self.get_job(job_id)
            if job is None:
                error_msg = f"Job not found for job_id: {job_id}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Increment version
            job.current_version += 1
            new_version = job.current_version

            # Save updated job
            await self.save_job(job)
            logger.debug(f"Incremented job version for job_id: {job_id}, new version: {new_version}")

            return new_version

        except Exception as e:
            if not isinstance(e, Exception) or "Job not found" not in str(e):
                error_msg = f"Unexpected error incrementing job version for job_id: {job_id}. Error: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e
            raise
