# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for WorkerService."""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

from metadata_harmonization_api.workers.worker_service import WorkerService
from metadata_harmonization_api.services.processor_manager import ProcessorManager
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor import MetadataHarmonizationProcessor
from tests.utils.test_data import TestDataFactory
from tests.utils.helpers import create_async_mock


class TestWorkerService:
    """Test cases for WorkerService."""

    @pytest.fixture
    def mock_job_status_saver(self):
        """Create a mock JobStatusSaver."""
        return create_async_mock()

    @pytest.fixture
    def mock_processor_manager(self):
        """Create a mock ProcessorManager."""
        mock_manager = AsyncMock(spec=ProcessorManager)
        mock_processor = AsyncMock(spec=MetadataHarmonizationProcessor)
        mock_manager.get_processor.return_value = mock_processor
        mock_manager.cleanup_processor.return_value = None
        # Default load_metadata_csv returns an empty DataFrame
        mock_manager.load_metadata_csv.return_value = pd.DataFrame()
        return mock_manager

    @pytest.fixture
    def mock_metadata_processor(self):
        """Create a mock MetadataHarmonizationProcessor."""
        mock_processor = AsyncMock(spec=MetadataHarmonizationProcessor)
        mock_processor.process.return_value = CombinedResults(
            validation_results=ValidationResults(
                validation_results=[],
                summary=ValidationResultsSummary(
                    total_rows=100,
                    total_errors=0,
                    error_types={},
                    columns_validated=0,
                ),
            )
        )
        return mock_processor

    @pytest.fixture
    def worker_service(self, mock_processor_manager):
        """Create a WorkerService instance with mocked dependencies."""
        return WorkerService(processor_manager=mock_processor_manager)

    @pytest.fixture
    def sample_job_data(self):
        """Create sample job data for testing."""
        return TestDataFactory.create_upload_job(
            job_id="test_job_123",
            user_id="test_user",
            status="pending",
            core_schema_id="test_core_v1",
            program_schema_id="test_program_v1",
        )

    @pytest.fixture
    def sample_csv_content(self):
        """Create sample CSV content for testing."""
        return TestDataFactory.create_csv_content(include_errors=True)

    @pytest.fixture
    def sample_validation_results(self):
        """Create sample validation results for testing."""
        return TestDataFactory.create_validation_results()

    @pytest.mark.asyncio
    async def test_process_metadata_success(
        self,
        worker_service,
        mock_processor_manager,
        mock_metadata_processor,
        sample_job_data,
        sample_csv_content,
        sample_validation_results,
    ):
        """Test successful metadata processing using MetadataHarmonizationProcessor."""
        job_id = sample_job_data["job_id"]
        csv_file_path = "test_file.csv"
        core_schema_id = sample_job_data["core_schema_id"]
        program_schema_id = sample_job_data["program_schema_id"]
        version = 1

        # Setup processor manager mock
        mock_processor_manager.get_processor.return_value = mock_metadata_processor

        # Mock load_metadata_csv to return a DataFrame
        mock_df = pd.DataFrame(
            {"participant_id": ["ABC123", "DEF456"], "age": [25, 30], "city": ["New York", "Los Angeles"]}
        )
        mock_processor_manager.load_metadata_csv.return_value = mock_df

        # Mock processor.process() to return CombinedResults wrapping validation results
        mock_metadata_processor.process.return_value = CombinedResults(
            validation_results=ValidationResults(
                validation_results=sample_validation_results["validation_results"],
                summary=ValidationResultsSummary(**sample_validation_results["summary"]),
            )
        )

        # Execute the method
        result = await worker_service.process_metadata_validation(
            job_id, csv_file_path, core_schema_id, program_schema_id, version
        )

        # Verify CSV was loaded via processor manager
        mock_processor_manager.load_metadata_csv.assert_called_once_with(
            csv_file_path, program_schema_id, core_schema_id
        )

        # Verify processor was called correctly
        mock_processor_manager.get_processor.assert_called_once_with(job_id)
        mock_metadata_processor.process.assert_called_once()

        # Verify the call arguments to processor.process()
        call_args = mock_metadata_processor.process.call_args
        assert call_args[1]["program_id"] == program_schema_id
        assert call_args[1]["core_id"] == core_schema_id
        assert isinstance(call_args[1]["metadata_df"], pd.DataFrame)

        # Verify processor cleanup was called
        mock_processor_manager.cleanup_processor.assert_called_once_with(job_id)

        # Verify result is returned
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_metadata_csv_read_error(self, worker_service, mock_processor_manager):
        """Test processing when CSV file cannot be read."""
        job_id = "test_job_123"
        csv_file_path = "nonexistent_file.csv"

        # Mock load_metadata_csv to raise error
        mock_processor_manager.load_metadata_csv.side_effect = FileNotFoundError("File not found")

        with pytest.raises(Exception, match="Failed to read CSV file"):
            await worker_service.process_metadata_validation(job_id, csv_file_path, "core_v1", "program_v1", 1)

        # Verify processor was never retrieved (so no cleanup needed)
        mock_processor_manager.get_processor.assert_not_called()
        mock_processor_manager.cleanup_processor.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_metadata_processor_error(
        self, worker_service, mock_processor_manager, mock_metadata_processor
    ):
        """Test processing when processor fails."""
        job_id = "test_job_123"
        csv_file_path = "test_file.csv"

        # Setup processor manager mock
        mock_processor_manager.get_processor.return_value = mock_metadata_processor
        mock_processor_manager.load_metadata_csv.return_value = pd.DataFrame({"test": ["data"]})

        # Mock processor error
        mock_metadata_processor.process.side_effect = Exception("Processor validation failed")

        with pytest.raises(Exception, match="Processor validation failed"):
            await worker_service.process_metadata_validation(job_id, csv_file_path, "core_v1", "program_v1", 1)

        # Verify processor cleanup was still called
        mock_processor_manager.cleanup_processor.assert_called_once_with(job_id)

    @pytest.mark.asyncio
    async def test_process_metadata_with_validation_errors(
        self, worker_service, mock_processor_manager, mock_metadata_processor, sample_validation_results
    ):
        """Test processing that returns validation errors."""
        job_id = "test_job_123"
        csv_file_path = "test_file.csv"

        # Setup processor manager mock
        mock_processor_manager.get_processor.return_value = mock_metadata_processor
        mock_processor_manager.load_metadata_csv.return_value = pd.DataFrame({"participant_id": ["", "ABC123"]})

        # Mock processor to return CombinedResults with validation errors
        validation_results_with_errors = CombinedResults(
            validation_results=ValidationResults(
                validation_results=[
                    ValidationErrorDetail(
                        row=1,
                        column="participant_id",
                        current_value="",
                        error_type=ValidationErrorType.REQUIRED_VALUE,
                    )
                ],
                summary=ValidationResultsSummary(
                    total_rows=100,
                    total_errors=1,
                    error_types={ValidationErrorType.REQUIRED_VALUE: 1},
                    columns_validated=1,
                ),
            )
        )
        mock_metadata_processor.process.return_value = validation_results_with_errors

        result = await worker_service.process_metadata_validation(job_id, csv_file_path, "core_v1", "program_v1", 1)

        # Verify result contains validation errors
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_metadata_dataframe_conversion(
        self, worker_service, mock_processor_manager, mock_metadata_processor
    ):
        """Test that CSV data is properly converted to DataFrame for processor."""
        job_id = "test_job_123"
        csv_file_path = "test_file.csv"

        # Setup processor manager mock
        mock_processor_manager.get_processor.return_value = mock_metadata_processor

        # Mock load_metadata_csv to return a specific DataFrame
        csv_data = {
            "participant_id": ["ABC123", "DEF456", "GHI789"],
            "age": [25, 30, 35],
            "city": ["New York", "Los Angeles", "Chicago"],
        }
        mock_df = pd.DataFrame(csv_data)
        mock_processor_manager.load_metadata_csv.return_value = mock_df

        await worker_service.process_metadata_validation(job_id, csv_file_path, "core_v1", "program_v1", 1)

        # Verify processor was called with DataFrame
        mock_metadata_processor.process.assert_called_once()
        call_args = mock_metadata_processor.process.call_args

        # Check that metadata_df is a DataFrame with expected data
        passed_df = call_args[1]["metadata_df"]
        assert isinstance(passed_df, pd.DataFrame)
        assert list(passed_df.columns) == ["participant_id", "age", "city"]
        assert len(passed_df) == 3
        assert passed_df.iloc[0]["participant_id"] == "ABC123"


class TestProcessorManagerIntegration:
    """Test cases for ProcessorManager lifecycle and session management."""

    @pytest.fixture
    def mock_processor_config(self):
        """Create a mock processor configuration."""
        from metadata_harmonization_processor.config import ProcessorConfig

        return ProcessorConfig(
            schema_directory="./test_schemas",
            local_development_mode=True,
            job_status_saver_type="local",
            result_saver_type="local",
            session_saver_type="file",  # Use file session type for local development
            file_session_directory="./test_sessions",  # Required for file session type
            s3_bucket="test-bucket",  # Provide s3_bucket even though not used in local mode
            enable_redis_cache=False,  # Disable Redis cache for tests
            enable_memory_cache=True,  # Use memory cache instead
        )

    @pytest.fixture
    def processor_manager(self, mock_processor_config):
        """Create a ProcessorManager instance with mocked config."""
        return ProcessorManager(mock_processor_config)

    @pytest.mark.asyncio
    async def test_processor_manager_get_processor(self, processor_manager):
        """Test getting a processor instance from manager."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock()
            mock_processor_class.return_value = mock_processor_instance

            processor = await processor_manager.get_processor(session_id)

            # Verify processor was created and cached
            assert processor == mock_processor_instance
            mock_processor_class.assert_called_once_with(
                config=processor_manager.processor_config, session_id=session_id
            )

    @pytest.mark.asyncio
    async def test_processor_manager_reuse_processor(self, processor_manager):
        """Test that processor instances are reused for same session."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock()
            mock_processor_class.return_value = mock_processor_instance

            # Get processor twice
            processor1 = await processor_manager.get_processor(session_id)
            processor2 = await processor_manager.get_processor(session_id)

            # Should be the same instance
            assert processor1 == processor2
            # Should only create once
            mock_processor_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_processor_manager_cleanup_processor(self, processor_manager):
        """Test cleaning up a processor instance."""
        session_id = "test_session_123"

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock()
            mock_processor_instance.cleanup = AsyncMock()
            mock_processor_class.return_value = mock_processor_instance

            # Get processor then clean it up
            await processor_manager.get_processor(session_id)
            await processor_manager.cleanup_processor(session_id)

            # Verify cleanup was called if method exists
            if hasattr(mock_processor_instance, "cleanup"):
                mock_processor_instance.cleanup.assert_called_once()

            # Verify processor was removed from cache
            assert processor_manager.get_active_session_count() == 0

    @pytest.mark.asyncio
    async def test_processor_manager_cleanup_all_processors(self, processor_manager):
        """Test cleaning up all processor instances."""
        session_ids = ["session_1", "session_2", "session_3"]

        with patch(
            "metadata_harmonization_api.services.processor_manager.MetadataHarmonizationProcessor"
        ) as mock_processor_class:
            mock_processor_instance = AsyncMock()
            mock_processor_class.return_value = mock_processor_instance

            # Create multiple processors
            for session_id in session_ids:
                await processor_manager.get_processor(session_id)

            assert processor_manager.get_active_session_count() == 3

            # Clean up all
            await processor_manager.cleanup_all_processors()

            # Verify all were cleaned up
            assert processor_manager.get_active_session_count() == 0

    def test_processor_manager_get_active_sessions(self, processor_manager):
        """Test getting list of active session IDs."""
        # Initially empty
        assert processor_manager.get_active_sessions() == []

        # Add some sessions to the internal dict (simulating active processors)
        processor_manager._processors["session_1"] = MagicMock()
        processor_manager._processors["session_2"] = MagicMock()

        active_sessions = processor_manager.get_active_sessions()
        assert set(active_sessions) == {"session_1", "session_2"}
        assert processor_manager.get_active_session_count() == 2
