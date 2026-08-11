# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for ResultSaver interface."""

from abc import ABC
from datetime import datetime
from typing import Any

import pytest

from metadata_harmonization_processor.interfaces.result_saver import ResultSaver
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.job import JobResults
from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResults,
    SchemaAlignmentResultsSummary,
)
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class MockResultSaver(ResultSaver):
    """Mock implementation of ResultSaver for testing."""

    def __init__(self):
        self.saved_combined_results: dict[str, dict[int, CombinedResults]] = {}
        self.saved_metadata: dict[str, dict[int, dict[str, Any]]] = {}
        self.job_results_store: dict[str, list[JobResults]] = {}

    async def save_results(
        self,
        job_id: str,
        version: int,
        combined_results: CombinedResults,
        metadata: dict[str, Any] | None = None,
    ) -> JobResults:
        """Mock save_results implementation using single results.json storage."""
        if job_id not in self.saved_combined_results:
            self.saved_combined_results[job_id] = {}
            self.saved_metadata[job_id] = {}
            self.job_results_store[job_id] = []

        self.saved_combined_results[job_id][version] = combined_results
        self.saved_metadata[job_id][version] = metadata or {}

        job_results = JobResults(
            storage_type="local",
            location=f"/tmp/results/{job_id}/v{version}/results.json",
        )

        self.job_results_store[job_id].append(job_results)
        return job_results

    async def get_results(self, job_results: JobResults) -> CombinedResults | None:
        """Mock get_results implementation returning single CombinedResults instance."""
        # Extract job_id and version from location path
        parts = job_results.location.split("/")
        if len(parts) >= 4:
            job_id = parts[-3]
            version_str = parts[-2]
            if version_str.startswith("v"):
                version = int(version_str[1:])
                return self.saved_combined_results.get(job_id, {}).get(version)
        return None

    async def list_results(self, job_id: str) -> list[JobResults]:
        """Mock list_results implementation."""
        return self.job_results_store.get(job_id, [])


class TestResultSaverInterface:
    """Test cases for ResultSaver interface contract."""

    @pytest.fixture
    def mock_result_saver(self):
        """Create mock ResultSaver instance."""
        return MockResultSaver()

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
    def sample_schema_alignment_results(self):
        """Create sample SchemaAlignmentResults for testing."""
        change_detail = SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="col1",
            new_column="aligned_col1",
            reason="Schema alignment mapping",
            row_count_affected=1,
        )

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-123",
            version=1,
            timestamp=datetime.utcnow(),
            original_data_csv="col1,col2\nval1,val2\n",
            aligned_data_csv="aligned_col1,aligned_col2\nval1,val2\n",
            total_changes=1,
            columns_renamed=1,
            columns_added=0,
            columns_removed=0,
            rows_original=1,
            rows_aligned=1,
        )

        return SchemaAlignmentResults(schema_alignment_results=[change_detail], summary=summary)

    @pytest.fixture
    def sample_combined_results(self, sample_validation_results, sample_schema_alignment_results):
        """Create sample CombinedResults for testing."""
        return CombinedResults(
            validation_results=sample_validation_results,
            schema_alignment_results=sample_schema_alignment_results,
        )

    @pytest.mark.asyncio
    async def test_save_results_interface(self, mock_result_saver, sample_combined_results):
        """Test that save_results returns JobResults with correct structure using single CombinedResults parameter."""
        job_id = "test-job-123"
        version = 1
        metadata = {"test": "metadata"}

        job_results = await mock_result_saver.save_results(
            job_id=job_id,
            version=version,
            combined_results=sample_combined_results,
            metadata=metadata,
        )

        # Verify JobResults structure
        assert isinstance(job_results, JobResults)
        assert job_results.storage_type in ["s3", "local"]
        assert job_results.location is not None
        assert len(job_results.location) > 0

        # For S3 storage type, bucket should be provided
        if job_results.storage_type == "s3":
            assert job_results.bucket is not None

    @pytest.mark.asyncio
    async def test_get_results_interface(self, mock_result_saver, sample_combined_results):
        """Test that get_results retrieves saved CombinedResults from single results.json file."""
        job_id = "test-job-456"
        version = 1

        # Save results first
        job_results = await mock_result_saver.save_results(
            job_id=job_id, version=version, combined_results=sample_combined_results
        )

        # Retrieve results
        retrieved_combined = await mock_result_saver.get_results(job_results)

        # Verify retrieved combined results match original
        assert retrieved_combined is not None
        assert isinstance(retrieved_combined, CombinedResults)

        # Verify validation results within combined results
        assert retrieved_combined.has_validation_results()
        retrieved_validation = retrieved_combined.validation_results
        assert len(retrieved_validation.validation_results) == len(
            sample_combined_results.validation_results.validation_results
        )
        assert retrieved_validation.summary.total_rows == sample_combined_results.validation_results.summary.total_rows

        # Verify schema alignment results within combined results
        assert retrieved_combined.has_schema_alignment_results()
        retrieved_schema_alignment = retrieved_combined.schema_alignment_results
        assert len(retrieved_schema_alignment.schema_alignment_results) == len(
            sample_combined_results.schema_alignment_results.schema_alignment_results
        )
        assert (
            retrieved_schema_alignment.summary.job_id == sample_combined_results.schema_alignment_results.summary.job_id
        )
        assert (
            retrieved_schema_alignment.summary.version
            == sample_combined_results.schema_alignment_results.summary.version
        )

    @pytest.mark.asyncio
    async def test_get_results_not_found(self, mock_result_saver):
        """Test that get_results returns None for non-existent results."""
        job_results = JobResults(storage_type="local", location="/tmp/nonexistent/results.json")

        retrieved_combined = await mock_result_saver.get_results(job_results)
        assert retrieved_combined is None

    @pytest.mark.asyncio
    async def test_list_results_interface(self, mock_result_saver, sample_combined_results):
        """Test that list_results returns all JobResults for a job."""
        job_id = "test-job-789"

        # Save multiple versions
        await mock_result_saver.save_results(job_id=job_id, version=1, combined_results=sample_combined_results)

        await mock_result_saver.save_results(job_id=job_id, version=2, combined_results=sample_combined_results)

        # List results
        all_results = await mock_result_saver.list_results(job_id)

        # Verify all versions are returned
        assert len(all_results) == 2
        assert all(isinstance(jr, JobResults) for jr in all_results)

        # Verify locations are different for different versions
        locations = [jr.location for jr in all_results]
        assert len(set(locations)) == 2  # All locations should be unique

    @pytest.mark.asyncio
    async def test_list_results_empty(self, mock_result_saver):
        """Test that list_results returns empty list for non-existent job."""
        all_results = await mock_result_saver.list_results("nonexistent-job")
        assert all_results == []

    @pytest.mark.asyncio
    async def test_save_results_with_metadata(self, mock_result_saver, sample_combined_results):
        """Test that save_results handles optional metadata parameter."""
        job_id = "test-job-metadata"
        version = 1
        metadata = {
            "program_id": "test-program",
            "core_id": "test-core",
            "processing_time": "2024-01-01T00:00:00Z",
        }

        job_results = await mock_result_saver.save_results(
            job_id=job_id,
            version=version,
            combined_results=sample_combined_results,
            metadata=metadata,
        )

        # Verify results were saved (implementation-specific verification)
        assert isinstance(job_results, JobResults)
        assert job_results.location is not None

    @pytest.mark.asyncio
    async def test_save_results_without_metadata(self, mock_result_saver, sample_validation_results):
        """Test that save_results works without metadata parameter."""
        job_id = "test-job-no-metadata"
        version = 1

        # Create combined results with only validation results
        combined_results = CombinedResults(validation_results=sample_validation_results, schema_alignment_results=None)

        job_results = await mock_result_saver.save_results(
            job_id=job_id, version=version, combined_results=combined_results
        )

        # Verify results were saved
        assert isinstance(job_results, JobResults)
        assert job_results.location is not None

    @pytest.mark.asyncio
    async def test_save_results_validation_only(self, mock_result_saver, sample_validation_results):
        """Test that save_results works with only validation results (no schema alignment)."""
        job_id = "test-job-validation-only"
        version = 1

        # Create combined results with only validation results
        combined_results = CombinedResults(validation_results=sample_validation_results, schema_alignment_results=None)

        job_results = await mock_result_saver.save_results(
            job_id=job_id, version=version, combined_results=combined_results
        )

        # Verify results were saved
        assert isinstance(job_results, JobResults)
        assert job_results.location is not None

        # Retrieve and verify only validation results exist
        retrieved_combined = await mock_result_saver.get_results(job_results)
        assert retrieved_combined is not None
        assert retrieved_combined.has_validation_results()
        assert not retrieved_combined.has_schema_alignment_results()
        assert retrieved_combined.validation_results is not None
        assert retrieved_combined.schema_alignment_results is None

    def test_result_saver_is_abstract(self):
        """Test that ResultSaver cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ResultSaver()

    def test_result_saver_inheritance(self):
        """Test that ResultSaver is properly defined as an abstract base class."""
        assert issubclass(ResultSaver, ABC)

        # Verify abstract methods are defined
        abstract_methods = ResultSaver.__abstractmethods__
        expected_methods = {"save_results", "get_results", "list_results"}
        assert abstract_methods == expected_methods

    @pytest.mark.asyncio
    async def test_combined_results_serialization(self, mock_result_saver, sample_combined_results):
        """Test that CombinedResults can be properly serialized and deserialized for single file storage."""
        job_id = "test-job-serialization"
        version = 1

        # Save combined results
        job_results = await mock_result_saver.save_results(
            job_id=job_id, version=version, combined_results=sample_combined_results
        )

        # Retrieve and verify serialization/deserialization works
        retrieved_combined = await mock_result_saver.get_results(job_results)

        # Test to_dict() method works
        combined_dict = sample_combined_results.to_dict()
        assert "validation_results" in combined_dict
        assert "schema_alignment_results" in combined_dict

        # Test from_dict() method works
        reconstructed_combined = CombinedResults.from_dict(combined_dict)
        assert reconstructed_combined.has_validation_results()
        assert reconstructed_combined.has_schema_alignment_results()

        # Verify data integrity after round-trip
        assert retrieved_combined.has_validation_results() == sample_combined_results.has_validation_results()
        assert (
            retrieved_combined.has_schema_alignment_results() == sample_combined_results.has_schema_alignment_results()
        )
