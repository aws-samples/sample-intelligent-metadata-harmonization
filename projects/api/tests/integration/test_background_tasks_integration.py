# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for background task processing."""

import pytest
import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from metadata_harmonization_api.workers.worker_service import WorkerService
from metadata_harmonization_api.services.processor_manager import ProcessorManager
from metadata_harmonization_processor import MetadataHarmonizationProcessor
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from tests.utils.test_data import TestDataFactory


@pytest.mark.integration
class TestBackgroundTasksIntegration:
    """Integration tests for background task processing."""

    @pytest.fixture
    def mock_processor_manager(self):
        """Mock ProcessorManager for background task testing."""
        mock_manager = AsyncMock(spec=ProcessorManager)
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

        mock_manager.get_processor.return_value = mock_processor
        mock_manager.cleanup_processor.return_value = None
        mock_manager.load_metadata_csv = AsyncMock()

        return mock_manager, mock_processor

    @pytest.fixture
    def sample_job_data(self):
        """Sample job data for testing."""
        return TestDataFactory.create_upload_job(
            job_id=str(uuid4()),
            status="pending",
        )

    @pytest.mark.asyncio
    async def test_processor_integration_in_background_task(self, mock_processor_manager, sample_job_data):
        """Test MetadataHarmonizationProcessor integration in background task processing."""
        mock_manager, mock_processor = mock_processor_manager

        import pandas as pd

        mock_df = pd.DataFrame(
            {
                "participant_id": ["", "ABC123", "DEF456"],
                "age": [25, 30, 35],
                "city": ["New York", "Los Angeles", "Chicago"],
            }
        )
        mock_manager.load_metadata_csv.return_value = mock_df

        validation_results = CombinedResults(
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
                    total_rows=50,
                    total_errors=1,
                    error_types={ValidationErrorType.REQUIRED_VALUE: 1},
                    columns_validated=1,
                ),
            )
        )
        mock_processor.process.return_value = validation_results

        worker_service = WorkerService(processor_manager=mock_manager)

        result = await worker_service.process_metadata_validation(
            job_id=sample_job_data["job_id"],
            csv_file_path="test_file.csv",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            version=1,
        )

        mock_manager.get_processor.assert_called_once_with(sample_job_data["job_id"])
        mock_processor.process.assert_called_once()

        call_args = mock_processor.process.call_args
        assert call_args[1]["core_id"] == "core_v1"
        assert call_args[1]["program_id"] == "cancer_v1"
        assert isinstance(call_args[1]["metadata_df"], pd.DataFrame)

        mock_manager.cleanup_processor.assert_called_once_with(sample_job_data["job_id"])

        assert isinstance(result, CombinedResults)
        assert result.validation_results.summary.total_errors == 1

    @pytest.mark.asyncio
    async def test_processor_error_handling_and_recovery(self, mock_processor_manager, sample_job_data):
        """Test processor error handling and recovery in background tasks."""
        mock_manager, mock_processor = mock_processor_manager

        import pandas as pd

        mock_df = pd.DataFrame({"participant_id": ["ABC123"], "age": [25]})
        mock_manager.load_metadata_csv.return_value = mock_df

        mock_processor.process.side_effect = [
            Exception("Processor temporarily unavailable"),
            CombinedResults(
                validation_results=ValidationResults(
                    validation_results=[],
                    summary=ValidationResultsSummary(
                        total_rows=10,
                        total_errors=0,
                        error_types={},
                        columns_validated=0,
                    ),
                )
            ),
        ]

        worker_service = WorkerService(processor_manager=mock_manager)

        with pytest.raises(Exception, match="Processor temporarily unavailable"):
            await worker_service.process_metadata_validation(
                job_id=sample_job_data["job_id"],
                csv_file_path="test_file.csv",
                core_schema_id="core_v1",
                program_schema_id="cancer_v1",
                version=1,
            )

        mock_manager.cleanup_processor.assert_called_with(sample_job_data["job_id"])

        mock_manager.cleanup_processor.reset_mock()
        mock_manager.get_processor.reset_mock()

        result = await worker_service.process_metadata_validation(
            job_id=sample_job_data["job_id"],
            csv_file_path="test_file.csv",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            version=1,
        )

        assert isinstance(result, CombinedResults)
        assert result.validation_results.summary.total_errors == 0

        mock_manager.cleanup_processor.assert_called_with(sample_job_data["job_id"])

    @pytest.mark.asyncio
    async def test_concurrent_background_tasks(self, mock_processor_manager):
        """Test concurrent background task processing."""
        mock_manager, mock_processor = mock_processor_manager

        import pandas as pd

        mock_df = pd.DataFrame({"participant_id": ["ABC123"], "age": [25]})
        mock_manager.load_metadata_csv.return_value = mock_df

        job_ids = [str(uuid4()) for _ in range(3)]

        worker_service = WorkerService(processor_manager=mock_manager)

        tasks = [
            worker_service.process_metadata_validation(
                job_id=job_id,
                csv_file_path=f"test_file_{job_id}.csv",
                core_schema_id="core_v1",
                program_schema_id="cancer_v1",
                version=1,
            )
            for job_id in job_ids
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, CombinedResults)

        assert mock_manager.get_processor.call_count == 3
        assert mock_manager.cleanup_processor.call_count == 3
