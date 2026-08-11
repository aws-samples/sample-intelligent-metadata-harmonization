# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for LocalResultSaver implementation."""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from metadata_harmonization_processor.implementations.local_result_saver import (  # noqa: E501
    LocalResultSaver,
)
from metadata_harmonization_processor.models.combined_results import (  # noqa: E501
    CombinedResults,
)
from metadata_harmonization_processor.models.job import JobResults
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class TestLocalResultSaver:
    """Test LocalResultSaver with local file storage."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for file storage tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def result_saver(self, temp_dir):
        """Create LocalResultSaver with temporary directory."""
        return LocalResultSaver(storage_dir=temp_dir)

    @pytest.fixture
    def sample_validation_results(self):
        """Sample ValidationResults for testing."""
        errors = [
            ValidationErrorDetail(
                row=1,
                column="age",
                current_value="invalid_age",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.INVALID_PATTERN,
            ),
            ValidationErrorDetail(
                row=2,
                column="gender",
                current_value="X",
                valid_options=["M", "F"],
                recommended_value="F",
                error_type=ValidationErrorType.INVALID_OPTION,
            ),
        ]

        summary = ValidationResultsSummary(
            total_rows=10,
            total_errors=2,
            columns_validated=2,
            error_types={
                ValidationErrorType.INVALID_PATTERN: 1,
                ValidationErrorType.INVALID_OPTION: 1,
                ValidationErrorType.REQUIRED_VALUE: 0,
            },
        )

        return ValidationResults(validation_results=errors, summary=summary)

    @pytest.fixture
    def sample_combined_results(self, sample_validation_results):
        """Sample CombinedResults for testing."""
        return CombinedResults(validation_results=sample_validation_results)

    def test_init_with_default_directory(self):
        """Test initialization with default directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_resolve.return_value = Path(temp_dir) / "validation-results"
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    saver = LocalResultSaver()
                    assert saver.storage_dir == Path(temp_dir) / "validation-results"
                    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_with_custom_directory(self, temp_dir):
        """Test initialization with custom directory."""
        custom_dir = Path(temp_dir) / "custom_results"
        saver = LocalResultSaver(storage_dir=str(custom_dir))
        assert saver.storage_dir == custom_dir.resolve()
        assert custom_dir.exists()

    def test_init_with_empty_directory_raises_error(self):
        """Test initialization with empty directory raises ValueError."""
        with pytest.raises(ValueError, match="storage_dir cannot be empty"):
            LocalResultSaver(storage_dir="")

    def test_init_directory_creation_error(self):
        """Test initialization handles directory creation errors."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = OSError("Permission denied")
            with pytest.raises(OSError, match="Permission denied"):
                LocalResultSaver(storage_dir="/invalid/path")

    @pytest.mark.asyncio
    async def test_save_results_success(self, result_saver, sample_combined_results):
        """Test successful result saving."""
        job_id = "test-job-123"
        version = 1
        metadata = {"processing_time": 45.2, "rows_processed": 100}

        job_results = await result_saver.save_results(
            job_id=job_id,
            version=version,
            combined_results=sample_combined_results,
            metadata=metadata,
        )

        # Verify JobResults
        assert job_results.storage_type == "local"
        assert job_results.location == "test-job-123/v1/results.json"

        # Verify file was created
        file_path = result_saver.storage_dir / job_results.location
        assert file_path.exists()

        # Verify file contents
        with open(file_path, "r", encoding="utf-8") as f:
            stored_data = json.load(f)

        assert stored_data["job_id"] == job_id
        assert stored_data["version"] == version
        assert stored_data["metadata"] == metadata
        assert "timestamp" in stored_data
        assert "combined_results" in stored_data

        # Verify results structure
        results_data = stored_data["combined_results"]["validation_results"]
        assert results_data["summary"]["total_errors"] == 2
        assert len(results_data["validation_results"]) == 2

    @pytest.mark.asyncio
    async def test_save_results_empty_job_id_raises_error(self, result_saver, sample_combined_results):
        """Test save_results with empty job_id raises ValueError."""
        with pytest.raises(ValueError, match="job_id cannot be empty"):
            await result_saver.save_results("", 1, sample_combined_results)

    @pytest.mark.asyncio
    async def test_save_results_invalid_version_raises_error(self, result_saver, sample_combined_results):
        """Test save_results with invalid version raises ValueError."""
        with pytest.raises(ValueError, match="version must be >= 1"):
            await result_saver.save_results("job-123", 0, sample_combined_results)

    @pytest.mark.asyncio
    async def test_save_results_file_write_error(self, result_saver, sample_combined_results):
        """Test save_results handles file write errors."""
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = OSError("Permission denied")

            with pytest.raises(OSError, match="Permission denied"):
                await result_saver.save_results("job-123", 1, sample_combined_results)

    @pytest.mark.asyncio
    async def test_get_results_success(self, result_saver, sample_combined_results):
        """Test successful result retrieval."""
        # First save results
        job_results = await result_saver.save_results(
            job_id="test-job-456", version=1, combined_results=sample_combined_results
        )

        # Then retrieve them
        retrieved_results = await result_saver.get_results(job_results)

        assert retrieved_results is not None
        assert isinstance(retrieved_results, CombinedResults)
        assert retrieved_results.validation_results is not None
        assert retrieved_results.validation_results.summary.total_errors == 2
        assert len(retrieved_results.validation_results.validation_results) == 2

        # Verify error details
        error1 = retrieved_results.validation_results.validation_results[0]
        assert error1.row == 1
        assert error1.column == "age"
        assert error1.current_value == "invalid_age"
        assert error1.error_type == ValidationErrorType.INVALID_PATTERN

    @pytest.mark.asyncio
    async def test_get_results_wrong_storage_type_raises_error(self, result_saver):
        """Test get_results with wrong storage type raises ValueError."""
        job_results = JobResults(storage_type="s3", location="bucket/key/results.json", bucket="test-bucket")

        with pytest.raises(ValueError, match="Expected local storage type, got: s3"):
            await result_saver.get_results(job_results)

    @pytest.mark.asyncio
    async def test_get_results_file_not_found_returns_none(self, result_saver):
        """Test get_results returns None when file doesn't exist."""
        job_results = JobResults(storage_type="local", location="nonexistent-job/v1/results.json")

        result = await result_saver.get_results(job_results)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_results_file_read_error(self, result_saver):
        """Test get_results handles file read errors."""
        job_results = JobResults(storage_type="local", location="test-job/v1/results.json")

        # Create the file path but mock read error
        file_path = result_saver.storage_dir / job_results.location
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = OSError("Permission denied")

            with pytest.raises(OSError, match="Permission denied"):
                await result_saver.get_results(job_results)

    @pytest.mark.asyncio
    async def test_get_results_invalid_json_raises_error(self, result_saver):
        """Test get_results handles invalid JSON."""
        job_results = JobResults(storage_type="local", location="test-job/v1/results.json")

        # Create file with invalid JSON
        file_path = result_saver.storage_dir / job_results.location
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            await result_saver.get_results(job_results)

    @pytest.mark.asyncio
    async def test_get_results_missing_results_data_raises_error(self, result_saver):
        """Test get_results raises error when combined_results data is missing."""
        job_results = JobResults(storage_type="local", location="test-job/v1/results.json")

        # Create file with missing combined_results data
        file_path = result_saver.storage_dir / job_results.location
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump({"job_id": "test-job", "version": 1}, f)

        # This should raise an error since combined_results is None
        with pytest.raises((TypeError, AttributeError)):
            await result_saver.get_results(job_results)

    @pytest.mark.asyncio
    async def test_list_results_success(self, result_saver, sample_combined_results):
        """Test successful result listing."""
        job_id = "multi-version-job"

        # Save multiple versions
        await result_saver.save_results(job_id, 1, sample_combined_results)
        await result_saver.save_results(job_id, 2, sample_combined_results)
        await result_saver.save_results(job_id, 3, sample_combined_results)

        # List results
        results = await result_saver.list_results(job_id)

        assert len(results) == 3

        # Verify results are sorted by version
        assert results[0].location == "multi-version-job/v1/results.json"
        assert results[1].location == "multi-version-job/v2/results.json"
        assert results[2].location == "multi-version-job/v3/results.json"

        # Verify all are local storage type
        for result in results:
            assert result.storage_type == "local"

    @pytest.mark.asyncio
    async def test_list_results_empty_job_id_raises_error(self, result_saver):
        """Test list_results with empty job_id raises ValueError."""
        with pytest.raises(ValueError, match="job_id cannot be empty"):
            await result_saver.list_results("")

    @pytest.mark.asyncio
    async def test_list_results_no_job_directory_returns_empty(self, result_saver):
        """Test list_results returns empty list when job directory doesn't exist."""
        results = await result_saver.list_results("nonexistent-job")
        assert results == []

    @pytest.mark.asyncio
    async def test_list_results_skips_invalid_directories(self, result_saver, sample_combined_results):
        """Test list_results skips directories that don't match expected pattern."""
        job_id = "test-job-with-invalid-dirs"

        # Save one valid result
        await result_saver.save_results(job_id, 1, sample_combined_results)

        # Create invalid directories
        job_dir = result_saver.storage_dir / job_id
        (job_dir / "invalid_dir").mkdir()
        (job_dir / "v2_invalid").mkdir()
        (job_dir / "vnotanumber").mkdir()

        # List results should only return the valid one
        results = await result_saver.list_results(job_id)
        assert len(results) == 1
        assert results[0].location == "test-job-with-invalid-dirs/v1/results.json"

    @pytest.mark.asyncio
    async def test_list_results_directory_read_error(self, result_saver):
        """Test list_results handles directory read errors."""
        job_id = "error-job"

        # Create job directory
        job_dir = result_saver.storage_dir / job_id
        job_dir.mkdir()

        with patch("pathlib.Path.iterdir") as mock_iterdir:
            mock_iterdir.side_effect = OSError("Permission denied")

            with pytest.raises(OSError, match="Permission denied"):
                await result_saver.list_results(job_id)

    @pytest.mark.asyncio
    async def test_utf8_encoding_support(self, result_saver):
        """Test UTF-8 encoding support for international characters."""
        # Create validation results with international characters
        errors = [
            ValidationErrorDetail(
                row=1,
                column="name",
                current_value="José María",
                valid_options=["José", "María"],
                recommended_value="José",
                error_type=ValidationErrorType.INVALID_OPTION,
            )
        ]

        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            columns_validated=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
        )

        validation_results = ValidationResults(validation_results=errors, summary=summary)
        combined_results = CombinedResults(validation_results=validation_results)

        # Save and retrieve
        job_results = await result_saver.save_results("utf8-job", 1, combined_results)
        retrieved_results = await result_saver.get_results(job_results)

        assert retrieved_results is not None
        assert retrieved_results.validation_results is not None
        assert retrieved_results.validation_results.validation_results[0].current_value == "José María"
        assert retrieved_results.validation_results.validation_results[0].recommended_value == "José"

    @pytest.mark.asyncio
    async def test_relative_path_resolution(self):
        """Test that relative paths are properly resolved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use relative path
            relative_path = "./test_results"

            with patch("pathlib.Path.resolve") as mock_resolve:
                resolved_path = Path(temp_dir) / "test_results"
                mock_resolve.return_value = resolved_path

                with patch("pathlib.Path.mkdir"):
                    saver = LocalResultSaver(storage_dir=relative_path)
                    assert saver.storage_dir == resolved_path
                    mock_resolve.assert_called_once()
