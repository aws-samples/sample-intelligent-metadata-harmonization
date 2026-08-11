# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Job status persistence interface for metadata harmonization processor."""

from abc import ABC, abstractmethod
from typing import Optional

from ..models.job import JobResults, MetadataUploadJob


class JobStatusSaver(ABC):
    """Interface for persisting job status using Pydantic models."""

    @abstractmethod
    async def save_job(self, job: MetadataUploadJob) -> None:
        """Save complete job information.

        Args:
            job: MetadataUploadJob instance with all job data

        Raises:
            Exception: If job cannot be saved
        """
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[MetadataUploadJob]:
        """Retrieve job by ID.

        Args:
            job_id: Unique identifier for the job

        Returns:
            MetadataUploadJob instance or None if not found

        Raises:
            Exception: If job cannot be retrieved
        """
        pass

    @abstractmethod
    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status and optional fields.

        Args:
            job_id: Unique identifier for the job
            status: New status for the job
            **kwargs: Optional fields to update (e.g., completed_at)

        Raises:
            Exception: If job status cannot be updated
        """
        pass

    @abstractmethod
    async def add_job_results(self, job_id: str, version: int, job_results: JobResults) -> None:
        """Add results for a specific version to the job.

        Args:
            job_id: Unique identifier for the job
            version: Version number for these results
            job_results: JobResults instance with storage location info

        Raises:
            Exception: If results cannot be added
        """
        pass

    @abstractmethod
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
        pass
