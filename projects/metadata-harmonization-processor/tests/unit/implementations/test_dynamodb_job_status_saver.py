# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for DynamoDB JobStatusSaver implementation using Pydantic models."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from metadata_harmonization_processor.implementations.dynamodb_job_status_saver import (
    DynamodbJobStatusSaver,
)
from metadata_harmonization_processor.models.job import JobResults, MetadataUploadJob


class TestDynamodbJobStatusSaver:
    """Test cases for DynamodbJobStatusSaver class."""

    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table for testing."""
        with patch("boto3.resource") as mock_resource:
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_resource.return_value = mock_dynamodb
            yield mock_table

    @pytest.fixture
    def job_status_saver(self, mock_dynamodb_table):
        """Create DynamodbJobStatusSaver instance for testing."""
        return DynamodbJobStatusSaver(
            table_name="test-job-status-table",
            region="us-east-1",
            max_retries=2,
            timeout_seconds=10,
        )

    @pytest.fixture
    def sample_job(self):
        """Sample MetadataUploadJob for testing."""
        return MetadataUploadJob(
            job_id="job123",
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
            storage_type="s3",
            location="validation-results/job123/v1/results.json",
            bucket="test-results-bucket",
        )

    @pytest.mark.asyncio
    async def test_save_job_success(self, job_status_saver, mock_dynamodb_table, sample_job):
        """Test saving a complete job successfully."""
        mock_dynamodb_table.put_item.return_value = {}

        await job_status_saver.save_job(sample_job)

        # Verify put_item was called
        mock_dynamodb_table.put_item.assert_called_once()
        call_args = mock_dynamodb_table.put_item.call_args[1]["Item"]

        assert call_args["job_id"] == "job123"
        assert call_args["user_id"] == "user456"
        assert call_args["status"] == "pending"
        assert call_args["core_schema_id"] == "core-schema-v1"
        assert call_args["program_schema_id"] == "program-schema-v1"

    @pytest.mark.asyncio
    async def test_save_job_with_results(self, job_status_saver, mock_dynamodb_table, sample_job, sample_job_results):
        """Test saving a job with results."""
        sample_job.results = {"1": sample_job_results}
        mock_dynamodb_table.put_item.return_value = {}

        await job_status_saver.save_job(sample_job)

        mock_dynamodb_table.put_item.assert_called_once()
        call_args = mock_dynamodb_table.put_item.call_args[1]["Item"]

        assert "results" in call_args
        assert "1" in call_args["results"]
        assert call_args["results"]["1"]["storage_type"] == "s3"
        assert call_args["results"]["1"]["bucket"] == "test-results-bucket"

    @pytest.mark.asyncio
    async def test_save_job_dynamodb_error(self, job_status_saver, mock_dynamodb_table, sample_job):
        """Test handling DynamoDB errors during save_job."""
        mock_dynamodb_table.put_item.side_effect = ClientError(
            error_response={"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
            operation_name="PutItem",
        )

        with pytest.raises(Exception) as exc_info:
            await job_status_saver.save_job(sample_job)

        assert "Failed to save job" in str(exc_info.value)
        assert "job123" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_job_existing(self, job_status_saver, mock_dynamodb_table, sample_job_results):
        """Test retrieving an existing job."""
        mock_response = {
            "Item": {
                "job_id": "job123",
                "user_id": "user456",
                "core_schema_id": "core-schema-v1",
                "program_schema_id": "program-schema-v1",
                "status": "completed",
                "created_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:30:00Z",
                "current_version": 1,
                "results": {
                    "1": {
                        "storage_type": "s3",
                        "location": "validation-results/job123/v1/results.json",
                        "bucket": "test-results-bucket",
                    }
                },
            }
        }
        mock_dynamodb_table.get_item.return_value = mock_response

        result = await job_status_saver.get_job("job123")

        assert result is not None
        assert isinstance(result, MetadataUploadJob)
        assert result.job_id == "job123"
        assert result.status == "completed"
        assert result.current_version == 1
        assert len(result.results) == 1
        assert isinstance(result.results["1"], JobResults)
        assert result.results["1"].storage_type == "s3"

        mock_dynamodb_table.get_item.assert_called_once_with(Key={"job_id": "job123"})

    @pytest.mark.asyncio
    async def test_get_job_nonexistent(self, job_status_saver, mock_dynamodb_table):
        """Test retrieving a non-existent job."""
        mock_dynamodb_table.get_item.return_value = {}  # No 'Item' key

        result = await job_status_saver.get_job("nonexistent")

        assert result is None
        mock_dynamodb_table.get_item.assert_called_once_with(Key={"job_id": "nonexistent"})

    @pytest.mark.asyncio
    async def test_get_job_dynamodb_error(self, job_status_saver, mock_dynamodb_table):
        """Test handling DynamoDB errors during get_job."""
        mock_dynamodb_table.get_item.side_effect = ClientError(
            error_response={"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
            operation_name="GetItem",
        )

        with pytest.raises(Exception) as exc_info:
            await job_status_saver.get_job("job123")

        assert "Failed to retrieve job" in str(exc_info.value)
        assert "job123" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_job_status_success(self, job_status_saver, mock_dynamodb_table):
        """Test updating job status successfully."""
        mock_dynamodb_table.update_item.return_value = {}

        await job_status_saver.update_job_status("job123", "completed", completed_at="2024-01-01T12:30:00Z")

        mock_dynamodb_table.update_item.assert_called_once()
        call_args = mock_dynamodb_table.update_item.call_args[1]

        assert call_args["Key"] == {"job_id": "job123"}
        assert call_args["ExpressionAttributeValues"][":status"] == "completed"
        assert call_args["ExpressionAttributeValues"][":completed_at"] == "2024-01-01T12:30:00Z"

    @pytest.mark.asyncio
    async def test_update_job_status_dynamodb_error(self, job_status_saver, mock_dynamodb_table):
        """Test handling DynamoDB errors during update_job_status."""
        mock_dynamodb_table.update_item.side_effect = ClientError(
            error_response={"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
            operation_name="UpdateItem",
        )

        with pytest.raises(Exception) as exc_info:
            await job_status_saver.update_job_status("job123", "completed")

        assert "Failed to update job status" in str(exc_info.value)
        assert "job123" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_job_results_success(self, job_status_saver, mock_dynamodb_table, sample_job_results):
        """Test adding job results successfully."""
        mock_dynamodb_table.update_item.return_value = {}

        await job_status_saver.add_job_results("job123", 1, sample_job_results)

        mock_dynamodb_table.update_item.assert_called_once()
        call_args = mock_dynamodb_table.update_item.call_args[1]

        assert call_args["Key"] == {"job_id": "job123"}
        assert call_args["ExpressionAttributeNames"]["#version"] == "1"
        results_data = call_args["ExpressionAttributeValues"][":results"]
        assert results_data["storage_type"] == "s3"
        assert results_data["bucket"] == "test-results-bucket"

    @pytest.mark.asyncio
    async def test_add_job_results_dynamodb_error(self, job_status_saver, mock_dynamodb_table, sample_job_results):
        """Test handling DynamoDB errors during add_job_results."""
        mock_dynamodb_table.update_item.side_effect = ClientError(
            error_response={"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
            operation_name="UpdateItem",
        )

        with pytest.raises(Exception) as exc_info:
            await job_status_saver.add_job_results("job123", 1, sample_job_results)

        assert "Failed to add results" in str(exc_info.value)
        assert "job123" in str(exc_info.value)
        assert "version: 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_boto_core_error_handling(self, job_status_saver, mock_dynamodb_table):
        """Test handling BotoCoreError exceptions."""
        mock_dynamodb_table.get_item.side_effect = BotoCoreError()

        with pytest.raises(Exception) as exc_info:
            await job_status_saver.get_job("job123")

        assert "Failed to retrieve job" in str(exc_info.value)

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        with patch("boto3.resource") as mock_resource:
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_resource.return_value = mock_dynamodb

            saver = DynamodbJobStatusSaver(
                table_name="custom-table",
                region="us-west-2",
                max_retries=5,
                timeout_seconds=60,
            )

            assert saver.table_name == "custom-table"
            assert saver.region == "us-west-2"
            assert saver.max_retries == 5

            # Verify boto3 resource was called with correct config
            mock_resource.assert_called_once()
            config_arg = mock_resource.call_args[1]["config"]
            assert config_arg.region_name == "us-west-2"
            assert config_arg.retries["max_attempts"] == 5
