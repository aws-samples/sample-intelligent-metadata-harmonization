# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Data saver coordinator for metadata harmonization processor."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .interfaces.job_status_saver import JobStatusSaver
from .interfaces.result_saver import ResultSaver
from .models.change_tracking import ChangeObject, ChangesSummary
from .models.combined_results import CombinedResults
from .models.job import JobResults, MetadataUploadJob
from .utils.schema_change_detector import ChangeDetector


class DataSaver:
    """Coordinator class that manages both job status and result storage.

    This class provides a unified interface for saving job information and
    validation results, coordinating between JobStatusSaver and ResultSaver
    implementations to ensure consistent data persistence.
    """

    def __init__(
        self,
        job_status_saver: JobStatusSaver,
        result_saver: ResultSaver,
        enable_change_detection: bool = True,
    ):
        """Initialize DataSaver with storage implementations.

        Args:
            job_status_saver: Implementation for job status persistence
            result_saver: Implementation for validation result storage
            enable_change_detection: Whether to enable change detection (default: True)
        """
        self.job_status_saver = job_status_saver
        self.result_saver = result_saver
        self.enable_change_detection = enable_change_detection
        self.change_detector = ChangeDetector() if enable_change_detection else None

    async def save_job_and_results(
        self,
        job: MetadataUploadJob,
        combined_results: CombinedResults,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JobResults:
        """Save job status and combined validation/schema alignment results atomically.

        This method coordinates saving both the job status and the combined
        results using single results.json file storage, ensuring that the job record
        includes the correct storage location information for the results.

        The job completion status is determined based on validation results:
        - "completed": Job completed successfully with no validation errors
        - "completed_with_errors": Job completed successfully but validation errors were found
        - "failed": Job failed during processing (set in exception handler)

        Args:
            job: MetadataUploadJob instance with job information
            combined_results: CombinedResults instance containing both validation and schema alignment data
            metadata: Optional metadata about the processing

        Returns:
            JobResults with storage location information

        Raises:
            Exception: If either job or results cannot be saved
        """
        if combined_results is None:
            raise ValueError("CombinedResults cannot be None")

        if not combined_results.has_validation_results():
            raise ValueError("CombinedResults must contain ValidationResults")

        try:
            # Increment the job version for this new processing run
            # current_version = await self.job_status_saver.increment_job_version(job.job_id)
            current_version = job.current_version

            # Log what we're saving
            if combined_results.has_schema_alignment_results():
                logger.info(
                    f"Saving combined validation and schema alignment results for job {job.job_id}, version {current_version}"
                )
            else:
                logger.info(f"Saving validation results only for job {job.job_id}, version {current_version}")

            # Do change detection FIRST (before saving) to include it in the single save
            if self.enable_change_detection and self.change_detector and current_version > 1:
                try:
                    logger.info(f"Starting change detection for job {job.job_id}, version {current_version}")
                    changes = await self.change_detector.detect_changes(
                        job_id=job.job_id,
                        current_version=current_version,
                        current_results=combined_results,
                        result_saver=self.result_saver,
                    )

                    if changes:
                        logger.info(f"Change detection completed for job {job.job_id}: {len(changes)} changes detected")
                        # Create changes summary
                        changes_summary = self._create_changes_summary(changes)
                        logger.info(
                            f"Changes summary for job {job.job_id}: {changes_summary.total_changes} total changes "
                            f"({changes_summary.adds} adds, {changes_summary.removes} removes, {changes_summary.renames} renames), "
                            f"{changes_summary.system_changes} system changes, {changes_summary.user_changes} user changes"
                        )

                        # Create change tracking results and update combined_results
                        from .models.change_tracking import ChangeTrackingResults

                        change_tracking = ChangeTrackingResults(
                            changes=changes,
                            summary=changes_summary,
                            comparison_metadata={
                                "detection_timestamp": datetime.utcnow().isoformat(),
                                "compared_versions": [
                                    current_version - 1,
                                    current_version,
                                ],
                                "job_id": job.job_id,
                            },
                        )

                        # Update the combined_results with change tracking data
                        combined_results.change_tracking = change_tracking
                        logger.info(f"Added change tracking data to combined results for job {job.job_id}")
                    else:
                        logger.info(f"Change detection completed for job {job.job_id}: no changes detected")

                except Exception as change_error:
                    # Log change detection errors but don't fail the job completion
                    logger.error(f"Change detection failed for job {job.job_id}: {change_error}")
                    logger.info("Continuing with save operation despite change detection failure")

            # Save the combined results (with change tracking if available) in a SINGLE operation
            job_results = await self.result_saver.save_results(
                job_id=job.job_id,
                version=current_version,
                combined_results=combined_results,
                metadata=metadata,
            )

            # Add the results to the job record
            await self.job_status_saver.add_job_results(
                job_id=job.job_id, version=current_version, job_results=job_results
            )

            # Determine completion status based on validation results
            has_validation_errors = combined_results.validation_results.summary.total_errors > 0
            completion_status = "completed_with_errors" if has_validation_errors else "completed"

            # Update job status with appropriate completion status
            await self.job_status_saver.update_job_status(
                job_id=job.job_id,
                status=completion_status,
                completed_at=datetime.utcnow().isoformat(),
            )

            logger.info(f"Successfully saved job and results for {job.job_id} with status '{completion_status}'")
            return job_results

        except Exception as e:
            # Update job status to failed if saving results fails
            logger.error(f"Failed to save job and results for {job.job_id}: {e}")
            try:
                await self.job_status_saver.update_job_status(
                    job_id=job.job_id,
                    status="failed",
                    completed_at=datetime.utcnow().isoformat(),
                )
                logger.info(f"Updated job {job.job_id} status to 'failed' due to save error")
            except Exception as status_error:
                logger.error(f"Failed to update job status to failed: {status_error}")

            raise

    async def create_job(
        self, job_id: str, user_id: str, core_schema_id: str, program_schema_id: str
    ) -> MetadataUploadJob:
        """Create a new job record or return existing job.

        Version incrementing happens in save_job_and_results when results are actually saved.

        Args:
            job_id: Unique identifier for the job
            user_id: User identifier from authentication
            core_schema_id: Core schema used for validation
            program_schema_id: Program schema used for validation

        Returns:
            Created or existing MetadataUploadJob instance

        Raises:
            Exception: If job cannot be created
        """
        # Check if job already exists
        existing_job = await self.job_status_saver.get_job(job_id)

        if existing_job:
            # Job exists, return it (version will be incremented when results are saved)
            logger.info(f"Found existing job {job_id} with current version {existing_job.current_version}")
            return existing_job
        else:
            # Create new job with version 1
            job = MetadataUploadJob(
                job_id=job_id,
                user_id=user_id,
                core_schema_id=core_schema_id,
                program_schema_id=program_schema_id,
                status="pending",
                created_at=datetime.utcnow().isoformat(),
                current_version=1,
                results={},
            )

            await self.job_status_saver.save_job(job)
            logger.info(f"Created new job {job_id} with version 1")
            return job

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status.

        Args:
            job_id: Unique identifier for the job
            status: New status for the job
            **kwargs: Optional fields to update

        Raises:
            Exception: If job status cannot be updated
        """
        await self.job_status_saver.update_job_status(job_id, status, **kwargs)
        logger.info(f"Updated job {job_id} status to {status}")

    async def get_job(self, job_id: str) -> Optional[MetadataUploadJob]:
        """Retrieve job by ID.

        Args:
            job_id: Unique identifier for the job

        Returns:
            MetadataUploadJob instance or None if not found
        """
        return await self.job_status_saver.get_job(job_id)

    async def get_results(self, job_results: JobResults) -> Optional[CombinedResults]:
        """Retrieve combined validation and schema alignment results using JobResults location info.

        Args:
            job_results: JobResults with storage location information

        Returns:
            CombinedResults instance or None if not found
        """
        return await self.result_saver.get_results(job_results)

    async def list_results(self, job_id: str) -> List[JobResults]:
        """List all saved results for a job across versions.

        Args:
            job_id: Unique identifier for the processing job

        Returns:
            List of JobResults for all versions of this job
        """
        return await self.result_saver.list_results(job_id)

    def _create_changes_summary(self, changes: List[ChangeObject]) -> ChangesSummary:
        """Create a summary of changes from a list of change objects.

        This method calculates summary statistics from change objects including:
        - Total number of changes
        - Counts for different change types (add, remove, rename)
        - Counts for different change sources (system, user)

        Args:
            changes: List of ChangeObject instances to summarize

        Returns:
            ChangesSummary instance with calculated statistics

        Raises:
            ValueError: If changes list contains invalid change objects
        """
        logger.debug(f"Creating changes summary for {len(changes)} changes")

        try:
            # Use the built-in class method to create summary from changes
            summary = ChangesSummary.from_changes(changes)

            logger.info(
                f"Created changes summary: {summary.total_changes} total changes "
                f"({summary.adds} adds, {summary.removes} removes, {summary.renames} renames), "
                f"{summary.system_changes} system changes, {summary.user_changes} user changes"
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to create changes summary: {e}")
            raise ValueError(f"Failed to create changes summary: {e}") from e
