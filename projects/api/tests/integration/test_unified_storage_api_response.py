# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""API integration tests for enhanced response model with unified data structure."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import MetadataValidationHandler
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
def mock_handler_deps():
    """Create mock dependencies for MetadataValidationHandler."""
    mock_schema_collector = AsyncMock()
    mock_job_status_saver = AsyncMock()
    mock_processor_manager = AsyncMock()
    mock_processor = AsyncMock()
    mock_processor.data_saver = AsyncMock()
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor_manager.cleanup_processor = AsyncMock()
    return {
        "schema_collector": mock_schema_collector,
        "job_status_saver": mock_job_status_saver,
        "processor_manager": mock_processor_manager,
        "processor": mock_processor,
    }


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
                valid_options=None,
                recommended_value="PAT001",
            ),
            ValidationErrorDetail(
                row=3,
                column="birth_date",
                current_value="invalid-date",
                error_type=ValidationErrorType.INVALID_PATTERN,
                valid_options=None,
                recommended_value="1990-01-01",
            ),
        ],
        summary=ValidationResultsSummary(
            total_rows=10,
            total_errors=2,
            error_types={
                ValidationErrorType.REQUIRED_VALUE: 1,
                ValidationErrorType.INVALID_PATTERN: 1,
            },
            columns_validated=2,
        ),
    )


@pytest.fixture
def sample_schema_alignment_results():
    """Sample schema alignment results for testing."""
    return ProcessorSchemaAlignmentResults(
        schema_alignment_results=[
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="patient_id",
                reason="Required field missing",
                row_count_affected=3,
            )
        ],
        summary=SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            original_data_csv="patient_name,age,gender\nJohn Doe,30,M\nJane Smith,25,F\nBob Johnson,45,M",
            aligned_data_csv="patient_id,patient_name,age,gender\n,John Doe,30,M\n,Jane Smith,25,F\n,Bob Johnson,45,M",
            total_changes=1,
            columns_renamed=0,
            columns_added=1,
            columns_removed=0,
            rows_original=3,
            rows_aligned=3,
        ),
    )


def _create_completed_job(job_id: str) -> MetadataUploadJob:
    """Helper to create a completed job."""
    return MetadataUploadJob(
        job_id=job_id,
        user_id="test_user",
        core_schema_id="cyclospora_core",
        program_schema_id="cyclospora_program",
        status="completed",
        created_at=datetime.now(timezone.utc).isoformat(),
        completed_at=datetime.now(timezone.utc).isoformat(),
        current_version=1,
        results={
            "1": JobResults(
                storage_type="s3",
                location=f"validation-results/{job_id}/v1/",
                bucket="test-bucket",
            )
        },
    )


@pytest.mark.asyncio
async def test_api_response_with_combined_results(
    mock_handler_deps, sample_validation_results, sample_schema_alignment_results
):
    """Test API response structure with combined validation and schema alignment results."""
    deps = mock_handler_deps
    job_id = str(uuid4())
    completed_job = _create_completed_job(job_id)

    deps["job_status_saver"].get_job.return_value = completed_job
    combined = ProcessorCombinedResults(
        validation_results=sample_validation_results,
        schema_alignment_results=sample_schema_alignment_results,
    )
    deps["processor"].data_saver.get_results.return_value = combined

    handler = MetadataValidationHandler(
        schema_collector=deps["schema_collector"],
        job_status_saver=deps["job_status_saver"],
        processor_manager=deps["processor_manager"],
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(metadata_id=job_id, request=request)

    response_dict = response.model_dump(by_alias=True)

    assert str(response_dict["jobId"]) == job_id
    assert response_dict["status"] == "completed"
    assert response_dict["latestResults"] is not None

    latest_results = response_dict["latestResults"]
    assert "validationResults" in latest_results
    assert "schemaAlignmentResults" in latest_results

    validation_results = latest_results["validationResults"]
    assert validation_results is not None
    assert "validationResults" in validation_results
    assert "summary" in validation_results

    validation_errors = validation_results["validationResults"]
    assert len(validation_errors) == 2
    assert validation_errors[0]["column"] == "patient_id"
    assert validation_errors[0]["errorType"] == "REQUIRED_VALUE"
    assert validation_errors[1]["column"] == "birth_date"
    assert validation_errors[1]["errorType"] == "INVALID_PATTERN"

    summary = validation_results["summary"]
    assert summary["totalRows"] == 10
    assert summary["totalErrors"] == 2
    assert "errorTypes" in summary

    schema_alignment = latest_results["schemaAlignmentResults"]
    assert schema_alignment is not None
    assert "summary" in schema_alignment
    assert "originalDataCsv" in schema_alignment["summary"]
    assert "alignedDataCsv" in schema_alignment["summary"]

    assert "John Doe,30,M" in schema_alignment["summary"]["originalDataCsv"]
    assert "patient_id,patient_name,age,gender" in schema_alignment["summary"]["alignedDataCsv"]


@pytest.mark.asyncio
async def test_api_response_validation_results_only(mock_handler_deps, sample_validation_results):
    """Test API response when only validation results are available."""
    deps = mock_handler_deps
    job_id = str(uuid4())
    completed_job = _create_completed_job(job_id)

    deps["job_status_saver"].get_job.return_value = completed_job
    combined = ProcessorCombinedResults(
        validation_results=sample_validation_results,
        schema_alignment_results=None,
    )
    deps["processor"].data_saver.get_results.return_value = combined

    handler = MetadataValidationHandler(
        schema_collector=deps["schema_collector"],
        job_status_saver=deps["job_status_saver"],
        processor_manager=deps["processor_manager"],
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(metadata_id=job_id, request=request)

    response_dict = response.model_dump(by_alias=True)
    latest_results = response_dict["latestResults"]
    assert latest_results["validationResults"] is not None
    assert latest_results["schemaAlignmentResults"] is None

    validation_results = latest_results["validationResults"]
    assert len(validation_results["validationResults"]) == 2
    assert validation_results["summary"]["totalErrors"] == 2


@pytest.mark.asyncio
async def test_api_response_schema_alignment_only(mock_handler_deps, sample_schema_alignment_results):
    """Test API response when only schema alignment results are available."""
    deps = mock_handler_deps
    job_id = str(uuid4())
    completed_job = _create_completed_job(job_id)

    deps["job_status_saver"].get_job.return_value = completed_job
    combined = ProcessorCombinedResults(
        validation_results=None,
        schema_alignment_results=sample_schema_alignment_results,
    )
    deps["processor"].data_saver.get_results.return_value = combined

    handler = MetadataValidationHandler(
        schema_collector=deps["schema_collector"],
        job_status_saver=deps["job_status_saver"],
        processor_manager=deps["processor_manager"],
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(metadata_id=job_id, request=request)

    response_dict = response.model_dump(by_alias=True)
    latest_results = response_dict["latestResults"]
    assert latest_results["validationResults"] is None
    assert latest_results["schemaAlignmentResults"] is not None


@pytest.mark.asyncio
async def test_api_response_no_results(mock_handler_deps):
    """Test API response when no results are available."""
    deps = mock_handler_deps
    job_id = str(uuid4())
    completed_job = _create_completed_job(job_id)

    deps["job_status_saver"].get_job.return_value = completed_job
    deps["processor"].data_saver.get_results.return_value = None

    handler = MetadataValidationHandler(
        schema_collector=deps["schema_collector"],
        job_status_saver=deps["job_status_saver"],
        processor_manager=deps["processor_manager"],
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(metadata_id=job_id, request=request)

    response_dict = response.model_dump(by_alias=True)
    assert response_dict["latestResults"] is None


@pytest.mark.asyncio
async def test_api_response_pending_job(mock_handler_deps):
    """Test API response for pending job (no results yet)."""
    deps = mock_handler_deps
    job_id = str(uuid4())
    pending_job = MetadataUploadJob(
        job_id=job_id,
        user_id="test_user",
        core_schema_id="cyclospora_core",
        program_schema_id="cyclospora_program",
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        completed_at=None,
        current_version=1,
        results={},
    )

    deps["job_status_saver"].get_job.return_value = pending_job

    handler = MetadataValidationHandler(
        schema_collector=deps["schema_collector"],
        job_status_saver=deps["job_status_saver"],
        processor_manager=deps["processor_manager"],
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(metadata_id=job_id, request=request)

    response_dict = response.model_dump(by_alias=True)
    assert str(response_dict["jobId"]) == job_id
    assert response_dict["status"] == "pending"
    assert response_dict["completedAt"] is None
    assert response_dict["latestResults"] is None

    deps["processor_manager"].get_processor.assert_not_called()


@pytest.mark.asyncio
async def test_api_response_error_handling(mock_handler_deps):
    """Test API response error handling when data retrieval fails."""
    deps = mock_handler_deps
    job_id = str(uuid4())
    completed_job = _create_completed_job(job_id)

    deps["job_status_saver"].get_job.return_value = completed_job
    deps["processor"].data_saver.get_results.side_effect = Exception("S3 connection failed")

    handler = MetadataValidationHandler(
        schema_collector=deps["schema_collector"],
        job_status_saver=deps["job_status_saver"],
        processor_manager=deps["processor_manager"],
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(metadata_id=job_id, request=request)

    response_dict = response.model_dump(by_alias=True)
    assert str(response_dict["jobId"]) == job_id
    assert response_dict["status"] == "completed"
    assert response_dict["latestResults"] is None

    deps["processor_manager"].cleanup_processor.assert_called_once()


@pytest.mark.asyncio
async def test_api_response_backward_compatibility(
    mock_handler_deps, sample_validation_results, sample_schema_alignment_results
):
    """Test that API response maintains backward compatibility with field names."""
    deps = mock_handler_deps
    job_id = str(uuid4())
    completed_job = _create_completed_job(job_id)

    deps["job_status_saver"].get_job.return_value = completed_job
    combined = ProcessorCombinedResults(
        validation_results=sample_validation_results,
        schema_alignment_results=sample_schema_alignment_results,
    )
    deps["processor"].data_saver.get_results.return_value = combined

    handler = MetadataValidationHandler(
        schema_collector=deps["schema_collector"],
        job_status_saver=deps["job_status_saver"],
        processor_manager=deps["processor_manager"],
    )

    request = MagicMock()
    request.state.user_id = "test_user"
    response = await handler.get_validation_status(metadata_id=job_id, request=request)

    response_dict = response.model_dump(by_alias=True)

    assert "jobId" in response_dict
    assert "userId" in response_dict
    assert "coreSchemaId" in response_dict
    assert "programSchemaId" in response_dict
    assert "createdAt" in response_dict
    assert "completedAt" in response_dict
    assert "currentVersion" in response_dict
    assert "latestResults" in response_dict

    latest_results = response_dict["latestResults"]
    assert "validationResults" in latest_results
    assert "schemaAlignmentResults" in latest_results

    schema_alignment = latest_results["schemaAlignmentResults"]
    assert "summary" in schema_alignment
    assert "originalDataCsv" in schema_alignment["summary"]
    assert "alignedDataCsv" in schema_alignment["summary"]
