# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""MCP validation tools using shared dependency injection."""

from typing import Dict, Any
from uuid import uuid4

from fastmcp import FastMCP
from loguru import logger

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.utils.shared_dependencies import (
    get_schema_collector,
    get_processor_manager,
    get_metadata_worker,
)


def setup_validation_tools(mcp: FastMCP, processor_config: ProcessorConfig) -> None:
    """
    Set up MCP validation tools using shared dependency injection.

    Args:
        mcp: FastMCP server instance
        processor_config: ProcessorConfig instance for shared component initialization
    """

    @mcp.tool(description="Submit metadata for validation and get complete results")
    async def submit_metadata_validation(
        metadata_content: str, core_schema_id: str, program_schema_id: str, format: str = "csv"
    ) -> Dict[str, Any]:
        """
        Submit metadata for validation and wait for complete results.

        Args:
            metadata_content: CSV or JSON content to validate
            core_schema_id: Core schema identifier for validation
            program_schema_id: Program schema identifier for validation
            format: Format of metadata: 'csv' or 'json' (default: 'csv')

        Returns:
            Dictionary containing validation results or error information
        """
        job_id = str(uuid4())
        content_length = len(metadata_content) if metadata_content else 0

        logger.info(
            f"Starting metadata validation - job_id: {job_id}, schema: {core_schema_id}/{program_schema_id}, format: {format}, content_length: {content_length}"
        )

        # Validate input parameters
        if not metadata_content or not metadata_content.strip():
            logger.error("Validation failed: metadata_content cannot be empty")
            return {
                "success": False,
                "job_id": job_id,
                "error": "metadata_content cannot be empty",
                "error_code": "INVALID_INPUT",
            }

        if not core_schema_id or not core_schema_id.strip():
            logger.error("Validation failed: core_schema_id cannot be empty")
            return {
                "success": False,
                "job_id": job_id,
                "error": "core_schema_id cannot be empty",
                "error_code": "INVALID_INPUT",
            }

        if not program_schema_id or not program_schema_id.strip():
            logger.error("Validation failed: program_schema_id cannot be empty")
            return {
                "success": False,
                "job_id": job_id,
                "error": "program_schema_id cannot be empty",
                "error_code": "INVALID_INPUT",
            }

        if format.lower() not in ["csv", "json"]:
            logger.error(f"Validation failed: unsupported format '{format}'")
            return {
                "success": False,
                "job_id": job_id,
                "error": f"Unsupported format '{format}'. Supported formats: csv, json",
                "error_code": "INVALID_FORMAT",
            }

        # Validate schema combination using shared SchemaCollector
        logger.info(f"Validating schema combination: {core_schema_id}/{program_schema_id}")

        try:
            # Get shared SchemaCollector via dependency injection
            schema_collector = get_schema_collector(processor_config)

            # Use await instead of creating new event loop (we're already in async context)
            await schema_collector.get_schema(program_schema_id, core_schema_id)
            logger.info("Schema validation successful")

        except Exception as schema_error:
            logger.error(f"Schema validation failed: {str(schema_error)}")
            return {
                "success": False,
                "job_id": job_id,
                "error": f"Invalid schema combination: core_schema_id='{core_schema_id}', program_schema_id='{program_schema_id}'. Error: {str(schema_error)}",
                "error_code": "INVALID_SCHEMA",
            }

        # Process validation using shared MetadataWorker
        logger.info("Starting metadata validation processing")

        processor_manager = get_processor_manager(processor_config)
        worker = get_metadata_worker(processor_manager)

        # Convert content to bytes for processing
        content_bytes = metadata_content.encode("utf-8")

        # Use await instead of creating new event loop (we're already in async context)
        validation_results = await worker.process_validation_job(
            job_id=job_id,
            csv_content=content_bytes,
            core_schema_id=core_schema_id,
            program_schema_id=program_schema_id,
            version=1,
        )

        if validation_results:
            logger.info(f"Validation processing completed successfully - job_id: {job_id}")

            # Convert validation results to dictionary format
            results_dict = validation_results.dict() if hasattr(validation_results, "dict") else str(validation_results)

            return {
                "success": True,
                "job_id": job_id,
                "status": "completed",
                "validation_results": results_dict,
                "format": format,
            }
        else:
            logger.error(f"Validation processing failed - no results returned - job_id: {job_id}")
            return {
                "success": False,
                "job_id": job_id,
                "error": "Validation processing failed - no results returned",
                "error_code": "PROCESSING_FAILED",
            }

    logger.info("MCP validation tools registered successfully")
