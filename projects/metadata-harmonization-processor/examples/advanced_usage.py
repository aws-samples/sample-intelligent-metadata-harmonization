#!/usr/bin/env python3
# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Advanced Usage Example for MetadataHarmonizationProcessor

This example demonstrates advanced features including:
- Custom configuration overrides
- Error handling and recovery
- Progress monitoring
- Batch processing
- Resource management
"""

import asyncio
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any

from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.config import load_processor_settings
from metadata_harmonization_processor.models.validation import ValidationResults


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AdvancedMetadataProcessor:
    """Advanced wrapper for MetadataHarmonizationProcessor with additional features."""

    def __init__(self, config_path: str, config_overrides: Dict[str, Any] = None):
        """Initialize with configuration and overrides."""
        self.config_path = config_path
        self.config_overrides = config_overrides or {}
        self.processor = None

    async def initialize(self):
        """Initialize the processor with configuration-driven components."""
        logger.info("Initializing MetadataHarmonizationProcessor with configuration-driven approach...")

        # Load configuration with overrides
        config = load_processor_settings(config_path=Path(self.config_path), override=self.config_overrides)

        logger.info("Configuration loaded:")
        logger.info(f"  - Job Status Saver: {config.job_status_saver_type}")
        logger.info(f"  - Result Saver: {config.result_saver_type}")
        logger.info(f"  - Schema Directory: {config.schema_directory}")

        # Initialize processor with configuration-driven approach
        # All components (JobStatusSaver, ResultSaver, SchemaCollector) created automatically
        session_id = f"advanced-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
        self.processor = MetadataHarmonizationProcessor(config=config, session_id=session_id)

        # Access the result saver for demonstration purposes
        self.result_saver = self.processor.data_saver.result_saver

        logger.info("Processor initialized successfully with configuration-driven components")

    async def process_batch(
        self, dataframes: List[pd.DataFrame], program_id: str, core_id: str
    ) -> List[ValidationResults]:
        """Process multiple DataFrames in sequence."""
        results = []

        for i, df in enumerate(dataframes):
            logger.info(f"Processing batch {i+1}/{len(dataframes)} ({len(df)} rows)")

            try:
                # Reset state for each batch
                self.processor.reset_state()

                # Process the DataFrame
                result = await self.processor.process(df, program_id=program_id, core_id=core_id)
                results.append(result)

                # Log progress
                logger.info(f"Batch {i+1} completed: {result.summary.total_errors} errors found")

            except Exception as e:
                logger.error(f"Error processing batch {i+1}: {e}")
                # Continue with next batch
                continue

        return results

    async def process_with_monitoring(
        self, metadata_df: pd.DataFrame, program_id: str, core_id: str
    ) -> ValidationResults:
        """Process with detailed progress monitoring."""
        logger.info(f"Starting processing of {len(metadata_df)} rows")

        try:
            # Start processing
            result = await self.processor.process(metadata_df, program_id=program_id, core_id=core_id)

            # Get final state
            state = self.processor.get_current_state()
            if state:
                duration = state.get_processing_duration()
                logger.info(f"Processing completed in {duration:.2f} seconds")
                logger.info(f"Final stage: {state.current_stage}")

            return result

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            # Get current state for debugging
            state = self.processor.get_current_state()
            if state:
                logger.error(f"Failed at stage: {state.current_stage}")
            raise

    async def demonstrate_result_storage(self, validation_results: ValidationResults, job_id: str) -> None:
        """Demonstrate S3ResultSaver functionality."""
        logger.info("=== S3 Result Storage Demo ===")

        try:
            # Save results to S3
            job_results = await self.result_saver.save_results(
                job_id=job_id,
                version=1,
                results=validation_results,
                metadata={
                    "processing_time": 123.45,
                    "rows_processed": validation_results.summary.total_rows,
                    "error_count": validation_results.summary.total_errors,
                    "processor_version": "0.2.0",
                },
            )

            logger.info("Results saved to S3:")
            logger.info(f"  Storage type: {job_results.storage_type}")
            logger.info(f"  Bucket: {job_results.bucket}")
            logger.info(f"  Location: {job_results.location}")

            # Retrieve results from S3
            retrieved_results = await self.result_saver.get_results(job_results)
            if retrieved_results:
                logger.info("Successfully retrieved results from S3:")
                logger.info(f"  Total errors: {retrieved_results.summary.total_errors}")
                logger.info(f"  Error types: {retrieved_results.summary.error_types}")

            # List all results for this job
            all_results = await self.result_saver.list_results(job_id)
            logger.info(f"Found {len(all_results)} result versions for job {job_id}")

        except Exception as e:
            logger.error(f"S3 result storage demo failed: {e}")
            logger.info("Note: This requires valid AWS credentials and S3 bucket access")

    async def cleanup(self):
        """Clean up processor resources."""
        if self.processor:
            await self.processor.cleanup()
            logger.info("Processor resources cleaned up")


async def demonstrate_advanced_features():
    """Demonstrate advanced processor features."""

    # Configuration overrides for production-like setup with S3ResultSaver
    config_overrides = {
        "enable_redis_cache": True,
        "redis_endpoint": "localhost",  # For local Redis instance
        "redis_port": 6379,
        "cosine_similarity_threshold": 0.8,
        "max_retries": 5,
        "timeout_seconds": 600,
        # S3 Result Storage Configuration
        "result_saver_type": "s3",
        "results_s3_bucket": "my-metadata-validation-results",
        "results_s3_prefix": "advanced-demo/results/",
        # DynamoDB Job Status Configuration
        "job_status_saver_type": "dynamodb",
        "job_status_table_name": "metadata-processor-jobs-prod",
        # AWS Configuration
        "aws_region": "us-east-1",
    }

    # Initialize advanced processor with S3 configuration
    processor = AdvancedMetadataProcessor(
        config_path="examples/config-s3.yaml",  # Use S3-specific configuration
        config_overrides=config_overrides,
    )

    try:
        await processor.initialize()

        # Create sample datasets for batch processing
        datasets = []
        for i in range(3):
            sample_data = {
                "patient_id": [f"P{j:03d}" for j in range(i * 10, (i + 1) * 10)],
                "age": [str(25 + j) if j % 3 != 0 else "invalid" for j in range(10)],
                "gender": ["Male" if j % 2 == 0 else "Female" for j in range(10)],
                "status": ["active" if j % 4 != 0 else "" for j in range(10)],
                "email": [f"user{j}@example.com" if j % 5 != 0 else "invalid-email" for j in range(10)],
            }
            datasets.append(pd.DataFrame(sample_data))

        logger.info(f"Created {len(datasets)} datasets for batch processing")

        # Demonstrate batch processing
        logger.info("=== Batch Processing Demo ===")
        batch_results = await processor.process_batch(
            datasets, program_id="example-program-uuid", core_id="example-core-uuid"
        )

        # Analyze batch results
        total_errors = sum(result.summary.total_errors for result in batch_results)
        total_rows = sum(result.summary.total_rows for result in batch_results)

        logger.info("Batch processing completed:")
        logger.info(f"  Total batches: {len(batch_results)}")
        logger.info(f"  Total rows: {total_rows}")
        logger.info(f"  Total errors: {total_errors}")
        logger.info(f"  Error rate: {total_errors/total_rows*100:.1f}%")

        # Demonstrate monitoring
        logger.info("\n=== Monitoring Demo ===")
        combined_df = pd.concat(datasets, ignore_index=True)
        monitored_result = await processor.process_with_monitoring(
            combined_df, program_id="example-program-uuid", core_id="example-core-uuid"
        )

        # Display detailed results
        logger.info("Monitored processing results:")
        logger.info(f"  Rows processed: {monitored_result.summary.total_rows}")
        logger.info(f"  Errors found: {monitored_result.summary.total_errors}")
        logger.info(f"  Error types: {monitored_result.summary.error_types}")

        # Show sample recommendations
        recommendations = [error for error in monitored_result.validation_results if error.recommended_value]

        if recommendations:
            logger.info(f"\nSample AI recommendations ({len(recommendations)} total):")
            for error in recommendations[:5]:  # Show first 5
                logger.info(f"  Row {error.row}, Column '{error.column}':")
                logger.info(f"    '{error.current_value}' → '{error.recommended_value}'")

        # Demonstrate S3 result storage
        state = processor.processor.get_current_state()
        if state:
            await processor.demonstrate_result_storage(monitored_result, state.job_id)

    except Exception as e:
        logger.error(f"Advanced processing failed: {e}")
        raise

    finally:
        await processor.cleanup()


async def demonstrate_error_handling():
    """Demonstrate error handling and recovery scenarios."""
    logger.info("\n=== Error Handling Demo ===")

    # Test with invalid configuration
    try:
        invalid_processor = AdvancedMetadataProcessor(
            config_path="nonexistent-config.yaml", config_overrides={"invalid_setting": "invalid_value"}
        )
        await invalid_processor.initialize()
    except Exception as e:
        logger.info(f"Expected configuration error handled: {type(e).__name__}")

    # Test with invalid schema IDs
    processor = AdvancedMetadataProcessor("examples/config-basic.yaml")
    try:
        await processor.initialize()

        # Try processing with invalid schema IDs
        sample_df = pd.DataFrame({"col1": ["value1", "value2"]})

        await processor.processor.process(sample_df, program_id="invalid-program", core_id="invalid-core")
        logger.info("Processing with invalid schema IDs completed (graceful handling)")

    except Exception as e:
        logger.info(f"Schema error handled gracefully: {type(e).__name__}")
    finally:
        await processor.cleanup()


if __name__ == "__main__":

    async def main():
        """Run all advanced examples."""
        await demonstrate_advanced_features()
        await demonstrate_error_handling()
        logger.info("\nAdvanced usage demonstration completed!")

    asyncio.run(main())
