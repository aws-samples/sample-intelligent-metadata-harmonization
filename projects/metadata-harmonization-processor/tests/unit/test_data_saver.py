# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for DataSaver coordinator."""

from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

from metadata_harmonization_processor.data_saver import DataSaver
from metadata_harmonization_processor.interfaces.job_status_saver import JobStatusSaver
from metadata_harmonization_processor.interfaces.result_saver import ResultSaver
from metadata_harmonization_processor.models.change_tracking import (
    ChangeObject,
    ChangesSummary,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.job import JobResults, MetadataUploadJob
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class MockJobStatusSaver(JobStatusSaver):
    """Mock implementation of JobStatusSaver for testing."""

    def __init__(self):
        self.jobs: dict[str, MetadataUploadJob] = {}
        self.save_job_calls = []
        self.update_status_calls = []
        self.add_results_calls = []

    async def save_job(self, job: MetadataUploadJob) -> None:
        """Mock save_job implementation."""
        self.save_job_calls.append(job)
        self.jobs[job.job_id] = job

    async def get_job(self, job_id: str) -> MetadataUploadJob | None:
        """Mock get_job implementation."""
        return self.jobs.get(job_id)

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Mock update_job_status implementation."""
        self.update_status_calls.append((job_id, status, kwargs))
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            for key, value in kwargs.items():
                setattr(self.jobs[job_id], key, value)

    async def add_job_results(self, job_id: str, version: int, job_results: JobResults) -> None:
        """Mock add_job_results implementation."""
        self.add_results_calls.append((job_id, version, job_results))
        if job_id in self.jobs:
            self.jobs[job_id].results[str(version)] = job_results

    async def increment_job_version(self, job_id: str) -> int:
        """Mock increment_job_version implementation."""
        if job_id in self.jobs:
            self.jobs[job_id].current_version += 1
            return self.jobs[job_id].current_version
        raise Exception(f"Job {job_id} not found")


class MockResultSaver(ResultSaver):
    """Mock implementation of ResultSaver for testing."""

    def __init__(self):
        self.saved_results: dict[str, dict[int, ValidationResults]] = {}
        self.save_results_calls = []
        self.get_results_calls = []
        self.list_results_calls = []
        self.should_fail_save = False

    async def save_results(
        self,
        job_id: str,
        version: int,
        combined_results: CombinedResults,
        metadata: dict[str, Any] | None = None,
    ) -> JobResults:
        """Mock save_results implementation."""
        self.save_results_calls.append((job_id, version, combined_results, metadata))

        if self.should_fail_save:
            raise Exception("Mock save failure")

        if job_id not in self.saved_results:
            self.saved_results[job_id] = {}

        self.saved_results[job_id][version] = combined_results

        return JobResults(
            storage_type="local",
            location=f"/tmp/results/{job_id}/v{version}/results.json",
        )

    async def get_results(self, job_results: JobResults) -> CombinedResults | None:
        """Mock get_results implementation."""
        self.get_results_calls.append(job_results)
        # Simple mock implementation
        return None

    async def list_results(self, job_id: str) -> list[JobResults]:
        """Mock list_results implementation."""
        self.list_results_calls.append(job_id)
        return []


class TestDataSaver:
    """Test cases for DataSaver coordinator."""

    @pytest.fixture
    def mock_job_status_saver(self):
        """Create mock JobStatusSaver instance."""
        return MockJobStatusSaver()

    @pytest.fixture
    def mock_result_saver(self):
        """Create mock ResultSaver instance."""
        return MockResultSaver()

    @pytest.fixture
    def data_saver(self, mock_job_status_saver, mock_result_saver):
        """Create DataSaver instance with mocks."""
        return DataSaver(mock_job_status_saver, mock_result_saver)

    @pytest.fixture
    def sample_job(self):
        """Create sample MetadataUploadJob for testing."""
        return MetadataUploadJob(
            job_id="test-job-123",
            user_id="test-user",
            core_schema_id="core-123",
            program_schema_id="program-456",
            status="processing",
            created_at=datetime.utcnow().isoformat(),
            current_version=1,
            results={},
        )

    @pytest.fixture
    def sample_validation_results(self):
        """Create sample ValidationResults for testing."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="test_column",
            current_value="invalid_value",
            valid_options=["option1", "option2"],
            recommended_value="option1",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        summary = ValidationResultsSummary(
            total_rows=10,
            total_errors=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
            columns_validated=1,
        )

        return ValidationResults(validation_results=[error_detail], summary=summary)

    @pytest.fixture
    def sample_combined_results(self, sample_validation_results):
        """Create sample CombinedResults for testing."""
        return CombinedResults(validation_results=sample_validation_results, schema_alignment_results=None)

    def test_data_saver_initialization(self, mock_job_status_saver, mock_result_saver):
        """Test DataSaver initialization with dependencies."""
        data_saver = DataSaver(mock_job_status_saver, mock_result_saver)

        assert data_saver.job_status_saver is mock_job_status_saver
        assert data_saver.result_saver is mock_result_saver

    @pytest.mark.asyncio
    async def test_save_job_and_results_success(
        self,
        data_saver,
        mock_job_status_saver,
        mock_result_saver,
        sample_job,
        sample_combined_results,
    ):
        """Test successful save_job_and_results operation."""
        metadata = {"test": "metadata"}

        job_results = await data_saver.save_job_and_results(
            job=sample_job, combined_results=sample_combined_results, metadata=metadata
        )

        # Verify result saver was called
        assert len(mock_result_saver.save_results_calls) == 1
        save_call = mock_result_saver.save_results_calls[0]
        assert save_call[0] == sample_job.job_id
        assert save_call[1] == sample_job.current_version
        assert save_call[2] == sample_combined_results
        assert save_call[3] == metadata

        # Verify job status saver was called to add results
        assert len(mock_job_status_saver.add_results_calls) == 1
        add_results_call = mock_job_status_saver.add_results_calls[0]
        assert add_results_call[0] == sample_job.job_id
        assert add_results_call[1] == sample_job.current_version
        assert isinstance(add_results_call[2], JobResults)

        # Verify job status was updated to completed_with_errors (since sample has 1 error)
        assert len(mock_job_status_saver.update_status_calls) == 1
        status_call = mock_job_status_saver.update_status_calls[0]
        assert status_call[0] == sample_job.job_id
        assert status_call[1] == "completed_with_errors"
        assert "completed_at" in status_call[2]

        # Verify returned JobResults
        assert isinstance(job_results, JobResults)
        assert job_results.storage_type == "local"
        assert sample_job.job_id in job_results.location

    @pytest.fixture
    def sample_validation_results_no_errors(self):
        """Create sample ValidationResults with no errors for testing."""
        summary = ValidationResultsSummary(total_rows=10, total_errors=0, error_types={}, columns_validated=1)

        return ValidationResults(validation_results=[], summary=summary)

    @pytest.fixture
    def sample_combined_results_no_errors(self, sample_validation_results_no_errors):
        """Create sample CombinedResults with no errors for testing."""
        return CombinedResults(
            validation_results=sample_validation_results_no_errors,
            schema_alignment_results=None,
        )

    @pytest.mark.asyncio
    async def test_save_job_and_results_success_no_errors(
        self,
        data_saver,
        mock_job_status_saver,
        mock_result_saver,
        sample_job,
        sample_combined_results_no_errors,
    ):
        """Test successful save_job_and_results operation with no validation errors."""
        metadata = {"test": "metadata"}

        await data_saver.save_job_and_results(
            job=sample_job,
            combined_results=sample_combined_results_no_errors,
            metadata=metadata,
        )

        # Verify job status was updated to completed (since no errors)
        assert len(mock_job_status_saver.update_status_calls) == 1
        status_call = mock_job_status_saver.update_status_calls[0]
        assert status_call[0] == sample_job.job_id
        assert status_call[1] == "completed"
        assert "completed_at" in status_call[2]

    @pytest.mark.asyncio
    async def test_save_job_and_results_failure(
        self,
        data_saver,
        mock_job_status_saver,
        mock_result_saver,
        sample_job,
        sample_combined_results,
    ):
        """Test save_job_and_results handles result saving failure."""
        # Configure mock to fail
        mock_result_saver.should_fail_save = True

        with pytest.raises(Exception, match="Mock save failure"):
            await data_saver.save_job_and_results(job=sample_job, combined_results=sample_combined_results)

        # Verify job status was updated to failed
        assert len(mock_job_status_saver.update_status_calls) == 1
        status_call = mock_job_status_saver.update_status_calls[0]
        assert status_call[0] == sample_job.job_id
        assert status_call[1] == "failed"
        assert "completed_at" in status_call[2]

    @pytest.mark.asyncio
    async def test_create_job(self, data_saver, mock_job_status_saver):
        """Test create_job creates and saves new job."""
        job_id = "new-job-123"
        user_id = "test-user"
        core_schema_id = "core-456"
        program_schema_id = "program-789"

        job = await data_saver.create_job(
            job_id=job_id,
            user_id=user_id,
            core_schema_id=core_schema_id,
            program_schema_id=program_schema_id,
        )

        # Verify job was created with correct properties
        assert job.job_id == job_id
        assert job.user_id == user_id
        assert job.core_schema_id == core_schema_id
        assert job.program_schema_id == program_schema_id
        assert job.status == "pending"
        assert job.current_version == 1
        assert job.results == {}
        assert job.created_at is not None
        assert job.completed_at is None

        # Verify job was saved
        assert len(mock_job_status_saver.save_job_calls) == 1
        assert mock_job_status_saver.save_job_calls[0] == job

    @pytest.mark.asyncio
    async def test_update_job_status(self, data_saver, mock_job_status_saver):
        """Test update_job_status delegates to job status saver."""
        job_id = "test-job-456"
        status = "processing"
        kwargs = {"some_field": "some_value"}

        await data_saver.update_job_status(job_id, status, **kwargs)

        # Verify job status saver was called
        assert len(mock_job_status_saver.update_status_calls) == 1
        status_call = mock_job_status_saver.update_status_calls[0]
        assert status_call[0] == job_id
        assert status_call[1] == status
        assert status_call[2] == kwargs

    @pytest.mark.asyncio
    async def test_get_job(self, data_saver, mock_job_status_saver, sample_job):
        """Test get_job delegates to job status saver."""
        # Add job to mock storage
        mock_job_status_saver.jobs[sample_job.job_id] = sample_job

        retrieved_job = await data_saver.get_job(sample_job.job_id)

        assert retrieved_job == sample_job

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, data_saver, mock_job_status_saver):
        """Test get_job returns None for non-existent job."""
        retrieved_job = await data_saver.get_job("nonexistent-job")

        assert retrieved_job is None

    @pytest.mark.asyncio
    async def test_get_results(self, data_saver, mock_result_saver):
        """Test get_results delegates to result saver."""
        job_results = JobResults(storage_type="local", location="/tmp/test/results.json")

        await data_saver.get_results(job_results)

        # Verify result saver was called
        assert len(mock_result_saver.get_results_calls) == 1
        assert mock_result_saver.get_results_calls[0] == job_results

    @pytest.mark.asyncio
    async def test_list_results(self, data_saver, mock_result_saver):
        """Test list_results delegates to result saver."""
        job_id = "test-job-789"

        await data_saver.list_results(job_id)

        # Verify result saver was called
        assert len(mock_result_saver.list_results_calls) == 1
        assert mock_result_saver.list_results_calls[0] == job_id

    @pytest.mark.asyncio
    async def test_save_job_and_results_without_metadata(
        self, data_saver, mock_result_saver, sample_job, sample_combined_results
    ):
        """Test save_job_and_results works without metadata parameter."""
        job_results = await data_saver.save_job_and_results(job=sample_job, combined_results=sample_combined_results)

        # Verify result saver was called with None metadata
        assert len(mock_result_saver.save_results_calls) == 1
        save_call = mock_result_saver.save_results_calls[0]
        assert save_call[3] is None  # metadata parameter

        # Verify operation completed successfully
        assert isinstance(job_results, JobResults)


class TestDataSaverChangeDetectionIntegration:
    """Test cases for DataSaver change detection integration."""

    @pytest.fixture
    def mock_job_status_saver(self):
        """Create mock JobStatusSaver instance."""
        return MockJobStatusSaver()

    @pytest.fixture
    def mock_result_saver(self):
        """Create mock ResultSaver instance."""
        return MockResultSaver()

    @pytest.fixture
    def data_saver_with_change_detection(self, mock_job_status_saver, mock_result_saver):
        """Create DataSaver instance with change detection enabled."""
        return DataSaver(mock_job_status_saver, mock_result_saver, enable_change_detection=True)

    @pytest.fixture
    def data_saver_without_change_detection(self, mock_job_status_saver, mock_result_saver):
        """Create DataSaver instance with change detection disabled."""
        return DataSaver(mock_job_status_saver, mock_result_saver, enable_change_detection=False)

    @pytest.fixture
    def sample_job(self):
        """Create sample MetadataUploadJob for testing."""
        return MetadataUploadJob(
            job_id="test-job-123",
            user_id="test-user",
            core_schema_id="core-123",
            program_schema_id="program-456",
            status="processing",
            created_at=datetime.utcnow().isoformat(),
            current_version=2,  # Version 2 to enable change detection
            results={},
        )

    @pytest.fixture
    def sample_combined_results(self):
        """Create sample CombinedResults for testing."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="test_column",
            current_value="invalid_value",
            valid_options=["option1", "option2"],
            recommended_value="option1",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        summary = ValidationResultsSummary(
            total_rows=10,
            total_errors=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
            columns_validated=1,
        )

        validation_results = ValidationResults(validation_results=[error_detail], summary=summary)

        return CombinedResults(validation_results=validation_results, schema_alignment_results=None)

    @pytest.mark.asyncio
    async def test_change_detection_enabled_initialization(self, data_saver_with_change_detection):
        """Test DataSaver initialization with change detection enabled."""
        assert data_saver_with_change_detection.enable_change_detection is True
        assert data_saver_with_change_detection.change_detector is not None

    @pytest.mark.asyncio
    async def test_change_detection_disabled_initialization(self, data_saver_without_change_detection):
        """Test DataSaver initialization with change detection disabled."""
        assert data_saver_without_change_detection.enable_change_detection is False
        assert data_saver_without_change_detection.change_detector is None

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.utils.schema_change_detector.ChangeDetector.detect_changes")
    async def test_save_job_and_results_with_change_detection_success(
        self,
        mock_detect_changes,
        data_saver_with_change_detection,
        sample_job,
        sample_combined_results,
    ):
        """Test save_job_and_results triggers change detection successfully."""
        # Mock change detection to return some changes
        mock_changes = [
            ChangeObject(
                change_type="add",
                source_type="user",
                component="validation",
                column="test_column",
                row=1,
                new_value="new_value",
                source_version=1,
                target_version=2,
            )
        ]
        mock_detect_changes.return_value = mock_changes

        job_results = await data_saver_with_change_detection.save_job_and_results(
            job=sample_job, combined_results=sample_combined_results
        )

        # Verify change detection was called
        mock_detect_changes.assert_called_once_with(
            job_id=sample_job.job_id,
            current_version=sample_job.current_version,
            current_results=sample_combined_results,
            result_saver=data_saver_with_change_detection.result_saver,
        )

        # Verify job completed successfully despite change detection
        assert isinstance(job_results, JobResults)

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.utils.schema_change_detector.ChangeDetector.detect_changes")
    async def test_save_job_and_results_with_change_detection_no_changes(
        self,
        mock_detect_changes,
        data_saver_with_change_detection,
        sample_job,
        sample_combined_results,
    ):
        """Test save_job_and_results handles no changes detected."""
        # Mock change detection to return no changes
        mock_detect_changes.return_value = []

        job_results = await data_saver_with_change_detection.save_job_and_results(
            job=sample_job, combined_results=sample_combined_results
        )

        # Verify change detection was called
        mock_detect_changes.assert_called_once()

        # Verify job completed successfully
        assert isinstance(job_results, JobResults)

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.utils.schema_change_detector.ChangeDetector.detect_changes")
    async def test_save_job_and_results_with_change_detection_failure(
        self,
        mock_detect_changes,
        data_saver_with_change_detection,
        sample_job,
        sample_combined_results,
    ):
        """Test save_job_and_results handles change detection failure gracefully."""
        # Mock change detection to raise an exception
        mock_detect_changes.side_effect = Exception("Change detection failed")

        with patch("metadata_harmonization_processor.data_saver.logger") as mock_logger:
            job_results = await data_saver_with_change_detection.save_job_and_results(
                job=sample_job, combined_results=sample_combined_results
            )

        # Verify change detection was called
        mock_detect_changes.assert_called_once()

        # Verify job completed successfully despite change detection failure
        assert isinstance(job_results, JobResults)

        # Verify error was logged
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any("Change detection failed for job test-job-123" in call for call in error_calls)
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Continuing with save operation despite change detection failure" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_save_job_and_results_without_change_detection(
        self, data_saver_without_change_detection, sample_job, sample_combined_results
    ):
        """Test save_job_and_results skips change detection when disabled."""
        with patch(
            "metadata_harmonization_processor.utils.schema_change_detector.ChangeDetector.detect_changes"
        ) as mock_detect_changes:
            job_results = await data_saver_without_change_detection.save_job_and_results(
                job=sample_job, combined_results=sample_combined_results
            )

            # Verify change detection was not called
            mock_detect_changes.assert_not_called()

            # Verify job completed successfully
            assert isinstance(job_results, JobResults)

    @pytest.mark.asyncio
    @patch("metadata_harmonization_processor.utils.schema_change_detector.ChangeDetector.detect_changes")
    async def test_save_job_and_results_change_detection_logging(
        self,
        mock_detect_changes,
        data_saver_with_change_detection,
        sample_job,
        sample_combined_results,
    ):
        """Test save_job_and_results produces appropriate change detection log messages."""
        # Mock change detection to return some changes
        mock_changes = [
            ChangeObject(
                change_type="add",
                source_type="user",
                component="validation",
                column="column_a",
                row=1,
                new_value="new_value",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_type="remove",
                source_type="system",
                component="validation",
                column="column_b",
                row=1,
                old_value="old_value",
                source_version=1,
                target_version=2,
                confidence_score=0.8,
            ),
        ]
        mock_detect_changes.return_value = mock_changes

        with patch("metadata_harmonization_processor.data_saver.logger") as mock_logger:
            await data_saver_with_change_detection.save_job_and_results(
                job=sample_job, combined_results=sample_combined_results
            )

        # Check log messages
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Starting change detection for job test-job-123, version 2" in call for call in info_calls)
        assert any("Change detection completed for job test-job-123: 2 changes detected" in call for call in info_calls)
        assert any("Changes summary for job test-job-123: 2 total changes" in call for call in info_calls)
        assert any("1 adds, 1 removes, 0 renames" in call for call in info_calls)
        assert any("1 system changes, 1 user changes" in call for call in info_calls)


class TestDataSaverChangesSummary:
    """Test cases for DataSaver _create_changes_summary method."""

    @pytest.fixture
    def mock_job_status_saver(self):
        """Create mock JobStatusSaver instance."""
        return MockJobStatusSaver()

    @pytest.fixture
    def mock_result_saver(self):
        """Create mock ResultSaver instance."""
        return MockResultSaver()

    @pytest.fixture
    def data_saver(self, mock_job_status_saver, mock_result_saver):
        """Create DataSaver instance with mocks."""
        return DataSaver(mock_job_status_saver, mock_result_saver)

    @pytest.fixture
    def sample_add_change(self):
        """Create sample 'add' change object."""
        return ChangeObject(
            change_type="add",
            source_type="user",
            component="validation",
            column="column_a",
            row=1,
            new_value="new_value",
            source_version=1,
            target_version=2,
        )

    @pytest.fixture
    def sample_remove_change(self):
        """Create sample 'remove' change object."""
        return ChangeObject(
            change_type="remove",
            source_type="system",
            component="validation",
            column="column_b",
            row=2,
            old_value="old_value",
            source_version=1,
            target_version=2,
            confidence_score=0.8,
        )

    @pytest.fixture
    def sample_rename_change(self):
        """Create sample 'rename' change object."""
        return ChangeObject(
            change_type="rename",
            source_type="user",
            component="schema_alignment",
            column="field_name",
            old_value="old_name",
            new_value="new_name",
            source_version=1,
            target_version=2,
        )

    def test_create_changes_summary_empty_list(self, data_saver):
        """Test _create_changes_summary with empty changes list."""
        changes = []

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 0
        assert summary.adds == 0
        assert summary.removes == 0
        assert summary.renames == 0
        assert summary.system_changes == 0
        assert summary.user_changes == 0

    def test_create_changes_summary_single_add(self, data_saver, sample_add_change):
        """Test _create_changes_summary with single add change."""
        changes = [sample_add_change]

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 1
        assert summary.adds == 1
        assert summary.removes == 0
        assert summary.renames == 0
        assert summary.system_changes == 0
        assert summary.user_changes == 1

    def test_create_changes_summary_single_remove(self, data_saver, sample_remove_change):
        """Test _create_changes_summary with single remove change."""
        changes = [sample_remove_change]

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 1
        assert summary.adds == 0
        assert summary.removes == 1
        assert summary.renames == 0
        assert summary.system_changes == 1
        assert summary.user_changes == 0

    def test_create_changes_summary_single_rename(self, data_saver, sample_rename_change):
        """Test _create_changes_summary with single rename change."""
        changes = [sample_rename_change]

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 1
        assert summary.adds == 0
        assert summary.removes == 0
        assert summary.renames == 1
        assert summary.system_changes == 0
        assert summary.user_changes == 1

    def test_create_changes_summary_mixed_changes(
        self, data_saver, sample_add_change, sample_remove_change, sample_rename_change
    ):
        """Test _create_changes_summary with mixed change types."""
        changes = [sample_add_change, sample_remove_change, sample_rename_change]

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 3
        assert summary.adds == 1
        assert summary.removes == 1
        assert summary.renames == 1
        assert summary.system_changes == 1  # only sample_remove_change is system
        assert summary.user_changes == 2  # sample_add_change and sample_rename_change are user

    def test_create_changes_summary_multiple_same_type(self, data_saver):
        """Test _create_changes_summary with multiple changes of same type."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="user",
                component="validation",
                column="column_a",
                row=1,
                new_value="value1",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                column="column_a",
                row=2,
                new_value="value2",
                source_version=1,
                target_version=2,
                confidence_score=0.9,
            ),
            ChangeObject(
                change_type="add",
                source_type="user",
                component="schema_alignment",
                column="field1",
                new_value="value3",
                source_version=1,
                target_version=2,
            ),
        ]

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 3
        assert summary.adds == 3
        assert summary.removes == 0
        assert summary.renames == 0
        assert summary.system_changes == 1
        assert summary.user_changes == 2

    def test_create_changes_summary_all_system_changes(self, data_saver):
        """Test _create_changes_summary with all system changes."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                column="column_a",
                row=1,
                new_value="value1",
                source_version=1,
                target_version=2,
                confidence_score=0.7,
            ),
            ChangeObject(
                change_type="remove",
                source_type="system",
                component="validation",
                column="column_b",
                row=1,
                old_value="old_value",
                source_version=1,
                target_version=2,
                confidence_score=0.8,
            ),
            ChangeObject(
                change_type="rename",
                source_type="system",
                component="schema_alignment",
                column="field",
                old_value="old_name",
                new_value="new_name",
                source_version=1,
                target_version=2,
                confidence_score=0.9,
            ),
        ]

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 3
        assert summary.adds == 1
        assert summary.removes == 1
        assert summary.renames == 1
        assert summary.system_changes == 3
        assert summary.user_changes == 0

    def test_create_changes_summary_all_user_changes(self, data_saver):
        """Test _create_changes_summary with all user changes."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="user",
                component="validation",
                column="column_a",
                row=1,
                new_value="value1",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_type="remove",
                source_type="user",
                component="validation",
                column="column_b",
                row=1,
                old_value="old_value",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="schema_alignment",
                column="field",
                old_value="old_name",
                new_value="new_name",
                source_version=1,
                target_version=2,
            ),
        ]

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 3
        assert summary.adds == 1
        assert summary.removes == 1
        assert summary.renames == 1
        assert summary.system_changes == 0
        assert summary.user_changes == 3

    def test_create_changes_summary_large_dataset(self, data_saver):
        """Test _create_changes_summary with large number of changes."""
        changes = []

        # Create 100 changes of different types and sources
        for i in range(100):
            change_type = ["add", "remove", "rename"][i % 3]
            source_type = ["system", "user"][i % 2]

            if change_type == "add":
                change = ChangeObject(
                    change_type=change_type,
                    source_type=source_type,
                    component="validation",
                    column="column_a",
                    row=i + 1,
                    new_value=f"value_{i}",
                    source_version=1,
                    target_version=2,
                    confidence_score=0.8 if source_type == "system" else None,
                )
            elif change_type == "remove":
                change = ChangeObject(
                    change_type=change_type,
                    source_type=source_type,
                    component="validation",
                    column="column_b",
                    row=i + 1,
                    old_value=f"old_value_{i}",
                    source_version=1,
                    target_version=2,
                    confidence_score=0.8 if source_type == "system" else None,
                )
            else:  # rename
                change = ChangeObject(
                    change_type=change_type,
                    source_type=source_type,
                    component="schema_alignment",
                    column=f"field_{i}",
                    old_value=f"old_name_{i}",
                    new_value=f"new_name_{i}",
                    source_version=1,
                    target_version=2,
                    confidence_score=0.8 if source_type == "system" else None,
                )

            changes.append(change)

        summary = data_saver._create_changes_summary(changes)

        assert isinstance(summary, ChangesSummary)
        assert summary.total_changes == 100

        # Verify counts based on pattern
        # adds: indices 0, 3, 6, 9, ... (every 3rd starting from 0) = 34 items
        # removes: indices 1, 4, 7, 10, ... (every 3rd starting from 1) = 33 items
        # renames: indices 2, 5, 8, 11, ... (every 3rd starting from 2) = 33 items
        assert summary.adds == 34
        assert summary.removes == 33
        assert summary.renames == 33

        # system: indices 0, 2, 4, 6, ... (even indices) = 50 items
        # user: indices 1, 3, 5, 7, ... (odd indices) = 50 items
        assert summary.system_changes == 50
        assert summary.user_changes == 50

    def test_create_changes_summary_invalid_change_object(self, data_saver):
        """Test _create_changes_summary handles invalid change objects gracefully."""
        # Create a change object that will cause validation error in ChangesSummary.from_changes
        # This is tricky since ChangeObject has its own validation, so we'll test with None
        changes = [None]  # This should cause an error

        with pytest.raises(ValueError, match="Failed to create changes summary"):
            data_saver._create_changes_summary(changes)

    def test_create_changes_summary_logging(self, data_saver, sample_add_change):
        """Test _create_changes_summary produces appropriate log messages."""
        with patch("metadata_harmonization_processor.data_saver.logger") as mock_logger:
            changes = [sample_add_change]
            data_saver._create_changes_summary(changes)

            # Check debug log message
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any("Creating changes summary" in call for call in debug_calls)

            # Check info log message
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Created changes summary: 1 total changes" in call for call in info_calls)
            assert any("1 adds, 0 removes, 0 renames" in call for call in info_calls)
            assert any("0 system changes, 1 user changes" in call for call in info_calls)
