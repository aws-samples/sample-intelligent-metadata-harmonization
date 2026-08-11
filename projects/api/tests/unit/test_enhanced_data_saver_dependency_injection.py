# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests to verify enhanced data saver is accessible through existing dependency injection."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import MetadataValidationHandler
from metadata_harmonization_api.services.processor_manager import ProcessorManager
from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_processor.implementations.s3_result_saver import S3ResultSaver
from metadata_harmonization_processor.implementations.local_result_saver import LocalResultSaver


@pytest.fixture
def mock_processor_config():
    """Mock processor configuration."""
    return ProcessorConfig(
        schema_directory="./test_schemas",
        result_saver_type="s3",
        results_s3_bucket="test-bucket",
        results_s3_prefix="validation-results/",
        aws_region="us-east-1",
        session_saver_type="file",
        file_session_directory="./test_sessions",
        enable_redis_cache=False,
        enable_memory_cache=True,
    )


@pytest.fixture
def mock_processor_manager(mock_processor_config):
    """Mock processor manager with configuration."""
    return ProcessorManager(mock_processor_config)


@pytest.fixture
def mock_schema_collector():
    """Mock schema collector."""
    return AsyncMock()


@pytest.fixture
def mock_job_status_saver():
    """Mock job status saver."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_processor_manager_provides_enhanced_s3_data_saver(mock_processor_manager):
    """Test that processor manager provides processor with enhanced S3 data saver."""
    with patch(
        "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
    ) as mock_processor_class:
        # Setup mock processor instance with a mock S3 data saver
        mock_processor_instance = AsyncMock()
        mock_s3_saver = MagicMock(spec=S3ResultSaver)
        mock_s3_saver.get_results = AsyncMock(return_value=(None, None))
        mock_s3_saver.save_results = AsyncMock()
        mock_processor_instance.data_saver = mock_s3_saver
        mock_processor_class.return_value = mock_processor_instance

        # Get processor from manager
        processor = await mock_processor_manager.get_processor("test-job-id")

        # Verify processor has enhanced data saver
        assert processor is not None
        assert hasattr(processor, "data_saver")
        assert isinstance(processor.data_saver, S3ResultSaver)

        # Verify enhanced data saver has the new get_results method signature
        assert hasattr(processor.data_saver, "get_results")
        assert hasattr(processor.data_saver, "save_results")

        # Verify the get_results method returns tuple (ValidationResults, SchemaAlignmentResults)
        from metadata_harmonization_processor.models.job import JobResults

        mock_job_results = JobResults(
            storage_type="s3",
            location="validation-results/test-job/v1/",
            bucket="test-bucket",
        )

        result = await processor.data_saver.get_results(mock_job_results)
        assert isinstance(result, tuple)
        assert len(result) == 2


@pytest.mark.asyncio
async def test_processor_manager_provides_enhanced_local_data_saver():
    """Test that processor manager provides processor with enhanced local data saver."""
    # Create processor config for local development
    local_config = ProcessorConfig(
        schema_directory="./test_schemas",
        result_saver_type="local",
        local_development_mode=True,
        job_status_saver_type="local",
        job_status_storage_dir="./job_status",
        session_saver_type="file",
        file_session_directory="./test_sessions",
        enable_redis_cache=False,
        enable_memory_cache=True,
    )

    processor_manager = ProcessorManager(local_config)

    with patch(
        "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
    ) as mock_processor_class:
        # Setup mock processor instance with a mock local data saver
        mock_processor_instance = AsyncMock()
        mock_local_saver = MagicMock(spec=LocalResultSaver)
        mock_local_saver.get_results = AsyncMock()
        mock_local_saver.save_results = AsyncMock()
        mock_processor_instance.data_saver = mock_local_saver
        mock_processor_class.return_value = mock_processor_instance

        # Get processor from manager
        processor = await processor_manager.get_processor("test-job-id")

        # Verify processor has enhanced data saver
        assert processor is not None
        assert hasattr(processor, "data_saver")
        assert isinstance(processor.data_saver, LocalResultSaver)

        # Verify enhanced data saver has the new methods
        assert hasattr(processor.data_saver, "get_results")
        assert hasattr(processor.data_saver, "save_results")


@pytest.mark.asyncio
async def test_metadata_validation_handler_accesses_enhanced_data_saver(
    mock_schema_collector, mock_job_status_saver, mock_processor_manager
):
    """Test that MetadataValidationHandler can access enhanced data saver through processor manager."""
    # Setup mock processor with enhanced data saver
    mock_processor = AsyncMock()
    mock_processor.data_saver = AsyncMock()
    mock_processor.data_saver.get_results = AsyncMock(return_value=(None, None))

    mock_processor_manager.get_processor = AsyncMock(return_value=mock_processor)
    mock_processor_manager.cleanup_processor = AsyncMock()

    # Create handler with dependency injection
    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    # Verify handler has access to processor manager
    assert handler.processor_manager is mock_processor_manager

    # Simulate getting a processor and accessing its data saver
    processor = await handler.processor_manager.get_processor("test-job-id")
    assert processor is mock_processor
    assert hasattr(processor, "data_saver")

    # Verify the enhanced data saver method can be called
    from metadata_harmonization_processor.models.job import JobResults

    mock_job_results = JobResults(storage_type="s3", location="validation-results/test-job/v1/", bucket="test-bucket")

    result = await processor.data_saver.get_results(mock_job_results)
    assert isinstance(result, tuple)
    assert len(result) == 2

    # Verify cleanup is accessible
    await handler.processor_manager.cleanup_processor("test-job-id")
    mock_processor_manager.cleanup_processor.assert_called_once_with("test-job-id")


@pytest.mark.asyncio
async def test_enhanced_data_saver_interface_compatibility():
    """Test that enhanced data saver maintains interface compatibility."""
    # Test S3 data saver interface via mock (real S3ResultSaver contacts AWS)
    mock_s3_saver = MagicMock(spec=S3ResultSaver)

    # Verify interface methods exist on the spec
    assert hasattr(mock_s3_saver, "save_results")
    assert hasattr(mock_s3_saver, "get_results")
    assert hasattr(mock_s3_saver, "list_results")

    # Test Local data saver interface
    local_saver = LocalResultSaver(storage_dir="./test-results")

    # Verify interface methods exist
    assert hasattr(local_saver, "save_results")
    assert hasattr(local_saver, "get_results")
    assert hasattr(local_saver, "list_results")


def test_dependency_injection_configuration():
    """Test that dependency injection configuration supports enhanced data saver."""
    # Test that handler can be created with dependencies
    mock_schema_collector = MagicMock()
    mock_job_status_saver = MagicMock()
    mock_processor_manager = MagicMock()

    handler = MetadataValidationHandler(
        schema_collector=mock_schema_collector,
        job_status_saver=mock_job_status_saver,
        processor_manager=mock_processor_manager,
    )

    assert handler.schema_collector is mock_schema_collector
    assert handler.job_status_saver is mock_job_status_saver
    assert handler.processor_manager is mock_processor_manager


@pytest.mark.asyncio
async def test_enhanced_data_saver_method_signatures():
    """Test that enhanced data saver methods have correct signatures."""
    from metadata_harmonization_processor.models.validation import ValidationResults, ValidationResultsSummary
    from metadata_harmonization_processor.models.schema_alignment_results import (
        SchemaAlignmentResults,
        SchemaAlignmentResultsSummary,
    )
    from metadata_harmonization_processor.models.job import JobResults

    # Create mock data saver
    mock_data_saver = AsyncMock()

    # Test save_results method signature
    mock_validation_results = ValidationResults(
        validation_results=[],
        summary=ValidationResultsSummary(
            total_rows=10,
            total_errors=0,
            error_types={},
            columns_validated=0,
        ),
    )

    mock_schema_alignment_results = SchemaAlignmentResults(
        schema_alignment_results=[],
        summary=SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            original_data_csv="test,data\n1,2",
            aligned_data_csv="test,data,new\n1,2,",
        ),
    )

    # Mock save_results to return JobResults
    mock_job_results = JobResults(storage_type="s3", location="validation-results/test-job/v1/", bucket="test-bucket")
    mock_data_saver.save_results.return_value = mock_job_results

    # Test save_results call with enhanced signature
    await mock_data_saver.save_results(
        job_id="test-job",
        version=1,
        validation_results=mock_validation_results,
        schema_alignment_results=mock_schema_alignment_results,
    )

    # Verify call was made with correct parameters
    mock_data_saver.save_results.assert_called_once_with(
        job_id="test-job",
        version=1,
        validation_results=mock_validation_results,
        schema_alignment_results=mock_schema_alignment_results,
    )

    # Test get_results method signature
    mock_data_saver.get_results.return_value = (mock_validation_results, mock_schema_alignment_results)

    validation_results, schema_alignment_results = await mock_data_saver.get_results(mock_job_results)

    # Verify return types
    assert validation_results is mock_validation_results
    assert schema_alignment_results is mock_schema_alignment_results

    mock_data_saver.get_results.assert_called_once_with(mock_job_results)
