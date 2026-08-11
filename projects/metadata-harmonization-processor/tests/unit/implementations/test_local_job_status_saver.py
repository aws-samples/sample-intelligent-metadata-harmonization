# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for LocalJobStatusSaver implementation using Pydantic models."""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from metadata_harmonization_processor.implementations.local_job_status_saver import (
    LocalJobStatusSaver,
)
from metadata_harmonization_processor.models.job import JobResults, MetadataUploadJob


class TestLocalJobStatusSaverMemory:
    """Test LocalJobStatusSaver with in-memory storage using Pydantic models."""

    @pytest.fixture
    def memory_saver(self):
        """Create LocalJobStatusSaver with memory storage."""
        return LocalJobStatusSaver(storage_type="memory")

    @pytest.fixture
    def sample_job(self):
        """Sample MetadataUploadJob for testing."""
        return MetadataUploadJob(
            job_id="test-job-123",
            user_id="user456",
            core_schema_id="core-schema-v1",
            program_schema_id="program-schema-v1",
            status="pending",
            created_at="2024-01-01T12:00:00Z",
        )

    @pytest.fixture
    def sample_job_results(self):
        """Sample JobResults for testing."""
        return JobResults(
            storage_type="local",
            location="/tmp/validation-results/test-job-123-v1-results.json",
        )

    @pytest.mark.asyncio
    async def test_save_and_get_job_memory(self, memory_saver, sample_job):
        """Test saving and retrieving job in memory."""
        # Save job
        await memory_saver.save_job(sample_job)

        # Retrieve job
        result = await memory_saver.get_job(sample_job.job_id)

        assert result is not None
        assert isinstance(result, MetadataUploadJob)
        assert result.job_id == sample_job.job_id
        assert result.user_id == sample_job.user_id
        assert result.status == sample_job.status
        assert result.core_schema_id == sample_job.core_schema_id
        assert result.program_schema_id == sample_job.program_schema_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_job_memory(self, memory_saver):
        """Test retrieving non-existent job returns None."""
        result = await memory_saver.get_job("nonexistent-job")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_job_status_memory(self, memory_saver, sample_job):
        """Test updating job status in memory."""
        # Save initial job
        await memory_saver.save_job(sample_job)

        # Update status
        await memory_saver.update_job_status(sample_job.job_id, "completed", completed_at="2024-01-01T12:30:00Z")

        # Verify status was updated
        result = await memory_saver.get_job(sample_job.job_id)
        assert result is not None
        assert result.status == "completed"
        assert result.completed_at == "2024-01-01T12:30:00Z"

    @pytest.mark.asyncio
    async def test_update_job_status_nonexistent_memory(self, memory_saver):
        """Test updating status for non-existent job raises exception."""
        with pytest.raises(Exception, match="Job not found"):
            await memory_saver.update_job_status("nonexistent-job", "completed")

    @pytest.mark.asyncio
    async def test_add_job_results_memory(self, memory_saver, sample_job, sample_job_results):
        """Test adding job results in memory."""
        # Save initial job
        await memory_saver.save_job(sample_job)

        # Add results
        await memory_saver.add_job_results(sample_job.job_id, 1, sample_job_results)

        # Verify results were added
        result = await memory_saver.get_job(sample_job.job_id)
        assert result is not None
        assert len(result.results) == 1
        assert "1" in result.results
        assert isinstance(result.results["1"], JobResults)
        assert result.results["1"].storage_type == "local"
        assert result.results["1"].location == "/tmp/validation-results/test-job-123-v1-results.json"

    @pytest.mark.asyncio
    async def test_add_job_results_nonexistent_memory(self, memory_saver, sample_job_results):
        """Test adding results for non-existent job raises exception."""
        with pytest.raises(Exception, match="Job not found"):
            await memory_saver.add_job_results("nonexistent-job", 1, sample_job_results)

    @pytest.mark.asyncio
    async def test_job_with_multiple_results_memory(self, memory_saver, sample_job):
        """Test job with multiple result versions in memory."""
        # Save initial job
        await memory_saver.save_job(sample_job)

        # Add results for version 1
        results_v1 = JobResults(
            storage_type="local",
            location="/tmp/validation-results/test-job-123-v1-results.json",
        )
        await memory_saver.add_job_results(sample_job.job_id, 1, results_v1)

        # Add results for version 2
        results_v2 = JobResults(
            storage_type="s3",
            location="validation-results/test-job-123/v2/results.json",
            bucket="test-results-bucket",
        )
        await memory_saver.add_job_results(sample_job.job_id, 2, results_v2)

        # Verify both results exist
        result = await memory_saver.get_job(sample_job.job_id)
        assert result is not None
        assert len(result.results) == 2
        assert result.results["1"].storage_type == "local"
        assert result.results["2"].storage_type == "s3"
        assert result.results["2"].bucket == "test-results-bucket"


class TestLocalJobStatusSaverFile:
    """Test LocalJobStatusSaver with file-based storage using Pydantic models."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for file storage tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def file_saver(self, temp_dir):
        """Create LocalJobStatusSaver with file storage."""
        return LocalJobStatusSaver(storage_type="file", storage_dir=temp_dir)

    @pytest.fixture
    def sample_job(self):
        """Sample MetadataUploadJob for testing."""
        return MetadataUploadJob(
            job_id="test-job-file-123",
            user_id="user456",
            core_schema_id="core-schema-v1",
            program_schema_id="program-schema-v1",
            status="pending",
            created_at="2024-01-01T12:00:00Z",
        )

    @pytest.mark.asyncio
    async def test_save_and_get_job_file(self, file_saver, temp_dir, sample_job):
        """Test saving and retrieving job from file."""
        # Save job
        await file_saver.save_job(sample_job)

        # Verify file was created
        file_path = Path(temp_dir) / f"{sample_job.job_id}.json"
        assert file_path.exists()

        # Retrieve job
        result = await file_saver.get_job(sample_job.job_id)

        assert result is not None
        assert isinstance(result, MetadataUploadJob)
        assert result.job_id == sample_job.job_id
        assert result.user_id == sample_job.user_id
        assert result.status == sample_job.status

    @pytest.mark.asyncio
    async def test_get_nonexistent_job_file(self, file_saver):
        """Test retrieving non-existent job returns None."""
        result = await file_saver.get_job("nonexistent-job")
        assert result is None

    @pytest.mark.asyncio
    async def test_job_with_results_file_persistence(self, file_saver, sample_job):
        """Test job with results persists correctly to file."""
        # Add results to job
        job_results = JobResults(
            storage_type="s3",
            location="validation-results/test-job-file-123/v1/results.json",
            bucket="test-results-bucket",
        )
        sample_job.results = {"1": job_results}

        # Save job
        await file_saver.save_job(sample_job)

        # Retrieve job
        result = await file_saver.get_job(sample_job.job_id)

        assert result is not None
        assert len(result.results) == 1
        assert isinstance(result.results["1"], JobResults)
        assert result.results["1"].storage_type == "s3"
        assert result.results["1"].bucket == "test-results-bucket"

    @pytest.mark.asyncio
    async def test_directory_creation(self):
        """Test that storage directory is created automatically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "nested" / "job_status"

            # Directory doesn't exist initially
            assert not storage_path.exists()

            # Create saver - should create directory
            LocalJobStatusSaver(storage_type="file", storage_dir=str(storage_path))

            # Directory should now exist
            assert storage_path.exists()
            assert storage_path.is_dir()

    @pytest.mark.asyncio
    async def test_file_write_error_handling(self, temp_dir, sample_job):
        """Test error handling for file write operations."""
        file_saver = LocalJobStatusSaver(storage_type="file", storage_dir=temp_dir)

        # Mock open to raise IOError
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = IOError("Permission denied")

            with pytest.raises(Exception, match="Failed to write job file"):
                await file_saver.save_job(sample_job)

    @pytest.mark.asyncio
    async def test_file_read_error_handling(self, temp_dir, sample_job):
        """Test error handling for file read operations."""
        file_saver = LocalJobStatusSaver(storage_type="file", storage_dir=temp_dir)

        # Create a file first
        await file_saver.save_job(sample_job)

        # Mock open to raise IOError on read
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = IOError("Permission denied")

            with pytest.raises(Exception, match="Failed to read job file"):
                await file_saver.get_job(sample_job.job_id)

    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, temp_dir):
        """Test error handling for JSON decode errors."""
        file_saver = LocalJobStatusSaver(storage_type="file", storage_dir=temp_dir)
        job_id = "test-job-json-error"

        # Create a file with invalid JSON
        file_path = Path(temp_dir) / f"{job_id}.json"
        with open(file_path, "w") as f:
            f.write("invalid json content")

        with pytest.raises(Exception, match="Failed to parse job file"):
            await file_saver.get_job(job_id)

    @pytest.mark.asyncio
    async def test_json_encode_error_handling(self, temp_dir, sample_job):
        """Test error handling for JSON encode errors."""
        file_saver = LocalJobStatusSaver(storage_type="file", storage_dir=temp_dir)

        # Mock json.dump to raise TypeError (which can happen during JSON serialization)
        with patch("json.dump") as mock_dump:
            mock_dump.side_effect = TypeError("Object of type 'set' is not JSON serializable")

            with pytest.raises(Exception, match="Failed to serialize job data"):
                await file_saver.save_job(sample_job)

    @pytest.mark.asyncio
    async def test_directory_creation_error_handling(self):
        """Test error handling when directory creation fails."""
        # Try to create directory in a location that should fail
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = OSError("Permission denied")

            with pytest.raises(Exception, match="Failed to create storage directory"):
                LocalJobStatusSaver(storage_type="file", storage_dir="/invalid/path")

    @pytest.mark.asyncio
    async def test_pydantic_deserialization_error_handling(self, temp_dir):
        """Test error handling for Pydantic deserialization errors."""
        file_saver = LocalJobStatusSaver(storage_type="file", storage_dir=temp_dir)
        job_id = "test-job-pydantic-error"

        # Create a file with invalid job data (missing required fields)
        file_path = Path(temp_dir) / f"{job_id}.json"
        with open(file_path, "w") as f:
            json.dump({"job_id": job_id, "status": "pending"}, f)  # Missing required fields

        with pytest.raises(Exception, match="Failed to deserialize job data"):
            await file_saver.get_job(job_id)


class TestLocalJobStatusSaverGeneral:
    """Test general functionality of LocalJobStatusSaver using Pydantic models."""

    def test_init_memory_storage(self):
        """Test initialization with memory storage."""
        saver = LocalJobStatusSaver(storage_type="memory")
        assert saver.storage_type == "memory"
        assert isinstance(saver._memory_store, dict)
        assert len(saver._memory_store) == 0

    def test_init_file_storage_default_dir(self):
        """Test initialization with file storage and default directory."""
        with patch("pathlib.Path.mkdir"):
            saver = LocalJobStatusSaver(storage_type="file")
            assert saver.storage_type == "file"
            assert saver.storage_dir == Path("./job_status")

    def test_init_file_storage_custom_dir(self):
        """Test initialization with file storage and custom directory."""
        custom_dir = "/custom/job/status"
        with patch("pathlib.Path.mkdir"):
            saver = LocalJobStatusSaver(storage_type="file", storage_dir=custom_dir)
            assert saver.storage_type == "file"
            assert saver.storage_dir == Path(custom_dir)

    @pytest.mark.asyncio
    async def test_multiple_job_versions(self):
        """Test handling multiple result versions for the same job."""
        saver = LocalJobStatusSaver(storage_type="memory")

        # Create initial job
        job = MetadataUploadJob(
            job_id="multi-version-job",
            user_id="user123",
            core_schema_id="core-v1",
            program_schema_id="program-v1",
            status="pending",
            created_at="2024-01-01T12:00:00Z",
        )
        await saver.save_job(job)

        # Add results for version 1
        results_v1 = JobResults(storage_type="local", location="/tmp/results-v1.json")
        await saver.add_job_results(job.job_id, 1, results_v1)

        # Add results for version 2
        results_v2 = JobResults(storage_type="s3", location="results/v2/results.json", bucket="test-bucket")
        await saver.add_job_results(job.job_id, 2, results_v2)

        # Verify both versions exist
        result = await saver.get_job(job.job_id)
        assert result is not None
        assert len(result.results) == 2
        assert result.results["1"].storage_type == "local"
        assert result.results["2"].storage_type == "s3"
        assert result.results["2"].bucket == "test-bucket"

    @pytest.mark.asyncio
    async def test_job_status_progression(self):
        """Test job status progression through different states."""
        saver = LocalJobStatusSaver(storage_type="memory")

        # Create initial job
        job = MetadataUploadJob(
            job_id="status-progression-job",
            user_id="user123",
            core_schema_id="core-v1",
            program_schema_id="program-v1",
            status="pending",
            created_at="2024-01-01T12:00:00Z",
        )
        await saver.save_job(job)

        # Update to processing
        await saver.update_job_status(job.job_id, "processing")
        result = await saver.get_job(job.job_id)
        assert result.status == "processing"

        # Update to completed with completion time
        await saver.update_job_status(
            job.job_id,
            "completed",
            completed_at="2024-01-01T12:30:00Z",
            current_version=1,
        )
        result = await saver.get_job(job.job_id)
        assert result.status == "completed"
        assert result.completed_at == "2024-01-01T12:30:00Z"
        assert result.current_version == 1
