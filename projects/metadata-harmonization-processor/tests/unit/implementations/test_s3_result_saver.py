# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for S3ResultSaver implementation.

Tests S3 operations using mocked boto3 client to verify proper
error handling, multipart uploads, and result storage/retrieval.
"""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from metadata_harmonization_processor.implementations.s3_result_saver import (
    S3ResultSaver,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.job import JobResults
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


@pytest.fixture
def sample_validation_results():
    """Create sample ValidationResults for testing."""
    return ValidationResults(
        validationResults=[
            ValidationErrorDetail(
                row=1,
                column="test_column",
                currentValue="invalid_value",
                validOptions=["option1", "option2"],
                recommendedValue="option1",
                errorType=ValidationErrorType.INVALID_OPTION,
            )
        ],
        summary=ValidationResultsSummary(
            totalRows=10,
            totalErrors=1,
            errorTypes={ValidationErrorType.INVALID_OPTION: 1},
            columnsValidated=1,
        ),
    )


@pytest.fixture
def sample_combined_results(sample_validation_results):
    """Create sample CombinedResults for testing."""
    return CombinedResults(
        validation_results=sample_validation_results,
        schema_alignment_results=None,
    )


@pytest.fixture
def mock_s3_client():
    """Create a mocked S3 client."""
    with patch("boto3.client") as mock_boto3:
        mock_client = Mock()
        mock_boto3.return_value = mock_client

        # Mock successful head_bucket for credential validation
        mock_client.head_bucket.return_value = {}

        yield mock_client


class TestS3ResultSaverInitialization:
    """Test S3ResultSaver initialization and configuration."""

    def test_init_success(self, mock_s3_client):
        """Test successful initialization with valid parameters."""
        saver = S3ResultSaver(bucket_name="test-bucket", key_prefix="results/", region="us-west-2")

        assert saver.bucket_name == "test-bucket"
        assert saver.key_prefix == "results/"
        assert saver.region == "us-west-2"
        assert saver.multipart_threshold == 100 * 1024 * 1024

        # Verify S3 client was created and bucket access was verified
        mock_s3_client.head_bucket.assert_called_once_with(Bucket="test-bucket")

    def test_init_adds_trailing_slash_to_prefix(self, mock_s3_client):
        """Test that trailing slash is added to key_prefix if missing."""
        saver = S3ResultSaver(
            bucket_name="test-bucket",
            key_prefix="results",  # No trailing slash
        )

        assert saver.key_prefix == "results/"

    def test_init_empty_bucket_name_raises_error(self, mock_s3_client):
        """Test that empty bucket_name raises ValueError."""
        with pytest.raises(ValueError, match="bucket_name cannot be empty"):
            S3ResultSaver(bucket_name="")

    def test_init_no_credentials_raises_error(self):
        """Test that missing AWS credentials raises NoCredentialsError."""
        with patch("boto3.client") as mock_boto3:
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            mock_client.head_bucket.side_effect = NoCredentialsError()

            with pytest.raises(NoCredentialsError):
                S3ResultSaver(bucket_name="test-bucket")

    def test_init_client_error_raises_error(self):
        """Test that S3 client errors during initialization are raised."""
        with patch("boto3.client") as mock_boto3:
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            mock_client.head_bucket.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "HeadBucket")

            with pytest.raises(ClientError):
                S3ResultSaver(bucket_name="test-bucket")


class TestS3ResultSaverSaveResults:
    """Test save_results method."""

    @pytest.mark.asyncio
    async def test_save_results_success(self, mock_s3_client, sample_combined_results):
        """Test successful save_results operation."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock successful put_object
        mock_s3_client.put_object.return_value = {"ETag": '"test-etag"'}

        result = await saver.save_results(
            job_id="test-job-123",
            version=1,
            combined_results=sample_combined_results,
            metadata={"test": "metadata"},
        )

        # Verify JobResults
        assert isinstance(result, JobResults)
        assert result.storage_type == "s3"
        assert result.location == "validation-results/test-job-123/v1/results.json"
        assert result.bucket == "test-bucket"

        # Verify S3 put_object was called correctly
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args

        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == "validation-results/test-job-123/v1/results.json"
        assert call_args[1]["ContentType"] == "application/json"

        # Verify JSON content structure
        body_data = json.loads(call_args[1]["Body"].decode("utf-8"))
        assert body_data["job_id"] == "test-job-123"
        assert body_data["version"] == 1
        assert "timestamp" in body_data
        assert "combined_results" in body_data
        assert body_data["metadata"] == {"test": "metadata"}

    @pytest.mark.asyncio
    async def test_save_results_empty_job_id_raises_error(self, mock_s3_client, sample_combined_results):
        """Test that empty job_id raises ValueError."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        with pytest.raises(ValueError, match="job_id cannot be empty"):
            await saver.save_results(job_id="", version=1, combined_results=sample_combined_results)

    @pytest.mark.asyncio
    async def test_save_results_invalid_version_raises_error(self, mock_s3_client, sample_combined_results):
        """Test that invalid version raises ValueError."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        with pytest.raises(ValueError, match="version must be >= 1"):
            await saver.save_results(
                job_id="test-job",
                version=0,
                combined_results=sample_combined_results,
            )

    @pytest.mark.asyncio
    async def test_save_results_s3_error_raises_client_error(self, mock_s3_client, sample_combined_results):
        """Test that S3 errors are properly raised."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock S3 error
        mock_s3_client.put_object.side_effect = ClientError({"Error": {"Code": "NoSuchBucket"}}, "PutObject")

        with pytest.raises(ClientError):
            await saver.save_results(
                job_id="test-job",
                version=1,
                combined_results=sample_combined_results,
            )

    @pytest.mark.asyncio
    async def test_save_results_large_file_uses_multipart(self, mock_s3_client, sample_combined_results):
        """Test that large files trigger multipart upload."""
        # Set low threshold for testing
        saver = S3ResultSaver(bucket_name="test-bucket", multipart_threshold=100)

        # Mock multipart upload methods
        mock_s3_client.create_multipart_upload.return_value = {"UploadId": "test-upload-id"}
        mock_s3_client.upload_part.return_value = {"ETag": '"part-etag"'}
        mock_s3_client.complete_multipart_upload.return_value = {}

        await saver.save_results(
            job_id="test-job",
            version=1,
            combined_results=sample_combined_results,
        )

        # Verify multipart upload was used
        mock_s3_client.create_multipart_upload.assert_called_once()
        mock_s3_client.upload_part.assert_called()
        mock_s3_client.complete_multipart_upload.assert_called_once()

        # Verify regular put_object was not called
        mock_s3_client.put_object.assert_not_called()

    @pytest.mark.asyncio
    async def test_multipart_upload_failure_aborts_upload(self, mock_s3_client, sample_combined_results):
        """Test that multipart upload failures trigger abort."""
        saver = S3ResultSaver(bucket_name="test-bucket", multipart_threshold=100)

        # Mock multipart upload failure
        mock_s3_client.create_multipart_upload.return_value = {"UploadId": "test-upload-id"}
        mock_s3_client.upload_part.side_effect = ClientError({"Error": {"Code": "InternalError"}}, "UploadPart")
        mock_s3_client.abort_multipart_upload.return_value = {}

        with pytest.raises(ClientError):
            await saver.save_results(
                job_id="test-job",
                version=1,
                combined_results=sample_combined_results,
            )

        # Verify abort was called
        mock_s3_client.abort_multipart_upload.assert_called_once_with(
            Bucket="test-bucket",
            Key="validation-results/test-job/v1/results.json",
            UploadId="test-upload-id",
        )


class TestS3ResultSaverGetResults:
    """Test get_results method."""

    @pytest.mark.asyncio
    async def test_get_results_success(self, mock_s3_client, sample_combined_results):
        """Test successful get_results operation."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Prepare mock S3 response with CombinedResults
        storage_data = {
            "job_id": "test-job",
            "version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "combined_results": sample_combined_results.to_dict(),
            "metadata": {},
        }

        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = json.dumps(storage_data).encode("utf-8")
        mock_s3_client.get_object.return_value = mock_response

        job_results = JobResults(
            storage_type="s3",
            location="validation-results/test-job/v1/results.json",
            bucket="test-bucket",
        )

        combined_result = await saver.get_results(job_results)

        # Verify result is CombinedResults instance
        assert isinstance(combined_result, CombinedResults)
        assert combined_result.has_validation_results()
        assert combined_result.validation_results.summary.total_errors == 1

        # Verify S3 get_object was called correctly
        mock_s3_client.get_object.assert_called_once()
        call_args = mock_s3_client.get_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == "validation-results/test-job/v1/results.json"

    @pytest.mark.asyncio
    async def test_get_results_wrong_storage_type_raises_error(self, mock_s3_client):
        """Test that wrong storage type raises ValueError."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        job_results = JobResults(storage_type="local", location="/path/to/file.json")

        with pytest.raises(ValueError, match="Expected S3 storage type, got: local"):
            await saver.get_results(job_results)

    @pytest.mark.asyncio
    async def test_get_results_missing_bucket_raises_error(self, mock_s3_client):
        """Test that missing bucket raises ValueError."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Create JobResults with local storage type first, then modify
        # to test validation
        job_results = JobResults(
            storage_type="local",
            location="validation-results/test-job/v1/results.json",
        )
        # Manually set storage_type to bypass Pydantic validation for testing
        job_results.storage_type = "s3"
        job_results.bucket = None

        with pytest.raises(ValueError, match="bucket is required for S3 storage type"):
            await saver.get_results(job_results)

    @pytest.mark.asyncio
    async def test_get_results_not_found_returns_none(self, mock_s3_client):
        """Test that missing S3 object returns None."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock NoSuchKey error
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

        job_results = JobResults(
            storage_type="s3",
            location="validation-results/test-job/v1/results.json",
            bucket="test-bucket",
        )

        result = await saver.get_results(job_results)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_results_s3_error_raises_client_error(self, mock_s3_client):
        """Test that S3 errors (other than NoSuchKey) are raised."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock S3 error
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")

        job_results = JobResults(
            storage_type="s3",
            location="validation-results/test-job/v1/results.json",
            bucket="test-bucket",
        )

        with pytest.raises(ClientError):
            await saver.get_results(job_results)

    @pytest.mark.asyncio
    async def test_get_results_invalid_json_raises_error(self, mock_s3_client):
        """Test that invalid JSON raises JSONDecodeError."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock response with invalid JSON
        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = b"invalid json content"
        mock_s3_client.get_object.return_value = mock_response

        job_results = JobResults(
            storage_type="s3",
            location="validation-results/test-job/v1/results.json",
            bucket="test-bucket",
        )

        with pytest.raises(json.JSONDecodeError):
            await saver.get_results(job_results)


class TestS3ResultSaverListResults:
    """Test list_results method."""

    @pytest.mark.asyncio
    async def test_list_results_success(self, mock_s3_client):
        """Test successful list_results operation."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock S3 list_objects_v2 paginator
        mock_paginator = Mock()
        mock_s3_client.get_paginator.return_value = mock_paginator

        # Mock page iterator with test objects
        mock_page_iterator = [
            {
                "Contents": [
                    {"Key": "validation-results/test-job/v1/results.json"},
                    {"Key": "validation-results/test-job/v2/results.json"},
                    {"Key": "validation-results/test-job/v3/results.json"},
                    {"Key": "validation-results/test-job/other-file.txt"},  # Should be ignored
                ]
            }
        ]
        mock_paginator.paginate.return_value = mock_page_iterator

        result = await saver.list_results("test-job")

        # Verify results
        assert len(result) == 3
        assert all(isinstance(r, JobResults) for r in result)
        assert all(r.storage_type == "s3" for r in result)
        assert all(r.bucket == "test-bucket" for r in result)

        # Verify results are sorted by version and contain full paths to results.json
        expected_locations = [
            "validation-results/test-job/v1/results.json",
            "validation-results/test-job/v2/results.json",
            "validation-results/test-job/v3/results.json",
        ]
        actual_locations = [r.location for r in result]
        assert actual_locations == expected_locations

        # Verify S3 paginator was called correctly
        mock_s3_client.get_paginator.assert_called_once_with("list_objects_v2")
        mock_paginator.paginate.assert_called_once_with(Bucket="test-bucket", Prefix="validation-results/test-job/")

    @pytest.mark.asyncio
    async def test_list_results_empty_job_id_raises_error(self, mock_s3_client):
        """Test that empty job_id raises ValueError."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        with pytest.raises(ValueError, match="job_id cannot be empty"):
            await saver.list_results("")

    @pytest.mark.asyncio
    async def test_list_results_no_objects_returns_empty_list(self, mock_s3_client):
        """Test that no matching objects returns empty list."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock empty paginator response
        mock_paginator = Mock()
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{}]  # No 'Contents' key

        result = await saver.list_results("test-job")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_results_s3_error_raises_client_error(self, mock_s3_client):
        """Test that S3 errors are properly raised."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock S3 error
        mock_paginator = Mock()
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.side_effect = ClientError({"Error": {"Code": "NoSuchBucket"}}, "ListObjectsV2")

        with pytest.raises(ClientError):
            await saver.list_results("test-job")

    @pytest.mark.asyncio
    async def test_list_results_ignores_invalid_key_patterns(self, mock_s3_client):
        """Test that objects with invalid key patterns are ignored."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        # Mock paginator with mixed valid/invalid keys
        mock_paginator = Mock()
        mock_s3_client.get_paginator.return_value = mock_paginator

        mock_page_iterator = [
            {
                "Contents": [
                    {"Key": "validation-results/test-job/v1/results.json"},  # Valid
                    {"Key": "validation-results/test-job/invalid/results.json"},  # Invalid version
                    {"Key": "validation-results/test-job/v2/other.json"},  # Invalid filename
                    {"Key": "validation-results/test-job/v3/results.json"},  # Valid
                ]
            }
        ]
        mock_paginator.paginate.return_value = mock_page_iterator

        result = await saver.list_results("test-job")

        # Should only return valid results
        assert len(result) == 2
        expected_locations = [
            "validation-results/test-job/v1/results.json",
            "validation-results/test-job/v3/results.json",
        ]
        actual_locations = [r.location for r in result]
        assert actual_locations == expected_locations


class TestS3ResultSaverHelperMethods:
    """Test helper methods."""

    def test_generate_s3_key(self, mock_s3_client):
        """Test S3 key generation."""
        saver = S3ResultSaver(bucket_name="test-bucket", key_prefix="custom-prefix/")

        key = saver._generate_s3_key("test-job-123", 5, "results.json")

        assert key == "custom-prefix/test-job-123/v5/results.json"

    def test_generate_s3_key_default_prefix(self, mock_s3_client):
        """Test S3 key generation with default prefix."""
        saver = S3ResultSaver(bucket_name="test-bucket")

        key = saver._generate_s3_key("job-456", 1, "results.json")

        assert key == "validation-results/job-456/v1/results.json"
