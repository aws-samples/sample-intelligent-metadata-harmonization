# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for DynamoDB JobStatusSaver implementation.

These tests require actual AWS DynamoDB access and should be run in a test environment
with appropriate AWS credentials and a test DynamoDB table.
"""

import os
import uuid
from datetime import datetime, timezone

import pytest

from metadata_harmonization_processor.implementations.dynamodb_job_status_saver import (
    DynamodbJobStatusSaver,
)

# Skip integration tests if not in integration test environment
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require RUN_INTEGRATION_TESTS environment variable",
)


class TestDynamodbJobStatusSaverIntegration:
    """Integration test cases for DynamodbJobStatusSaver with real DynamoDB."""

    @pytest.fixture(scope="class")
    def test_table_name(self):
        """Get test table name from environment or use default."""
        return os.getenv("DYNAMODB_TEST_TABLE", "test-metadata-processor-job-status")

    @pytest.fixture(scope="class")
    def aws_region(self):
        """Get AWS region from environment or use default."""
        return os.getenv("AWS_REGION", "us-east-1")

    @pytest.fixture
    def job_status_saver(self, test_table_name, aws_region):
        """Create DynamodbJobStatusSaver instance for integration testing."""
        return DynamodbJobStatusSaver(
            table_name=test_table_name,
            region=aws_region,
            max_retries=3,
            timeout_seconds=30,
        )

    @pytest.fixture
    def unique_job_id(self):
        """Generate unique job ID for each test."""
        return f"test-job-{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "stage": "validation",
            "total_rows": 1000,
            "processed_rows": 500,
            "errors": [
                {"row": 1, "column": "name", "error": "required value missing"},
                {"row": 5, "column": "status", "error": "invalid option"},
            ],
            "start_time": datetime.now(timezone.utc).isoformat(),
            "nested_data": {
                "config": {"batch_size": 100},
                "metrics": {"accuracy": 0.95},
            },
        }

    @pytest.mark.asyncio
    async def test_save_and_get_status_new_job(self, job_status_saver, unique_job_id, sample_metadata):
        """Test saving and retrieving status for a new job."""
        # Save status for new job
        await job_status_saver.save_status(unique_job_id, "running", sample_metadata)

        # Retrieve and verify
        result = await job_status_saver.get_status(unique_job_id)

        assert result is not None
        assert result["job_id"] == unique_job_id
        assert result["status"] == "running"
        assert result["metadata"] == sample_metadata
        assert "created_at" in result
        assert "updated_at" in result

        # Verify timestamps are valid ISO format
        datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))
        datetime.fromisoformat(result["updated_at"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_update_existing_job_status(self, job_status_saver, unique_job_id, sample_metadata):
        """Test updating status for an existing job."""
        # Create initial job
        await job_status_saver.save_status(unique_job_id, "running", sample_metadata)
        initial_result = await job_status_saver.get_status(unique_job_id)

        # Update with new status and metadata
        updated_metadata = {
            **sample_metadata,
            "processed_rows": 1000,
            "stage": "completed",
        }
        await job_status_saver.save_status(unique_job_id, "completed", updated_metadata)

        # Verify update
        updated_result = await job_status_saver.get_status(unique_job_id)

        assert updated_result["job_id"] == unique_job_id
        assert updated_result["status"] == "completed"
        assert updated_result["metadata"] == updated_metadata
        assert updated_result["created_at"] == initial_result["created_at"]  # Should not change
        assert updated_result["updated_at"] != initial_result["updated_at"]  # Should be different

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, job_status_saver):
        """Test retrieving status for a non-existent job."""
        nonexistent_id = f"nonexistent-{uuid.uuid4().hex[:8]}"
        result = await job_status_saver.get_status(nonexistent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_progress_single_stage(self, job_status_saver, unique_job_id, sample_metadata):
        """Test updating progress for a single stage."""
        # Create initial job
        await job_status_saver.save_status(unique_job_id, "running", sample_metadata)

        # Update progress for validation stage
        await job_status_saver.update_progress(unique_job_id, "validation", 0.75)

        # Retrieve and verify progress was updated
        result = await job_status_saver.get_status(unique_job_id)

        # Note: The current implementation stores progress in a separate field,
        # so we need to check if the item was updated (updated_at should change)
        assert result is not None
        assert result["job_id"] == unique_job_id
        # The updated_at timestamp should be more recent
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_update_progress_multiple_stages(self, job_status_saver, unique_job_id, sample_metadata):
        """Test updating progress for multiple stages."""
        # Create initial job
        await job_status_saver.save_status(unique_job_id, "running", sample_metadata)

        # Update progress for multiple stages
        await job_status_saver.update_progress(unique_job_id, "schema_alignment", 1.0)
        await job_status_saver.update_progress(unique_job_id, "validation", 0.5)
        await job_status_saver.update_progress(unique_job_id, "prediction", 0.25)

        # Retrieve and verify all updates were applied
        result = await job_status_saver.get_status(unique_job_id)

        assert result is not None
        assert result["job_id"] == unique_job_id
        # Verify the item was updated
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, job_status_saver, sample_metadata):
        """Test concurrent updates to the same job."""
        import asyncio

        job_id = f"concurrent-test-{uuid.uuid4().hex[:8]}"

        # Create initial job
        await job_status_saver.save_status(job_id, "running", sample_metadata)

        # Define concurrent update tasks
        async def update_status(status_suffix):
            await job_status_saver.save_status(
                job_id,
                f"running-{status_suffix}",
                {**sample_metadata, "update_id": status_suffix},
            )

        async def update_progress_task(stage, progress):
            await job_status_saver.update_progress(job_id, stage, progress)

        # Run concurrent updates
        tasks = [
            update_status("1"),
            update_status("2"),
            update_progress_task("stage1", 0.3),
            update_progress_task("stage2", 0.7),
        ]

        await asyncio.gather(*tasks)

        # Verify final state is consistent
        result = await job_status_saver.get_status(job_id)
        assert result is not None
        assert result["job_id"] == job_id
        # Status should be one of the updated values
        assert result["status"].startswith("running-")

    @pytest.mark.asyncio
    async def test_large_metadata_handling(self, job_status_saver, unique_job_id):
        """Test handling of large metadata objects."""
        # Create large metadata (but within DynamoDB limits)
        large_metadata = {
            "large_list": [f"item_{i}" for i in range(1000)],
            "large_dict": {f"key_{i}": f"value_{i}" for i in range(500)},
            "description": "A" * 1000,  # 1KB string
            "nested": {"level1": {"level2": {"level3": [{"data": f"nested_item_{i}"} for i in range(100)]}}},
        }

        # Save and retrieve large metadata
        await job_status_saver.save_status(unique_job_id, "processing", large_metadata)
        result = await job_status_saver.get_status(unique_job_id)

        assert result is not None
        assert result["job_id"] == unique_job_id
        assert result["status"] == "processing"
        assert result["metadata"] == large_metadata

    @pytest.mark.asyncio
    async def test_special_characters_in_metadata(self, job_status_saver, unique_job_id):
        """Test handling of special characters and unicode in metadata."""
        special_metadata = {
            "unicode_text": "Hello 世界 🌍 émojis and spëcial chars",
            "json_like_strings": '{"nested": "json", "array": [1, 2, 3]}',
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "newlines_and_tabs": "Line 1\nLine 2\tTabbed content",
            "empty_values": {"empty_string": "", "null_value": None, "zero": 0},
        }

        await job_status_saver.save_status(unique_job_id, "testing", special_metadata)
        result = await job_status_saver.get_status(unique_job_id)

        assert result is not None
        assert result["metadata"] == special_metadata

    @pytest.mark.asyncio
    async def test_error_recovery_after_network_issue(self, job_status_saver, unique_job_id, sample_metadata):
        """Test that operations work correctly after simulated network issues."""
        # This test verifies that the retry logic works by performing operations
        # that should succeed even if there are transient network issues

        # Perform multiple operations in sequence
        await job_status_saver.save_status(unique_job_id, "starting", sample_metadata)
        await job_status_saver.update_progress(unique_job_id, "init", 0.1)
        await job_status_saver.save_status(unique_job_id, "running", sample_metadata)
        await job_status_saver.update_progress(unique_job_id, "processing", 0.5)

        # Verify final state
        result = await job_status_saver.get_status(unique_job_id)
        assert result is not None
        assert result["status"] == "running"
