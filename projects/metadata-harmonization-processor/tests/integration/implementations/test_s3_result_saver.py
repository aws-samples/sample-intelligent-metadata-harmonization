# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Integration tests for S3ResultSaver implementation.

Tests S3 operations using actual AWS S3 service to verify end-to-end
functionality with combined ValidationResults and SchemaAlignmentResults.
Requires AWS credentials and S3 bucket access.
"""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
import pytest

from metadata_harmonization_processor.implementations.s3_result_saver import (
    S3ResultSaver,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.job import JobResults
from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentResults,
)
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)

# Skip integration tests if AWS credentials are not available
pytest_plugins = []

try:
    # Test AWS credentials and bucket availability
    _s3_client = boto3.client("s3")
    _test_bucket = os.environ.get("TEST_S3_BUCKET", "metadata-processor-test-bucket")
    _s3_client.head_bucket(Bucket=_test_bucket)
    AWS_AVAILABLE = True
except Exception:
    AWS_AVAILABLE = False


@pytest.fixture
def test_bucket_name():
    """Get test bucket name from environment or use default."""
    return os.getenv("TEST_S3_BUCKET", "metadata-processor-test-bucket")


@pytest.fixture
def test_key_prefix():
    """Generate unique key prefix for test isolation."""
    return f"integration-tests/{uuid.uuid4()}/"


@pytest.fixture
def sample_validation_results():
    """Create sample ValidationResults for testing."""
    return ValidationResults(
        validationResults=[
            ValidationErrorDetail(
                row=0,
                column="test_column",
                currentValue="invalid_value",
                validOptions=["option1", "option2"],
                recommendedValue="option1",
                errorType=ValidationErrorType.INVALID_OPTION,
            ),
            ValidationErrorDetail(
                row=1,
                column="another_column",
                currentValue="",
                validOptions=None,
                recommendedValue="required_value",
                errorType=ValidationErrorType.REQUIRED_VALUE,
            ),
        ],
        summary=ValidationResultsSummary(
            totalRows=100,
            totalErrors=2,
            errorTypes={
                ValidationErrorType.INVALID_OPTION: 1,
                ValidationErrorType.REQUIRED_VALUE: 1,
            },
        ),
    )


@pytest.fixture
def sample_schema_alignment_results():
    """Create sample SchemaAlignmentResults for testing with new structure."""
    from metadata_harmonization_processor.models.schema_alignment_results import (
        SchemaAlignmentChangeDetail,
        SchemaAlignmentResultsSummary,
    )

    # Create change details
    change_details = [
        SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="col1",
            new_column="aligned_col1",
            reason="Schema alignment for standardization",
            row_count_affected=2,
        ),
        SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="col2",
            new_column="aligned_col2",
            reason="Schema alignment for standardization",
            row_count_affected=2,
        ),
    ]

    # Create summary
    summary = SchemaAlignmentResultsSummary(
        job_id="test-job-123",
        version=1,
        timestamp=datetime.now(timezone.utc),
        original_data_csv="col1,col2\nval1,val2\nval3,val4\n",
        aligned_data_csv="aligned_col1,aligned_col2\nval1,val2\nval3,val4\n",
        total_changes=2,
        columns_renamed=2,
        columns_added=0,
        columns_removed=0,
        rows_original=2,
        rows_aligned=2,
    )

    return SchemaAlignmentResults(schema_alignment_results=change_details, summary=summary)


@pytest.fixture
def sample_combined_results(sample_validation_results, sample_schema_alignment_results):
    """Create sample CombinedResults for testing."""
    return CombinedResults(
        validation_results=sample_validation_results,
        schema_alignment_results=sample_schema_alignment_results,
    )


@pytest.fixture
def s3_result_saver(test_bucket_name, test_key_prefix):
    """Create S3ResultSaver instance for testing."""
    return S3ResultSaver(bucket_name=test_bucket_name, key_prefix=test_key_prefix, region="us-east-1")


@pytest.fixture
def cleanup_s3_objects(test_bucket_name, test_key_prefix):
    """Cleanup S3 objects after tests."""
    created_keys = []

    yield created_keys

    # Cleanup after test
    if AWS_AVAILABLE and created_keys:
        s3_client = boto3.client("s3")
        try:
            # Delete all created objects
            delete_objects = [{"Key": key} for key in created_keys]
            if delete_objects:
                s3_client.delete_objects(Bucket=test_bucket_name, Delete={"Objects": delete_objects})
        except Exception as e:
            print(f"Warning: Failed to cleanup S3 objects: {e}")


@pytest.mark.skipif(not AWS_AVAILABLE, reason="AWS credentials not available")
class TestS3ResultSaverIntegration:
    """Integration tests for S3ResultSaver with actual S3 service."""

    @pytest.mark.asyncio
    async def test_save_and_get_results_roundtrip(self, s3_result_saver, sample_combined_results, cleanup_s3_objects):
        """Test complete save and retrieve cycle with actual S3 using single results.json storage."""
        job_id = f"test-job-{uuid.uuid4()}"
        version = 1
        metadata = {
            "test_metadata": "integration_test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Update schema alignment results with correct job_id and version
        sample_combined_results.schema_alignment_results.summary.job_id = job_id
        sample_combined_results.schema_alignment_results.summary.version = version

        # Save combined results using single file approach
        job_results = await s3_result_saver.save_results(
            job_id=job_id,
            version=version,
            combined_results=sample_combined_results,
            metadata=metadata,
        )

        # Track for cleanup - only single results.json file
        cleanup_s3_objects.append(job_results.location)

        # Verify JobResults structure
        assert isinstance(job_results, JobResults)
        assert job_results.storage_type == "s3"
        assert job_results.bucket == s3_result_saver.bucket_name
        assert job_id in job_results.location
        assert f"v{version}" in job_results.location
        assert job_results.location.endswith("results.json")  # Should be file path

        # Retrieve results
        retrieved_combined = await s3_result_saver.get_results(job_results)

        # Verify retrieved combined results
        assert isinstance(retrieved_combined, CombinedResults)
        assert retrieved_combined.has_validation_results()
        assert retrieved_combined.has_schema_alignment_results()

        # Verify retrieved validation results match original
        retrieved_validation = retrieved_combined.validation_results
        original_validation = sample_combined_results.validation_results
        assert isinstance(retrieved_validation, ValidationResults)
        assert len(retrieved_validation.validation_results) == len(original_validation.validation_results)
        assert retrieved_validation.summary.total_rows == original_validation.summary.total_rows
        assert retrieved_validation.summary.total_errors == original_validation.summary.total_errors

        # Verify individual error details
        for original, retrieved in zip(
            original_validation.validation_results,
            retrieved_validation.validation_results,
        ):
            assert retrieved.row == original.row
            assert retrieved.column == original.column
            assert retrieved.current_value == original.current_value
            assert retrieved.error_type == original.error_type
            assert retrieved.recommended_value == original.recommended_value

        # Verify retrieved schema alignment results match original
        retrieved_schema_alignment = retrieved_combined.schema_alignment_results
        original_schema_alignment = sample_combined_results.schema_alignment_results
        assert isinstance(retrieved_schema_alignment, SchemaAlignmentResults)
        assert retrieved_schema_alignment.summary.job_id == original_schema_alignment.summary.job_id
        assert retrieved_schema_alignment.summary.version == original_schema_alignment.summary.version
        assert (
            retrieved_schema_alignment.summary.original_data_csv == original_schema_alignment.summary.original_data_csv
        )
        assert retrieved_schema_alignment.summary.aligned_data_csv == original_schema_alignment.summary.aligned_data_csv

        # Verify change details
        assert len(retrieved_schema_alignment.schema_alignment_results) == len(
            original_schema_alignment.schema_alignment_results
        )
        for original_change, retrieved_change in zip(
            original_schema_alignment.schema_alignment_results,
            retrieved_schema_alignment.schema_alignment_results,
        ):
            assert retrieved_change.change_type == original_change.change_type
            assert retrieved_change.original_column == original_change.original_column
            assert retrieved_change.new_column == original_change.new_column
            assert retrieved_change.reason == original_change.reason
            assert retrieved_change.row_count_affected == original_change.row_count_affected

        # Verify summary statistics
        assert retrieved_schema_alignment.summary.total_changes == original_schema_alignment.summary.total_changes
        assert retrieved_schema_alignment.summary.columns_renamed == original_schema_alignment.summary.columns_renamed
        assert retrieved_schema_alignment.summary.columns_added == original_schema_alignment.summary.columns_added
        assert retrieved_schema_alignment.summary.columns_removed == original_schema_alignment.summary.columns_removed
        assert retrieved_schema_alignment.summary.rows_original == original_schema_alignment.summary.rows_original
        assert retrieved_schema_alignment.summary.rows_aligned == original_schema_alignment.summary.rows_aligned

    @pytest.mark.asyncio
    async def test_save_validation_only_results(self, s3_result_saver, sample_validation_results, cleanup_s3_objects):
        """Test saving validation results without schema alignment results using single file storage."""
        job_id = f"validation-only-{uuid.uuid4()}"
        version = 1

        # Create combined results with only validation results
        combined_results = CombinedResults(validation_results=sample_validation_results, schema_alignment_results=None)

        # Save validation results only
        job_results = await s3_result_saver.save_results(
            job_id=job_id, version=version, combined_results=combined_results
        )

        # Track for cleanup
        cleanup_s3_objects.append(job_results.location)

        # Retrieve results
        retrieved_combined = await s3_result_saver.get_results(job_results)

        # Verify combined results structure
        assert retrieved_combined is not None
        assert isinstance(retrieved_combined, CombinedResults)
        assert retrieved_combined.has_validation_results()
        assert not retrieved_combined.has_schema_alignment_results()

        # Verify validation results exist
        assert retrieved_combined.validation_results is not None
        assert isinstance(retrieved_combined.validation_results, ValidationResults)

        # Verify schema alignment results are None
        assert retrieved_combined.schema_alignment_results is None

    @pytest.mark.asyncio
    async def test_save_multiple_versions_and_list(self, s3_result_saver, sample_combined_results, cleanup_s3_objects):
        """Test saving multiple versions and listing them."""
        job_id = f"test-job-{uuid.uuid4()}"

        # Save multiple versions
        saved_results = []
        for version in [1, 2, 3]:
            # Update schema alignment results for each version
            sample_combined_results.schema_alignment_results.summary.job_id = job_id
            sample_combined_results.schema_alignment_results.summary.version = version

            job_results = await s3_result_saver.save_results(
                job_id=job_id,
                version=version,
                combined_results=sample_combined_results,
                metadata={"version": version},
            )
            saved_results.append(job_results)

            # Track for cleanup - only single results.json file
            cleanup_s3_objects.append(job_results.location)

        # List results
        listed_results = await s3_result_saver.list_results(job_id)

        # Verify all versions are listed
        assert len(listed_results) == 3

        # Verify results are sorted by version
        for i, result in enumerate(listed_results):
            expected_version = i + 1
            assert f"v{expected_version}" in result.location
            assert result.storage_type == "s3"
            assert result.bucket == s3_result_saver.bucket_name

    @pytest.mark.asyncio
    async def test_get_nonexistent_results_returns_none(self, s3_result_saver):
        """Test that retrieving nonexistent results returns None."""
        nonexistent_job_results = JobResults(
            storage_type="s3",
            location=f"{s3_result_saver.key_prefix}nonexistent-job/v1/results.json",
            bucket=s3_result_saver.bucket_name,
        )

        result = await s3_result_saver.get_results(nonexistent_job_results)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_nonexistent_job_returns_empty_list(self, s3_result_saver):
        """Test that listing nonexistent job returns empty list."""
        nonexistent_job_id = f"nonexistent-job-{uuid.uuid4()}"

        results = await s3_result_saver.list_results(nonexistent_job_id)
        assert results == []

    @pytest.mark.asyncio
    async def test_large_results_multipart_upload(self, test_bucket_name, test_key_prefix, cleanup_s3_objects):
        """Test multipart upload with large results."""
        # Create saver with low multipart threshold for testing
        saver = S3ResultSaver(
            bucket_name=test_bucket_name,
            key_prefix=test_key_prefix,
            multipart_threshold=1024,  # 1KB threshold for testing
        )

        # Create large validation results
        large_errors = []
        for i in range(1000):  # Create many errors to exceed threshold
            large_errors.append(
                ValidationErrorDetail(
                    row=i + 1,
                    column=f"column_{i}",
                    current_value=f"invalid_value_{i}" * 10,
                    valid_options=[f"option_{j}" for j in range(10)],
                    recommended_value=f"recommended_{i}",
                    error_type=ValidationErrorType.INVALID_OPTION,
                )
            )

        large_results = ValidationResults(
            validation_results=large_errors,
            summary=ValidationResultsSummary(
                total_rows=1000,
                total_errors=len(large_errors),
                error_types={ValidationErrorType.INVALID_OPTION: len(large_errors)},
                columns_validated=0,
            ),
        )

        job_id = f"large-job-{uuid.uuid4()}"

        # Create combined results with large validation results
        large_combined_results = CombinedResults(validation_results=large_results, schema_alignment_results=None)

        # Save large results (should trigger multipart upload)
        job_results = await saver.save_results(job_id=job_id, version=1, combined_results=large_combined_results)

        cleanup_s3_objects.append(job_results.location)

        # Verify results were saved successfully
        assert isinstance(job_results, JobResults)
        assert job_results.storage_type == "s3"

        # Retrieve and verify
        retrieved_combined = await saver.get_results(job_results)
        assert isinstance(retrieved_combined, CombinedResults)
        assert retrieved_combined.has_validation_results()
        assert not retrieved_combined.has_schema_alignment_results()
        assert len(retrieved_combined.validation_results.validation_results) == len(large_results.validation_results)

    @pytest.mark.asyncio
    async def test_concurrent_saves_different_jobs(
        self, s3_result_saver, sample_validation_results, cleanup_s3_objects
    ):
        """Test concurrent saves for different jobs."""
        import asyncio

        async def save_job_results(job_suffix):
            job_id = f"concurrent-job-{job_suffix}"
            return await s3_result_saver.save_results(
                job_id=job_id,
                version=1,
                validation_results=sample_validation_results,
                metadata={"job_suffix": job_suffix},
            )

        # Save multiple jobs concurrently
        tasks = [save_job_results(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Track for cleanup
        for result in results:
            cleanup_s3_objects.append(f"{result.location}results.json")

        # Verify all saves succeeded
        assert len(results) == 5
        for i, result in enumerate(results):
            assert isinstance(result, JobResults)
            assert f"concurrent-job-{i}" in result.location

    def test_error_handling_invalid_bucket(self, test_key_prefix):
        """Test error handling with invalid bucket name."""
        # S3ResultSaver validates bucket access on init, so it should raise
        with pytest.raises(Exception):
            S3ResultSaver(bucket_name="nonexistent-bucket-12345", key_prefix=test_key_prefix)

    @pytest.mark.asyncio
    async def test_s3_object_metadata_and_content_type(
        self, s3_result_saver, sample_validation_results, cleanup_s3_objects
    ):
        """Test that S3 objects have correct metadata and content type."""
        job_id = f"metadata-test-{uuid.uuid4()}"

        # Create combined results
        combined_results = CombinedResults(validation_results=sample_validation_results, schema_alignment_results=None)

        # Save results
        job_results = await s3_result_saver.save_results(job_id=job_id, version=1, combined_results=combined_results)

        results_key = job_results.location
        cleanup_s3_objects.append(results_key)

        # Check S3 object metadata directly
        s3_client = boto3.client("s3")
        response = s3_client.head_object(Bucket=job_results.bucket, Key=results_key)

        # Verify content type
        assert response["ContentType"] == "application/json"

        # Verify custom metadata
        metadata = response.get("Metadata", {})
        assert metadata.get("job-id") == job_id
        assert metadata.get("version") == "1"
        assert metadata.get("content-type") == "combined-results"

    @pytest.mark.asyncio
    async def test_new_schema_alignment_storage_format(
        self,
        s3_result_saver,
        sample_validation_results,
        sample_schema_alignment_results,
        cleanup_s3_objects,
    ):
        """Test that new SchemaAlignmentResults structure is stored correctly."""
        job_id = f"new-format-test-{uuid.uuid4()}"
        version = 1

        # Update schema alignment results with correct job_id and version
        sample_schema_alignment_results.summary.job_id = job_id
        sample_schema_alignment_results.summary.version = version

        # Create combined results
        combined_results = CombinedResults(
            validation_results=sample_validation_results,
            schema_alignment_results=sample_schema_alignment_results,
        )

        # Save combined results
        job_results = await s3_result_saver.save_results(
            job_id=job_id, version=version, combined_results=combined_results
        )

        # Track for cleanup
        cleanup_s3_objects.append(job_results.location)

        # Verify results file exists in S3 with correct structure
        s3_client = boto3.client("s3")

        # Check results.json exists and has correct structure
        results_response = s3_client.get_object(Bucket=job_results.bucket, Key=job_results.location)
        results_data = json.loads(results_response["Body"].read().decode("utf-8"))

        assert "combined_results" in results_data
        combined_data = results_data["combined_results"]

        assert "validation_results" in combined_data
        assert "schema_alignment_results" in combined_data

        # Verify schema alignment results structure
        schema_alignment_data = combined_data["schema_alignment_results"]
        assert "schema_alignment_results" in schema_alignment_data
        assert "summary" in schema_alignment_data

        # Verify change details
        change_details = schema_alignment_data["schema_alignment_results"]
        assert isinstance(change_details, list)
        assert len(change_details) == 2  # Two rename changes
        for change in change_details:
            assert "change_type" in change
            assert "original_column" in change
            assert "new_column" in change
            assert "reason" in change
            assert "row_count_affected" in change

        # Verify summary structure
        summary_data = schema_alignment_data["summary"]
        assert "job_id" in summary_data
        assert "version" in summary_data
        assert "timestamp" in summary_data
        assert "original_data_csv" in summary_data
        assert "aligned_data_csv" in summary_data
        assert "total_changes" in summary_data
        assert "columns_renamed" in summary_data
        assert "columns_added" in summary_data
        assert "columns_removed" in summary_data
        assert "rows_original" in summary_data
        assert "rows_aligned" in summary_data

        # Retrieve and verify results can be reconstructed
        retrieved_combined = await s3_result_saver.get_results(job_results)

        assert retrieved_combined is not None
        assert retrieved_combined.has_validation_results()
        assert retrieved_combined.has_schema_alignment_results()
        assert len(retrieved_combined.schema_alignment_results.schema_alignment_results) == 2
        assert retrieved_combined.schema_alignment_results.summary.total_changes == 2
        assert retrieved_combined.schema_alignment_results.summary.columns_renamed == 2
