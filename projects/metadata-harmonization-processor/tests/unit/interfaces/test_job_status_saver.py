# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for JobStatusSaver interface contract."""

from abc import ABC
from unittest.mock import AsyncMock

import pytest

from metadata_harmonization_processor.interfaces.job_status_saver import JobStatusSaver
from metadata_harmonization_processor.models.job import JobResults, MetadataUploadJob


class MockJobStatusSaver(JobStatusSaver):
    """Mock implementation of JobStatusSaver for testing interface contract."""

    def __init__(self):
        self.jobs: dict[str, MetadataUploadJob] = {}
        self._save_job_mock = AsyncMock()
        self._get_job_mock = AsyncMock()
        self._update_job_status_mock = AsyncMock()
        self._add_job_results_mock = AsyncMock()
        self._increment_job_version_mock = AsyncMock()

    async def save_job(self, job: MetadataUploadJob) -> None:
        """Mock implementation of save_job."""
        await self._save_job_mock(job)
        self.jobs[job.job_id] = job

    async def get_job(self, job_id: str) -> MetadataUploadJob | None:
        """Mock implementation of get_job."""
        await self._get_job_mock(job_id)
        return self.jobs.get(job_id)

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Mock implementation of update_job_status."""
        await self._update_job_status_mock(job_id, status, **kwargs)
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            for key, value in kwargs.items():
                if hasattr(self.jobs[job_id], key):
                    setattr(self.jobs[job_id], key, value)

    async def add_job_results(self, job_id: str, version: int, job_results: JobResults) -> None:
        """Mock implementation of add_job_results."""
        await self._add_job_results_mock(job_id, version, job_results)
        if job_id in self.jobs:
            self.jobs[job_id].results[str(version)] = job_results

    async def increment_job_version(self, job_id: str) -> int:
        """Mock implementation of increment_job_version."""
        await self._increment_job_version_mock(job_id)
        if job_id in self.jobs:
            self.jobs[job_id].current_version += 1
            return self.jobs[job_id].current_version
        raise Exception(f"Job {job_id} not found")


class TestJobStatusSaver:
    """Test cases for JobStatusSaver interface contract."""

    def test_is_abstract_base_class(self):
        """Test that JobStatusSaver is an abstract base class."""
        assert issubclass(JobStatusSaver, ABC)

        with pytest.raises(TypeError):
            JobStatusSaver()

    def test_has_required_abstract_methods(self):
        """Test that JobStatusSaver has all required abstract methods."""
        abstract_methods = JobStatusSaver.__abstractmethods__
        expected_methods = {
            "save_job",
            "get_job",
            "update_job_status",
            "add_job_results",
            "increment_job_version",
        }

        assert abstract_methods == expected_methods

    @pytest.mark.asyncio
    async def test_save_job_interface(self):
        """Test save_job method interface contract."""
        saver = MockJobStatusSaver()

        job = MetadataUploadJob(
            job_id="test_job_123",
            user_id="user_456",
            core_schema_id="core_schema_1",
            program_schema_id="program_schema_1",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
        )

        await saver.save_job(job)

        saver._save_job_mock.assert_called_once_with(job)
        assert saver.jobs["test_job_123"] == job

    @pytest.mark.asyncio
    async def test_get_job_interface(self):
        """Test get_job method interface contract."""
        saver = MockJobStatusSaver()

        job_id = "test_job_123"

        result = await saver.get_job(job_id)
        assert result is None

        job = MetadataUploadJob(
            job_id=job_id,
            user_id="user_456",
            core_schema_id="core_schema_1",
            program_schema_id="program_schema_1",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
        )
        await saver.save_job(job)

        result = await saver.get_job(job_id)
        assert result is not None
        assert result.job_id == job_id
        assert result.status == "pending"

        saver._get_job_mock.assert_called_with(job_id)

    @pytest.mark.asyncio
    async def test_update_job_status_interface(self):
        """Test update_job_status method interface contract."""
        saver = MockJobStatusSaver()

        job_id = "test_job_123"
        job = MetadataUploadJob(
            job_id=job_id,
            user_id="user_456",
            core_schema_id="core_schema_1",
            program_schema_id="program_schema_1",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
        )
        await saver.save_job(job)

        await saver.update_job_status(job_id, "completed", completed_at="2024-01-01T01:00:00Z")

        saver._update_job_status_mock.assert_called_once_with(job_id, "completed", completed_at="2024-01-01T01:00:00Z")

        updated_job = await saver.get_job(job_id)
        assert updated_job.status == "completed"
        assert updated_job.completed_at == "2024-01-01T01:00:00Z"

    @pytest.mark.asyncio
    async def test_add_job_results_interface(self):
        """Test add_job_results method interface contract."""
        saver = MockJobStatusSaver()

        job_id = "test_job_123"
        job = MetadataUploadJob(
            job_id=job_id,
            user_id="user_456",
            core_schema_id="core_schema_1",
            program_schema_id="program_schema_1",
            status="processing",
            created_at="2024-01-01T00:00:00Z",
        )
        await saver.save_job(job)

        job_results = JobResults(
            storage_type="s3",
            location="path/to/results.json",
            bucket="test-bucket",
        )
        version = 1

        await saver.add_job_results(job_id, version, job_results)

        saver._add_job_results_mock.assert_called_once_with(job_id, version, job_results)

        updated_job = await saver.get_job(job_id)
        assert "1" in updated_job.results
        assert updated_job.results["1"] == job_results

    @pytest.mark.asyncio
    async def test_increment_job_version_interface(self):
        """Test increment_job_version method interface contract."""
        saver = MockJobStatusSaver()

        job_id = "test_job_123"
        job = MetadataUploadJob(
            job_id=job_id,
            user_id="user_456",
            core_schema_id="core_schema_1",
            program_schema_id="program_schema_1",
            status="completed",
            created_at="2024-01-01T00:00:00Z",
            current_version=1,
        )
        await saver.save_job(job)

        new_version = await saver.increment_job_version(job_id)

        assert new_version == 2

        updated_job = await saver.get_job(job_id)
        assert updated_job.current_version == 2

    @pytest.mark.asyncio
    async def test_method_signatures(self):
        """Test that all methods have correct signatures."""
        saver = MockJobStatusSaver()

        job = MetadataUploadJob(
            job_id="job_id",
            user_id="user_id",
            core_schema_id="core_schema_id",
            program_schema_id="program_schema_id",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
        )
        await saver.save_job(job)

        result = await saver.get_job("job_id")
        assert result is None or isinstance(result, MetadataUploadJob)

        await saver.update_job_status("job_id", "completed")

        job_results = JobResults(storage_type="local", location="/path/to/results.json")
        await saver.add_job_results("job_id", 1, job_results)

        version = await saver.increment_job_version("job_id")
        assert isinstance(version, int)

    def test_concrete_implementation_requirements(self):
        """Test that concrete implementations must implement all methods."""

        class IncompleteImplementation(JobStatusSaver):
            """Incomplete implementation missing required methods."""

            async def save_job(self, job: MetadataUploadJob) -> None:
                pass

            async def get_job(self, job_id: str) -> MetadataUploadJob | None:
                pass

        with pytest.raises(TypeError):
            IncompleteImplementation()

    @pytest.mark.asyncio
    async def test_error_handling_contract(self):
        """Test that implementations can raise exceptions as documented."""

        class ErrorRaisingImplementation(JobStatusSaver):
            """Implementation that raises exceptions for testing."""

            async def save_job(self, job: MetadataUploadJob) -> None:
                raise Exception("Save failed")

            async def get_job(self, job_id: str) -> MetadataUploadJob | None:
                raise Exception("Get failed")

            async def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
                raise Exception("Update failed")

            async def add_job_results(self, job_id: str, version: int, job_results: JobResults) -> None:
                raise Exception("Add results failed")

            async def increment_job_version(self, job_id: str) -> int:
                raise Exception("Increment failed")

        saver = ErrorRaisingImplementation()

        job = MetadataUploadJob(
            job_id="job_id",
            user_id="user_id",
            core_schema_id="core_schema_id",
            program_schema_id="program_schema_id",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
        )

        with pytest.raises(Exception, match="Save failed"):
            await saver.save_job(job)

        with pytest.raises(Exception, match="Get failed"):
            await saver.get_job("job_id")

        with pytest.raises(Exception, match="Update failed"):
            await saver.update_job_status("job_id", "completed")

        job_results = JobResults(storage_type="local", location="/path/to/results.json")
        with pytest.raises(Exception, match="Add results failed"):
            await saver.add_job_results("job_id", 1, job_results)

        with pytest.raises(Exception, match="Increment failed"):
            await saver.increment_job_version("job_id")
