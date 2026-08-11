# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Metadata validation endpoints."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile

from metadata_harmonization_api.api.v1.models.metadata import (
    SchemaInfo,
    ValidationJobResponse,
    ValidationStatusResponse,
)
from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import MetadataValidationHandler
from metadata_harmonization_api.api.v1.handlers.schema_handler import SchemaHandler
from metadata_harmonization_api.utils.shared_dependencies import (
    get_schema_collector,
    get_processor_manager,
    get_job_status_saver,
)
from metadata_harmonization_processor.interfaces.job_status_saver import JobStatusSaver
from metadata_harmonization_processor.interfaces.schema_collector import SchemaCollector


logger = logging.getLogger(__name__)

router = APIRouter()


def get_api_config(request: Request):
    """Dependency to get API configuration from application state."""
    return request.app.state.api_config


def get_processor_config(request: Request):
    """Dependency to get processor configuration from application state."""
    return request.app.state.processor_config


def get_shared_schema_collector(request: Request) -> SchemaCollector:
    """Dependency to get shared schema collector instance."""
    processor_config = get_processor_config(request)
    return get_schema_collector(processor_config)


def get_shared_processor_manager(request: Request):
    """Dependency to get shared ProcessorManager instance."""
    processor_config = get_processor_config(request)
    return get_processor_manager(processor_config)


def get_shared_job_status_saver(request: Request) -> JobStatusSaver:
    """Dependency to get shared job status saver instance."""
    processor_config = get_processor_config(request)
    return get_job_status_saver(processor_config)


def get_metadata_validation_handler(
    request: Request,
    schema_collector: SchemaCollector = Depends(get_shared_schema_collector),
    job_status_saver: JobStatusSaver = Depends(get_shared_job_status_saver),
    processor_manager=Depends(get_shared_processor_manager),
) -> MetadataValidationHandler:
    """Dependency to get MetadataValidationHandler with shared dependencies."""
    # Pass the loaded configuration, not the module-level default, so upload limits
    # reflect config.yaml and any environment overrides.
    return MetadataValidationHandler(
        schema_collector=schema_collector,
        job_status_saver=job_status_saver,
        processor_manager=processor_manager,
        metadata_config=get_api_config(request).metadata,
    )


def get_schema_handler(
    schema_collector: SchemaCollector = Depends(get_shared_schema_collector),
) -> SchemaHandler:
    """Dependency to get SchemaHandler with shared dependencies."""
    return SchemaHandler(schema_collector=schema_collector)


@router.post("/validate", response_model=ValidationJobResponse, status_code=201)
async def create_validation_job(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(..., description="CSV file to validate"),
    core_schema_id: str = Form(..., description="Core schema identifier for validation"),
    program_schema_id: str = Form(..., description="Program schema identifier for validation"),
    handler: MetadataValidationHandler = Depends(get_metadata_validation_handler),
) -> ValidationJobResponse:
    """
    Create a new metadata validation job.

    Uploads a CSV file for metadata validation against specified core and program schemas.
    Returns a job ID for tracking the validation process.

    Requirements: 1.1, 1.2, 1.3, 1.4
    """
    # Force debug logging to stdout to ensure we see entry
    logger.info(f"[ENDPOINT] create_validation_job called - core: {core_schema_id}, program: {program_schema_id}")
    logger.info(f"[ENDPOINT] File: {file.filename if file else 'None'}")

    try:
        logger.info("[ENDPOINT] Calling handler.create_validation_job")
        result = await handler.create_validation_job(
            background_tasks=background_tasks,
            request=request,
            file=file,
            core_schema_id=core_schema_id,
            program_schema_id=program_schema_id,
        )
        logger.info(f"[ENDPOINT] Handler returned successfully: {result}")
        return result
    except Exception as e:
        logger.info(f"[ENDPOINT ERROR] Exception in create_validation_job: {type(e).__name__}: {str(e)}")
        logger.info("[ENDPOINT ERROR] Raising exception to be handled by global handler")
        raise


@router.post("/validate/{metadata_id}", response_model=ValidationJobResponse)
async def update_validation_job(
    metadata_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(..., description="Updated CSV file to validate"),
    handler: MetadataValidationHandler = Depends(get_metadata_validation_handler),
) -> ValidationJobResponse:
    """
    Update an existing metadata validation job with a new CSV file.

    Uses the same schema IDs as the original job but processes the updated CSV file.
    Increments the job version and maintains the same job ID.

    Requirements: 2.1, 2.2, 2.3, 2.4
    """
    return await handler.update_validation_job(
        metadata_id=metadata_id,
        background_tasks=background_tasks,
        request=request,
        file=file,
    )


@router.get("/validate/{metadata_id}", response_model=ValidationStatusResponse)
async def get_validation_status(
    metadata_id: UUID,
    request: Request,
    handler: MetadataValidationHandler = Depends(get_metadata_validation_handler),
) -> ValidationStatusResponse:
    """
    Get the status and results of a metadata validation job.

    Returns job details including current status, timestamps, and validation results
    when the job is completed.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    return await handler.get_validation_status(
        metadata_id=metadata_id,
        request=request,
    )


@router.get("/schema", response_model=List[SchemaInfo])
async def get_available_schemas(
    request: Request,
    handler: SchemaHandler = Depends(get_schema_handler),
) -> List[SchemaInfo]:
    """
    Get all available metadata schemas for validation.

    Returns a list of core schemas with their associated program schemas,
    providing sufficient information for UI dropdown selection.

    Requirements: 3.1, 3.2, 3.3, 3.4
    """
    return await handler.get_available_schemas(request=request)
