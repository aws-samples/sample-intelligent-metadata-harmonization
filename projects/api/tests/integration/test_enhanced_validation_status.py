# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for enhanced validation status endpoint with combined result retrieval."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import MetadataValidationHandler
from metadata_harmonization_api.api.v1.models.metadata import (
    ValidationStatusResponse,
    CombinedResults as APICombinedResults,
    SchemaAlignmentResults as APISchemaAlignmentResults,
)
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentResults as ProcessorSchemaAlignmentResults,
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResultsSummary,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults as ProcessorCombinedResults
from metadata_harmonization_processor.models.job import MetadataUploadJob, JobResults


@pytest.fixture
def mock_schema_collector():
    """Mock schema collector for testing."""
    return AsyncMock()


@pytest.fixture
def mock_job_status_saver():
    """Mock job status saver for testing."""
    return AsyncMock()


@pytest.fixture
def mock_processor_manager():
    """Mock processor manager for testing."""
    return AsyncMock()


@pytest.fixture
def mock_processor():
    """Mock processor with enhanced data saver."""
    processor = AsyncMock()
    processor.data_saver = AsyncMock()
    return processor


@pytest.fixture
def sample_job():
    """Sample job data for testing."""
    job_id = str(uuid4())
    return MetadataUploadJob(
        job_id=job_id,
        user_id="test_user",
        core_schema_id="cyclospora_core",
        program_schema_id="cyclospora_program",
        status="completed",
        created_at=datetime.now(timezone.utc).isoformat(),
        completed_at=datetime.now(timezone.utc).isoformat(),
        current_version=1,
        results={"1": JobResults(storage_type="s3", location="validation-results/test-job/v1/", bucket="test-bucket")},
    )


@pytest.fixture
def sample_validation_results():
    """Sample validation results for testing."""
    return ValidationResults(
        validation_results=[
            ValidationErrorDetail(
                row=2,
                column="patient_id",
                current_value="",
                error_type=ValidationErrorType.REQUIRED_VALUE,
                recommended_value="Non-empty string",
            )
        ],
        summary=ValidationResultsSummary(
            total_rows=10,
            total_errors=1,
            error_types={ValidationErrorType.REQUIRED_VALUE: 1},
            columns_validated=1,
        ),
    )


@pytest.fixture
def sample_schema_alignment_results():
    """Sample processor schema alignment results for testing."""
    return ProcessorSchemaAlignmentResults(
        schema_alignment_results=[
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="patient_id",
                reason="Required field missing from original data",
                row_count_affected=2,
            )
        ],
        summary=SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            original_data_csv="patient_name,age\nJohn Doe,30\nJane Smith,25",
            aligned_data_csv="patient_id,patient_name,age\n,John Doe,30\n,Jane Smith,25",
            total_changes=1,
            columns_renamed=0,
            columns_added=1,
            columns_removed=0,
            rows_original=2,
            rows_aligned=2,
        ),
    )


@pytest.mark.asyncio
async def test_get_validation_status_with_combined_results(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
    sample_validation_results,
    sample_schema_alignment_results,
):
    """Test getting validation status with combined validation and schema alignment results."""
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor

    combined = ProcessorCombinedResults(
        validation_results=sample_validation_results,
        schema_alignment_results=sample_schema_alignment_results,
    )
    mock_processor.data_saver.get_results.return_value = combined

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(
        metadata_id=sample_job.job_id,
        request=request,
    )

    assert isinstance(response, ValidationStatusResponse)
    assert str(response.job_id) == sample_job.job_id
    assert response.status == "completed"
    assert response.latest_results is not None

    combined_results = response.latest_results
    assert isinstance(combined_results, APICombinedResults)
    assert combined_results.validation_results is not None
    assert combined_results.schema_alignment_results is not None

    validation_results = combined_results.validation_results
    assert len(validation_results.validation_results) == 1
    assert validation_results.validation_results[0].column == "patient_id"
    assert validation_results.validation_results[0].error_type == ValidationErrorType.REQUIRED_VALUE

    schema_results = combined_results.schema_alignment_results
    assert isinstance(schema_results, APISchemaAlignmentResults)
    assert schema_results.summary.original_data_csv == "patient_name,age\nJohn Doe,30\nJane Smith,25"
    assert schema_results.summary.aligned_data_csv == "patient_id,patient_name,age\n,John Doe,30\n,Jane Smith,25"
    assert schema_results.summary.columns_added == 1

    mock_processor_manager.cleanup_processor.assert_called_once_with(sample_job.job_id)


@pytest.mark.asyncio
async def test_get_validation_status_validation_only(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
    sample_validation_results,
):
    """Test getting validation status with validation results only (no schema alignment)."""
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor

    combined = ProcessorCombinedResults(
        validation_results=sample_validation_results,
        schema_alignment_results=None,
    )
    mock_processor.data_saver.get_results.return_value = combined

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(
        metadata_id=sample_job.job_id,
        request=request,
    )

    assert isinstance(response, ValidationStatusResponse)
    assert response.latest_results is not None

    combined_results = response.latest_results
    assert isinstance(combined_results, APICombinedResults)
    assert combined_results.validation_results is not None
    assert combined_results.schema_alignment_results is None

    assert len(combined_results.validation_results.validation_results) == 1


@pytest.mark.asyncio
async def test_get_validation_status_schema_alignment_only(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
    sample_schema_alignment_results,
):
    """Test getting validation status with schema alignment results only (no validation errors)."""
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor

    combined = ProcessorCombinedResults(
        validation_results=None,
        schema_alignment_results=sample_schema_alignment_results,
    )
    mock_processor.data_saver.get_results.return_value = combined

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(
        metadata_id=sample_job.job_id,
        request=request,
    )

    assert isinstance(response, ValidationStatusResponse)
    assert response.latest_results is not None

    combined_results = response.latest_results
    assert isinstance(combined_results, APICombinedResults)
    assert combined_results.validation_results is None
    assert combined_results.schema_alignment_results is not None

    schema_results = combined_results.schema_alignment_results
    assert isinstance(schema_results, APISchemaAlignmentResults)
    assert schema_results.summary.columns_added == 1


@pytest.mark.asyncio
async def test_get_validation_status_no_results(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
):
    """Test getting validation status when no results are available."""
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.return_value = None

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(
        metadata_id=sample_job.job_id,
        request=request,
    )

    assert isinstance(response, ValidationStatusResponse)
    assert response.latest_results is None


@pytest.mark.asyncio
async def test_get_validation_status_pending_job(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    sample_job,
):
    """Test getting validation status for a pending job (no results yet)."""
    sample_job.status = "pending"
    sample_job.completed_at = None
    sample_job.results = {}

    mock_job_status_saver.get_job.return_value = sample_job

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(
        metadata_id=sample_job.job_id,
        request=request,
    )

    assert isinstance(response, ValidationStatusResponse)
    assert response.status == "pending"
    assert response.completed_at is None
    assert response.latest_results is None

    mock_processor_manager.get_processor.assert_not_called()


@pytest.mark.asyncio
async def test_get_validation_status_error_handling(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
):
    """Test error handling when data saver fails."""
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.side_effect = Exception("S3 connection failed")

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(
        metadata_id=sample_job.job_id,
        request=request,
    )

    assert isinstance(response, ValidationStatusResponse)
    assert response.status == "completed"
    assert response.latest_results is None

    mock_processor_manager.cleanup_processor.assert_called_once_with(sample_job.job_id)


@pytest.mark.asyncio
async def test_get_validation_status_cross_tenant_returns_404(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    sample_job,
):
    """A caller who is not the job's owner must get a 404, not the job's data."""
    sample_job.user_id = "owner_user"
    mock_job_status_saver.get_job.return_value = sample_job

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "different_user"

    with pytest.raises(HTTPException) as exc_info:
        await handler.get_validation_status(
            metadata_id=sample_job.job_id,
            request=request,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_validation_job_cross_tenant_returns_404(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    sample_job,
):
    """A caller who is not the job's owner must not be able to update it."""
    sample_job.user_id = "owner_user"
    mock_job_status_saver.get_job.return_value = sample_job

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    request = MagicMock()
    request.state.user_id = "different_user"

    file = MagicMock()
    file.filename = "update.csv"
    file.content_type = "text/csv"
    file.read = AsyncMock(return_value=b"col1,col2\nval1,val2\n")
    file.file = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await handler.update_validation_job(
            metadata_id=sample_job.job_id,
            background_tasks=MagicMock(),
            request=request,
            file=file,
        )

    assert exc_info.value.status_code == 404
