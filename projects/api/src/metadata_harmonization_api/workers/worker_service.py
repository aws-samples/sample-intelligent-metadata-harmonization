# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
WorkerService for metadata validation processing.

This module provides the WorkerService class that integrates with the
MetadataHarmonizationProcessor to perform actual metadata validation
using the complete processor pipeline including AI predictions.
"""

import logging
from typing import Optional

from metadata_harmonization_api.services.processor_manager import ProcessorManager
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor import MetadataHarmonizationProcessor

logger = logging.getLogger(__name__)


class WorkerService:
    """
    Service for processing metadata validation jobs using MetadataHarmonizationProcessor.

    This service replaces mocked validation logic with actual processor integration,
    using the processor's complete pipeline including AI predictions and the
    processor's DataSaver for unified result and job status management.
    """

    def __init__(self, processor_manager: ProcessorManager):
        """
        Initialize WorkerService with ProcessorManager.

        Args:
            processor_manager: ProcessorManager instance for managing processor lifecycle
        """
        self.processor_manager = processor_manager

    async def process_metadata_validation(
        self, job_id: str, csv_file_path: str, core_schema_id: str, program_schema_id: str, version: int
    ) -> CombinedResults:
        """
        Process metadata validation using MetadataHarmonizationProcessor.

        This method replaces mocked validation logic with actual processor integration.
        It uses the processor's complete pipeline including schema alignment, validation,
        and AI-powered predictions, and leverages the processor's DataSaver for unified
        result and job status management.

        Args:
            job_id: Unique job identifier (passed to processor for consistent tracking)
            csv_file_path: Path to the CSV file to process
            core_schema_id: Core schema identifier for validation
            program_schema_id: Program schema identifier for validation
            version: Job version number

        Returns:
            CombinedResults from the processor containing validation results, schema alignment, and change tracking

        Raises:
            Exception: If CSV file cannot be read or processor fails

        Requirements: 6.1, 6.4, 6.5
        """
        processor: Optional[MetadataHarmonizationProcessor] = None
        processor_retrieved = False

        try:
            logger.info(f"Starting metadata validation processing for job {job_id}, version {version}")

            # Load CSV data into DataFrame with schema-aware dtype mapping
            # This prevents issues like "FALSE"/"TRUE" being converted to Python bools
            try:
                metadata_df = await self.processor_manager.load_metadata_csv(
                    csv_file_path, program_schema_id, core_schema_id
                )
                logger.debug(
                    f"Loaded CSV file with {len(metadata_df)} rows and {len(metadata_df.columns)} columns using schema-aware loading"
                )
            except Exception as e:
                logger.error(f"Failed to read CSV file {csv_file_path}: {e}")
                raise Exception(f"Failed to read CSV file: {e}")

            # Get processor instance from manager
            processor = await self.processor_manager.get_processor(job_id)
            processor_retrieved = True
            logger.info(f"Retrieved processor instance for session {job_id}")

            # Process metadata using the complete processor pipeline
            # This includes schema alignment, validation, and AI-powered predictions
            logger.info(
                f"Processing metadata with job_id={job_id}, core_schema_id={core_schema_id}, program_schema_id={program_schema_id}"
            )

            validation_results = await processor.process(
                metadata_df=metadata_df,
                program_id=program_schema_id,
                core_id=core_schema_id,
                job_id=job_id,  # Pass the job_id to the processor
            )

            logger.info(f"Metadata processing completed for job {job_id}")

            # Log validation results if available
            if validation_results.has_validation_results():
                logger.debug(
                    f"Validation results: {validation_results.validation_results.summary.total_errors} errors found "
                    f"in {validation_results.validation_results.summary.total_rows} rows"
                )

            # The processor's DataSaver automatically handles:
            # - Job status updates (pending -> processing -> completed)
            # - Result storage (S3 or local depending on configuration)
            # - Job metadata updates with result locations

            return validation_results

        except Exception as e:
            logger.error(f"Error processing metadata validation for job {job_id}: {e}")

            # The processor's DataSaver will handle error status updates
            # when the processor encounters errors during processing

            raise e

        finally:
            # Always clean up processor resources if processor was retrieved
            if processor_retrieved:
                try:
                    await self.processor_manager.cleanup_processor(job_id)
                    logger.debug(f"Cleaned up processor resources for job {job_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up processor for job {job_id}: {cleanup_error}")
