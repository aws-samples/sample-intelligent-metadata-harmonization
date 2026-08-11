# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
MetadataWorker for background metadata processing.

This module provides the MetadataWorker class that orchestrates background
metadata validation jobs using the WorkerService and ProcessorManager.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

from metadata_harmonization_api.workers.worker_service import WorkerService
from metadata_harmonization_api.services.processor_manager import ProcessorManager
from metadata_harmonization_processor.models.combined_results import CombinedResults

logger = logging.getLogger(__name__)


class MetadataWorker:
    """
    Worker for background metadata processing tasks.

    This class orchestrates the metadata processing workflow using the
    WorkerService and ProcessorManager, handling file management and
    error scenarios for background task execution.
    """

    def __init__(self, processor_manager: ProcessorManager):
        """
        Initialize MetadataWorker with ProcessorManager.

        Args:
            processor_manager: ProcessorManager instance for processor lifecycle management
        """
        self.processor_manager = processor_manager
        self.worker_service = WorkerService(processor_manager)

    async def process_validation_job(
        self, job_id: str, csv_content: bytes, core_schema_id: str, program_schema_id: str, version: int = 1
    ) -> Optional[CombinedResults]:
        """
        Process a metadata validation job in the background.

        This method handles the complete workflow for background metadata processing:
        1. Creates temporary file from CSV content
        2. Delegates to WorkerService for actual processing
        3. Handles cleanup and error scenarios

        Args:
            job_id: Unique job identifier
            csv_content: CSV file content as bytes
            core_schema_id: Core schema identifier for validation
            program_schema_id: Program schema identifier for validation
            version: Job version number (default: 1)

        Returns:
            CombinedResults if processing succeeds, None if it fails
        """
        temp_file_path: Optional[Path] = None

        try:
            logger.info(f"Starting background processing for job {job_id}, version {version}")

            # Create temporary file for CSV content
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as temp_file:
                temp_file.write(csv_content)
                temp_file_path = Path(temp_file.name)

            logger.debug(f"Created temporary CSV file: {temp_file_path}")

            # Process metadata validation using WorkerService
            validation_results = await self.worker_service.process_metadata_validation(
                job_id=job_id,
                csv_file_path=str(temp_file_path),
                core_schema_id=core_schema_id,
                program_schema_id=program_schema_id,
                version=version,
            )

            logger.info(f"Successfully completed background processing for job {job_id}")
            return validation_results

        except Exception as e:
            logger.error(f"Background processing failed for job {job_id}: {e}")
            # Error handling is delegated to the processor's DataSaver
            # which will update job status to "failed" automatically
            return None

        finally:
            # Clean up temporary file
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up temporary file {temp_file_path}: {cleanup_error}")


def create_background_task_function(
    processor_manager: ProcessorManager,
    job_id: str,
    csv_content: bytes,
    core_schema_id: str,
    program_schema_id: str,
    version: int = 1,
):
    """
    Create a background task function for FastAPI BackgroundTasks.

    This function creates a synchronous wrapper around the async metadata processing
    that can be used with FastAPI's BackgroundTasks.add_task().

    Args:
        processor_manager: ProcessorManager instance
        job_id: Unique job identifier
        csv_content: CSV file content as bytes
        core_schema_id: Core schema identifier
        program_schema_id: Program schema identifier
        version: Job version number (default: 1)

    Returns:
        Synchronous function that can be used with BackgroundTasks
    """

    def background_task():
        """Synchronous wrapper for async metadata processing."""
        try:
            # Create new event loop for background task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Use shared dependency injection to get MetadataWorker
            from metadata_harmonization_api.utils.shared_dependencies import get_metadata_worker

            worker = get_metadata_worker(processor_manager)

            result = loop.run_until_complete(
                worker.process_validation_job(
                    job_id=job_id,
                    csv_content=csv_content,
                    core_schema_id=core_schema_id,
                    program_schema_id=program_schema_id,
                    version=version,
                )
            )

            if result:
                logger.info(f"Background task completed successfully for job {job_id}")
            else:
                logger.error(f"Background task failed for job {job_id}")

        except Exception as e:
            logger.error(f"Background task execution error for job {job_id}: {e}")

        finally:
            # Clean up event loop
            try:
                loop.close()
            except Exception as loop_error:
                logger.warning(f"Error closing event loop for job {job_id}: {loop_error}")

    return background_task
