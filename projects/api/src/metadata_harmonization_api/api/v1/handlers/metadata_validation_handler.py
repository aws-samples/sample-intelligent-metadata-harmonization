# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Handler for metadata validation business logic."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, Request, UploadFile

from metadata_harmonization_api.api.v1.models.metadata import (
    ValidationJobResponse,
    ValidationStatusResponse,
)
from metadata_harmonization_api.config import MetadataConfig, api_config
from metadata_harmonization_processor.interfaces.job_status_saver import JobStatusSaver
from metadata_harmonization_processor.interfaces.schema_collector import SchemaCollector
from metadata_harmonization_processor.models.job import MetadataUploadJob
from metadata_harmonization_api.workers.metadata_worker import create_background_task_function


logger = logging.getLogger(__name__)


class MetadataValidationHandler:
    """Handler for metadata validation business logic."""

    def __init__(
        self,
        schema_collector: SchemaCollector,
        job_status_saver: JobStatusSaver,
        processor_manager,
        metadata_config: Optional[MetadataConfig] = None,
    ):
        """
        Initialize the metadata validation handler.

        Args:
            schema_collector: Schema collector for validation
            job_status_saver: Job status saver for persistence
            processor_manager: ProcessorManager for handling processor instances
            metadata_config: Metadata configuration used for upload validation. Defaults to
                the module-level config, which carries the same values when no YAML is loaded.
        """
        self.schema_collector = schema_collector
        self.job_status_saver = job_status_saver
        self.processor_manager = processor_manager
        self.metadata_config = metadata_config or api_config.metadata

    async def validate_csv_file(self, file: UploadFile) -> None:
        """
        Validate uploaded CSV file format and size against the configured limits.

        Both the accepted MIME types and the size cap come from configuration
        (``metadata.allowed_file_types`` and ``metadata.max_file_size_mb``) rather than
        being hardcoded here, so the deployed limits are the ones operators configure.

        Args:
            file: The uploaded file to validate

        Raises:
            HTTPException: If file validation fails
        """
        # Check file extension
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Invalid file format. Only CSV files are allowed.")

        # Check MIME type against the configured allow-list
        allowed_mime_types = self.metadata_config.allowed_file_types
        if file.content_type and file.content_type not in allowed_mime_types:
            raise HTTPException(
                status_code=400, detail=f"Invalid MIME type '{file.content_type}'. Only CSV files are allowed."
            )

        # Check file size against the configured cap
        max_size_mb = self.metadata_config.max_file_size_mb
        max_size_bytes = max_size_mb * 1024 * 1024
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_size_mb}MB, got {file_size / (1024*1024):.1f}MB.",
            )

        # Reset file position for later reading
        file.file.seek(0)

    async def _get_owned_job(self, job_id: str, request: Request) -> MetadataUploadJob:
        """
        Fetch a job and verify the caller owns it.

        Raises HTTPException(404) both when the job doesn't exist and when it
        exists but belongs to a different user - never 403 - so this endpoint
        can't be used as a job-ID oracle to distinguish "not found" from
        "not yours".
        """
        job = await self.job_status_saver.get_job(job_id)
        caller_id = getattr(request.state, "user_id", "anonymous")
        if not job or job.user_id != caller_id:
            raise HTTPException(status_code=404, detail=f"Validation job {job_id} not found")
        return job

    async def trigger_metadata_processing(
        self,
        job_id: str,
        background_tasks: BackgroundTasks,
        csv_file_content: bytes,
        core_schema_id: str,
        program_schema_id: str,
        version: int = 1,
    ) -> None:
        """
        Trigger background task for metadata processing using MetadataHarmonizationProcessor.

        This method replaces the mocked validation logic with actual processor integration,
        using the processor's complete pipeline including AI predictions and the
        processor's DataSaver for unified result and job status management.

        Args:
            job_id: The job ID to process
            background_tasks: FastAPI background tasks
            csv_file_content: CSV file content as bytes
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier
            version: Job version number (default: 1)
        """
        logger.info(f"Triggering metadata processing for job {job_id} with actual processor integration")

        # Create background task function using MetadataWorker
        background_task_func = create_background_task_function(
            processor_manager=self.processor_manager,
            job_id=job_id,
            csv_content=csv_file_content,
            core_schema_id=core_schema_id,
            program_schema_id=program_schema_id,
            version=version,
        )

        # Add task to FastAPI background tasks
        background_tasks.add_task(background_task_func)

        logger.info(f"Background task scheduled for job {job_id} using MetadataHarmonizationProcessor")

    async def create_validation_job(
        self,
        background_tasks: BackgroundTasks,
        request: Request,
        file: UploadFile,
        core_schema_id: str,
        program_schema_id: str,
    ) -> ValidationJobResponse:
        """
        Create a new metadata validation job.

        Args:
            background_tasks: FastAPI background tasks
            request: FastAPI request object
            file: CSV file to validate
            core_schema_id: Core schema identifier for validation
            program_schema_id: Program schema identifier for validation

        Returns:
            ValidationJobResponse with job ID

        Raises:
            HTTPException: If validation fails
        """
        try:
            logger.info(
                f"Creating validation job for core_schema_id={core_schema_id}, program_schema_id={program_schema_id}"
            )

            # Validate file format and size
            await self.validate_csv_file(file)

            # Read file content for processing
            csv_content = await file.read()

            # Validate that the schema combination exists
            logger.info(
                f"Validating schema combination: core_schema_id='{core_schema_id}', program_schema_id='{program_schema_id}'"
            )
            try:
                await self.schema_collector.get_schema(program_schema_id, core_schema_id)
                logger.info(
                    f"Schema validation successful for combination: core_schema_id='{core_schema_id}', program_schema_id='{program_schema_id}'"
                )
            except ValueError as e:
                logger.warning(
                    f"Invalid schema combination requested: core_schema_id='{core_schema_id}', program_schema_id='{program_schema_id}'. Error: {e}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid schema combination: core_schema_id='{core_schema_id}', program_schema_id='{program_schema_id}'",
                )
            except FileNotFoundError as e:
                logger.error(
                    f"Schema files not found for combination: core_schema_id='{core_schema_id}', program_schema_id='{program_schema_id}'. Error: {e}"
                )
                raise HTTPException(status_code=500, detail="Schema files not available on server")
            except Exception as e:
                logger.error(
                    f"Unexpected error during schema validation: core_schema_id='{core_schema_id}', program_schema_id='{program_schema_id}'. Error: {e}"
                )
                logger.exception("Full schema validation exception details:")
                raise HTTPException(status_code=500, detail="Internal server error during schema validation")

            # Generate job ID and get user ID from request state
            job_id = str(uuid4())
            user_id = getattr(request.state, "user_id", "anonymous")

            # Create job record
            job_data = MetadataUploadJob(
                job_id=job_id,
                user_id=user_id,
                core_schema_id=core_schema_id,
                program_schema_id=program_schema_id,
                status="pending",
                created_at=datetime.utcnow().isoformat(),
                completed_at=None,
                current_version=1,
                results={},
            )

            # Store job in DynamoDB
            await self.job_status_saver.save_job(job_data)

            # Trigger background processing with actual MetadataHarmonizationProcessor
            await self.trigger_metadata_processing(
                job_id, background_tasks, csv_content, core_schema_id, program_schema_id, version=1
            )

            logger.info(f"Successfully created validation job {job_id}")
            return ValidationJobResponse(job_id=UUID(job_id))

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Error creating validation job: {e}")
            raise HTTPException(status_code=500, detail="Internal server error while creating validation job")

    async def update_validation_job(
        self,
        metadata_id: UUID,
        background_tasks: BackgroundTasks,
        request: Request,
        file: UploadFile,
    ) -> ValidationJobResponse:
        """
        Update an existing metadata validation job with new CSV file.

        Args:
            metadata_id: UUID of the existing job
            background_tasks: FastAPI background tasks
            request: FastAPI request object
            file: Updated CSV file to validate

        Returns:
            ValidationJobResponse with job ID

        Raises:
            HTTPException: If validation fails or job not found
        """
        try:
            job_id = str(metadata_id)
            logger.info(f"Updating validation job {job_id}")

            # Validate file format and size
            await self.validate_csv_file(file)

            # Check if job exists and belongs to the caller
            existing_job = await self._get_owned_job(job_id, request)

            # Read file content for processing
            csv_content = await file.read()

            # Increment job version
            new_version = await self.job_status_saver.increment_job_version(job_id)

            # Reset status to pending for new processing (matches create_validation_job behavior)
            await self.job_status_saver.update_job_status(job_id, "pending")

            # Trigger background processing with existing schema IDs and new version
            await self.trigger_metadata_processing(
                job_id,
                background_tasks,
                csv_content,
                existing_job.core_schema_id,
                existing_job.program_schema_id,
                version=new_version,
            )

            logger.info(f"Successfully updated validation job {job_id} to version {new_version}")
            return ValidationJobResponse(job_id=metadata_id)

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Error updating validation job {metadata_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error while updating validation job")

    async def get_validation_status(
        self,
        metadata_id: UUID,
        request: Request,
    ) -> ValidationStatusResponse:
        """
        Get the status of a metadata validation job using single results.json approach.

        This method loads CombinedResults from a single results.json file instead of
        loading separate artifact files. The CombinedResults contains both validation
        results and schema alignment results in a unified structure.

        Args:
            metadata_id: UUID of the job
            request: FastAPI request object

        Returns:
            ValidationStatusResponse with job status and combined results from single file

        Raises:
            HTTPException: If job not found
        """
        try:
            job_id = str(metadata_id)
            logger.info(f"Retrieving status for validation job {job_id}")

            # Get job from database and verify the caller owns it
            job = await self._get_owned_job(job_id, request)

            # Convert job data to response format
            response_data = {
                "job_id": UUID(job.job_id),
                "user_id": job.user_id,
                "core_schema_id": job.core_schema_id,
                "program_schema_id": job.program_schema_id,
                "status": job.status,
                "created_at": datetime.fromisoformat(job.created_at),
                "completed_at": datetime.fromisoformat(job.completed_at) if job.completed_at else None,
                "current_version": job.current_version,
                "latest_results": None,  # Will be populated when job is completed
            }

            # If job is completed, get combined results from single results.json file
            if job.status in ["completed", "completed_with_errors"] and job.results:
                # Get the latest version results
                latest_version = str(job.current_version)
                if latest_version in job.results:
                    job_results = job.results[latest_version]
                    try:
                        # Get a processor instance to access its data_saver
                        processor = await self.processor_manager.get_processor(job_id)

                        # Load CombinedResults from single results.json file
                        combined_results_processor = await processor.data_saver.get_results(job_results)

                        if combined_results_processor:
                            # Import API models
                            from metadata_harmonization_api.api.v1.models.metadata import (
                                CombinedResults,
                                SchemaAlignmentResults,
                            )

                            # Create API CombinedResults
                            api_combined_results = CombinedResults()

                            # Extract ValidationResults (already in correct format)
                            if combined_results_processor.validation_results:
                                api_combined_results.validation_results = combined_results_processor.validation_results
                                logger.info(
                                    f"Job {job_id} completed, loaded {len(combined_results_processor.validation_results.validation_results)} validation results"
                                )

                            # Extract and convert SchemaAlignmentResults
                            if combined_results_processor.schema_alignment_results:
                                from metadata_harmonization_api.api.v1.models.metadata import (
                                    SchemaAlignmentChangeDetail,
                                    SchemaAlignmentResultsSummary,
                                )

                                # Convert change details from processor model to API model
                                api_change_details = [
                                    SchemaAlignmentChangeDetail(
                                        change_type=change.change_type,
                                        original_column=change.original_column,
                                        new_column=change.new_column,
                                        reason=change.reason,
                                        row_count_affected=change.row_count_affected,
                                        confidence_score=getattr(change, "confidence_score", 0.0),
                                        confidence_level=getattr(change, "confidence_level", "Low"),
                                        llm_confidence_level=getattr(change, "llm_confidence_level", None),
                                    )
                                    for change in combined_results_processor.schema_alignment_results.schema_alignment_results
                                ]

                                # Convert summary from processor model to API model
                                api_summary = SchemaAlignmentResultsSummary(
                                    job_id=combined_results_processor.schema_alignment_results.summary.job_id,
                                    version=combined_results_processor.schema_alignment_results.summary.version,
                                    timestamp=combined_results_processor.schema_alignment_results.summary.timestamp,
                                    original_data_csv=combined_results_processor.schema_alignment_results.summary.original_data_csv,
                                    aligned_data_csv=combined_results_processor.schema_alignment_results.summary.aligned_data_csv,
                                    total_changes=combined_results_processor.schema_alignment_results.summary.total_changes,
                                    columns_renamed=combined_results_processor.schema_alignment_results.summary.columns_renamed,
                                    columns_added=combined_results_processor.schema_alignment_results.summary.columns_added,
                                    columns_removed=combined_results_processor.schema_alignment_results.summary.columns_removed,
                                    rows_original=combined_results_processor.schema_alignment_results.summary.rows_original,
                                    rows_aligned=combined_results_processor.schema_alignment_results.summary.rows_aligned,
                                )

                                # Create API SchemaAlignmentResults
                                api_schema_alignment_results = SchemaAlignmentResults(
                                    schema_alignment_results=api_change_details, summary=api_summary
                                )

                                api_combined_results.schema_alignment_results = api_schema_alignment_results
                                logger.info(
                                    f"Job {job_id} completed, loaded schema alignment data with {len(api_change_details)} changes"
                                )

                            # Extract and convert ChangeTrackingResults
                            if combined_results_processor.change_tracking:
                                from metadata_harmonization_processor.models.change_tracking import (
                                    ChangeTrackingResults,
                                    ChangeObject,
                                    ChangesSummary,
                                )

                                # Convert change objects from processor model to API model
                                api_change_objects = [
                                    ChangeObject(
                                        change_id=change.change_id,
                                        change_type=change.change_type,
                                        source_type=change.source_type,
                                        component=change.component,
                                        row=change.row,
                                        column=change.column,
                                        old_value=change.old_value,
                                        new_value=change.new_value,
                                        timestamp=change.timestamp,
                                        source_version=change.source_version,
                                        target_version=change.target_version,
                                        confidence_score=change.confidence_score,
                                        user_context=change.user_context,
                                    )
                                    for change in combined_results_processor.change_tracking.changes
                                ]

                                # Convert summary from processor model to API model
                                api_changes_summary = ChangesSummary(
                                    total_changes=combined_results_processor.change_tracking.summary.total_changes,
                                    adds=combined_results_processor.change_tracking.summary.adds,
                                    removes=combined_results_processor.change_tracking.summary.removes,
                                    renames=combined_results_processor.change_tracking.summary.renames,
                                    system_changes=combined_results_processor.change_tracking.summary.system_changes,
                                    user_changes=combined_results_processor.change_tracking.summary.user_changes,
                                )

                                # Create API ChangeTrackingResults
                                api_change_tracking = ChangeTrackingResults(
                                    changes=api_change_objects,
                                    summary=api_changes_summary,
                                    comparison_metadata=combined_results_processor.change_tracking.comparison_metadata,
                                )

                                api_combined_results.change_tracking = api_change_tracking
                                logger.info(
                                    f"Job {job_id} completed, loaded change tracking data with {len(api_change_objects)} changes"
                                )

                            response_data["latest_results"] = api_combined_results
                        else:
                            logger.warning(
                                f"Job {job_id} completed but could not load combined results from {job_results}"
                            )

                    except Exception as e:
                        logger.error(f"Error loading combined results for job {job_id}: {e}")
                        # Don't fail the entire request if we can't load results
                        pass
                    finally:
                        # Clean up the processor instance
                        if "processor" in locals():
                            await self.processor_manager.cleanup_processor(job_id)

            logger.info(f"Retrieved status for job {job_id}: {job.status}")
            return ValidationStatusResponse(**response_data)

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Error retrieving validation job status {metadata_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error while retrieving validation job status")
