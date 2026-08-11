# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for single results.json file retrieval approach."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import MetadataValidationHandler
from metadata_harmonization_api.api.v1.models.metadata import (
    ValidationStatusResponse,
    CombinedResults,
    SchemaAlignmentResults,
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
    """Mock processor with enhanced data saver using single results.json approach."""
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
                row=1,
                column="patient_id",
                current_value="",
                valid_options=None,
                recommended_value="Non-empty string",
                error_type=ValidationErrorType.REQUIRED_VALUE,
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
def sample_processor_schema_alignment_results():
    """Sample processor schema alignment results for testing."""
    return ProcessorSchemaAlignmentResults(
        schema_alignment_results=[
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="patient_id",
                reason="Required field missing from original data",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="patient_name",
                new_column="full_name",
                reason="Column name standardization",
                row_count_affected=2,
            ),
        ],
        summary=SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="patient_name,age\nJohn Doe,30\nJane Smith,25",
            aligned_data_csv="patient_id,full_name,age\n,John Doe,30\n,Jane Smith,25",
            total_changes=2,
            columns_renamed=1,
            columns_added=1,
            columns_removed=0,
            rows_original=2,
            rows_aligned=2,
        ),
    )


@pytest.fixture
def sample_processor_combined_results(sample_validation_results, sample_processor_schema_alignment_results):
    """Sample processor combined results for testing."""
    return ProcessorCombinedResults(
        validation_results=sample_validation_results, schema_alignment_results=sample_processor_schema_alignment_results
    )


@pytest.mark.asyncio
async def test_get_validation_status_single_file_combined_results(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
    sample_processor_combined_results,
):
    """Test getting validation status with combined results from single results.json file."""
    # Setup mocks for single file approach
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.return_value = sample_processor_combined_results

    # Create handler
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Mock request
    request = MagicMock()
    request.state.user_id = "test_user"

    # Call method
    response = await handler.get_validation_status(metadata_id=sample_job.job_id, request=request)

    # Verify response structure
    assert isinstance(response, ValidationStatusResponse)
    assert str(response.job_id) == sample_job.job_id
    assert response.status == "completed"
    assert response.latest_results is not None

    # Verify combined results structure
    combined_results = response.latest_results
    assert isinstance(combined_results, CombinedResults)
    assert combined_results.validation_results is not None
    assert combined_results.schema_alignment_results is not None

    # Verify validation results
    validation_results = combined_results.validation_results
    assert len(validation_results.validation_results) == 1
    assert validation_results.validation_results[0].column == "patient_id"
    assert validation_results.validation_results[0].error_type == ValidationErrorType.REQUIRED_VALUE

    # Verify schema alignment results conversion from processor to API model
    schema_results = combined_results.schema_alignment_results
    assert isinstance(schema_results, SchemaAlignmentResults)
    assert len(schema_results.schema_alignment_results) == 2

    # Verify change details conversion
    change_details = schema_results.schema_alignment_results
    assert change_details[0].change_type == "add"
    assert change_details[0].new_column == "patient_id"
    assert change_details[0].row_count_affected == 2

    assert change_details[1].change_type == "rename"
    assert change_details[1].original_column == "patient_name"
    assert change_details[1].new_column == "full_name"

    # Verify summary conversion
    summary = schema_results.summary
    assert summary.job_id == "test-job"
    assert summary.total_changes == 2
    assert summary.columns_renamed == 1
    assert summary.columns_added == 1
    assert summary.columns_removed == 0
    assert summary.rows_original == 2
    assert summary.rows_aligned == 2

    # Verify processor cleanup was called
    mock_processor_manager.cleanup_processor.assert_called_once_with(sample_job.job_id)


@pytest.mark.asyncio
async def test_get_validation_status_single_file_validation_only(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
    sample_validation_results,
):
    """Test getting validation status with validation results only from single results.json file."""
    # Setup mocks - combined results with validation only
    combined_results = ProcessorCombinedResults(
        validation_results=sample_validation_results, schema_alignment_results=None
    )

    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.return_value = combined_results

    # Create handler
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Mock request
    request = MagicMock()
    request.state.user_id = "test_user"

    # Call method
    response = await handler.get_validation_status(metadata_id=sample_job.job_id, request=request)

    # Verify response structure
    assert isinstance(response, ValidationStatusResponse)
    assert response.latest_results is not None

    # Verify combined results structure
    api_combined_results = response.latest_results
    assert isinstance(api_combined_results, CombinedResults)
    assert api_combined_results.validation_results is not None
    assert api_combined_results.schema_alignment_results is None

    # Verify validation results
    validation_results = api_combined_results.validation_results
    assert len(validation_results.validation_results) == 1
    assert validation_results.validation_results[0].column == "patient_id"
    assert validation_results.validation_results[0].error_type == ValidationErrorType.REQUIRED_VALUE


@pytest.mark.asyncio
async def test_get_validation_status_single_file_schema_alignment_only(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
    sample_processor_schema_alignment_results,
):
    """Test getting validation status with schema alignment results only from single results.json file."""
    # Setup mocks - combined results with schema alignment only
    combined_results = ProcessorCombinedResults(
        validation_results=None, schema_alignment_results=sample_processor_schema_alignment_results
    )

    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.return_value = combined_results

    # Create handler
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Mock request
    request = MagicMock()
    request.state.user_id = "test_user"

    # Call method
    response = await handler.get_validation_status(metadata_id=sample_job.job_id, request=request)

    # Verify response structure
    assert isinstance(response, ValidationStatusResponse)
    assert response.latest_results is not None

    # Verify combined results structure
    api_combined_results = response.latest_results
    assert isinstance(api_combined_results, CombinedResults)
    assert api_combined_results.validation_results is None
    assert api_combined_results.schema_alignment_results is not None

    # Verify schema alignment results conversion
    schema_results = api_combined_results.schema_alignment_results
    assert isinstance(schema_results, SchemaAlignmentResults)
    assert len(schema_results.schema_alignment_results) == 2
    assert schema_results.summary.total_changes == 2


@pytest.mark.asyncio
async def test_get_validation_status_single_file_no_results(
    mock_schema_collector, mock_job_status_saver, mock_processor_manager, mock_processor, sample_job
):
    """Test getting validation status when single results.json file returns None."""
    # Setup mocks - no results from single file
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.return_value = None

    # Create handler
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Mock request
    request = MagicMock()
    request.state.user_id = "test_user"

    # Call method
    response = await handler.get_validation_status(metadata_id=sample_job.job_id, request=request)

    # Verify response structure
    assert isinstance(response, ValidationStatusResponse)
    assert response.latest_results is None


@pytest.mark.asyncio
async def test_get_validation_status_single_file_empty_combined_results(
    mock_schema_collector, mock_job_status_saver, mock_processor_manager, mock_processor, sample_job
):
    """Test getting validation status when single results.json file returns empty CombinedResults."""
    # Setup mocks - empty combined results
    empty_combined_results = ProcessorCombinedResults(validation_results=None, schema_alignment_results=None)

    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.return_value = empty_combined_results

    # Create handler
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Mock request
    request = MagicMock()
    request.state.user_id = "test_user"

    # Call method
    response = await handler.get_validation_status(metadata_id=sample_job.job_id, request=request)

    # Verify response structure
    assert isinstance(response, ValidationStatusResponse)
    assert response.latest_results is not None

    # Verify combined results structure (should be empty but not None)
    api_combined_results = response.latest_results
    assert isinstance(api_combined_results, CombinedResults)
    assert api_combined_results.validation_results is None
    assert api_combined_results.schema_alignment_results is None


@pytest.mark.asyncio
async def test_get_validation_status_single_file_error_handling(
    mock_schema_collector, mock_job_status_saver, mock_processor_manager, mock_processor, sample_job
):
    """Test error handling when single results.json file loading fails."""
    # Setup mocks with error
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.side_effect = Exception("Failed to load results.json from S3")

    # Create handler
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Mock request
    request = MagicMock()
    request.state.user_id = "test_user"

    # Call method - should not raise exception
    response = await handler.get_validation_status(metadata_id=sample_job.job_id, request=request)

    # Verify response structure (should still return job info without results)
    assert isinstance(response, ValidationStatusResponse)
    assert response.status == "completed"
    assert response.latest_results is None

    # Verify processor cleanup was still called
    mock_processor_manager.cleanup_processor.assert_called_once_with(sample_job.job_id)


@pytest.mark.asyncio
async def test_get_validation_status_single_file_data_saver_interface(
    mock_schema_collector,
    mock_job_status_saver,
    mock_processor_manager,
    mock_processor,
    sample_job,
    sample_processor_combined_results,
):
    """Test that the handler correctly uses the single file data saver interface."""
    # Setup mocks
    mock_job_status_saver.get_job.return_value = sample_job
    mock_processor_manager.get_processor.return_value = mock_processor
    mock_processor.data_saver.get_results.return_value = sample_processor_combined_results

    # Create handler
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Mock request
    request = MagicMock()
    request.state.user_id = "test_user"

    # Call method
    await handler.get_validation_status(metadata_id=sample_job.job_id, request=request)

    # Verify that data_saver.get_results was called with JobResults (single parameter)
    expected_job_results = sample_job.results["1"]
    mock_processor.data_saver.get_results.assert_called_once_with(expected_job_results)

    # Verify processor lifecycle management
    mock_processor_manager.get_processor.assert_called_once_with(sample_job.job_id)
    mock_processor_manager.cleanup_processor.assert_called_once_with(sample_job.job_id)
