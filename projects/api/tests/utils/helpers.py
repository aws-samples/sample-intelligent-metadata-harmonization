# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Test helper functions and utilities."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest


class AsyncContextManager:
    """Helper for creating async context managers in tests."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def create_async_mock(return_value=None, side_effect=None):
    """Create an AsyncMock with optional return value or side effect."""
    mock = AsyncMock()
    if return_value is not None:
        mock.return_value = return_value
    if side_effect is not None:
        mock.side_effect = side_effect
    return mock


def create_mock_dynamodb_response(items: List[Dict], next_token: Optional[str] = None) -> Dict:
    """Create a mock DynamoDB response."""
    response = {"Items": items}
    if next_token:
        response["LastEvaluatedKey"] = {"id": {"S": next_token}}
    return response


def create_mock_s3_response(content: str, status_code: int = 200) -> Dict:
    """Create a mock S3 response."""
    from io import BytesIO

    return {
        "Body": BytesIO(content.encode()),
        "ResponseMetadata": {"HTTPStatusCode": status_code},
        "ContentLength": len(content),
        "ContentType": "application/json",
    }


def assert_validation_error_detail(error_detail: Dict, expected: Dict):
    """Assert that a validation error detail matches expected values."""
    assert error_detail["row"] == expected["row"]
    assert error_detail["column"] == expected["column"]
    assert error_detail["current_value"] == expected["current_value"]
    assert error_detail["error_type"] == expected["error_type"]

    if "valid_options" in expected:
        assert error_detail["valid_options"] == expected["valid_options"]

    if "recommended_value" in expected:
        assert error_detail["recommended_value"] == expected["recommended_value"]


def assert_job_response(response: Dict, expected_job_id: str):
    """Assert that a job response has the expected structure."""
    assert "job_id" in response
    assert response["job_id"] == expected_job_id


def assert_validation_status_response(response: Dict, expected_status: str):
    """Assert that a validation status response has the expected structure."""
    required_fields = [
        "job_id",
        "user_id",
        "core_schema_id",
        "program_schema_id",
        "status",
        "created_at",
        "current_version",
    ]

    for field in required_fields:
        assert field in response, f"Missing required field: {field}"

    assert response["status"] == expected_status

    if expected_status == "completed":
        assert "latest_results" in response
        assert response["latest_results"] is not None
        assert "completed_at" in response
        assert response["completed_at"] is not None
    else:
        assert response.get("latest_results") is None


def assert_schema_info_response(response: List[Dict]):
    """Assert that a schema info response has the expected structure."""
    assert isinstance(response, list)

    for schema in response:
        required_fields = ["core_schema_id", "name", "core_schema_path", "core_schema_s3_bucket", "program_schemas"]

        for field in required_fields:
            assert field in schema, f"Missing required field: {field}"

        assert isinstance(schema["program_schemas"], list)

        for program_schema in schema["program_schemas"]:
            program_required_fields = ["program_name", "s3_location", "s3_bucket", "program_schema_id"]

            for field in program_required_fields:
                assert field in program_schema, f"Missing required program schema field: {field}"


class TempFileHelper:
    """Helper for creating temporary files in tests."""

    @staticmethod
    def create_temp_csv(content: str) -> str:
        """Create a temporary CSV file with the given content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(content)
            return f.name

    @staticmethod
    def create_temp_json(data: Dict) -> str:
        """Create a temporary JSON file with the given data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            return f.name

    @staticmethod
    def cleanup_temp_file(filepath: str):
        """Clean up a temporary file."""
        try:
            Path(filepath).unlink()
        except FileNotFoundError:
            pass


class FileTestHelper:
    """Helper for creating mock file uploads in tests."""

    @staticmethod
    def create_upload_file_mock(filename: Optional[str], content: str, content_type: str = "text/csv"):
        """Create a mock UploadFile for testing.

        Args:
            filename: Name of the file (can be None)
            content: File content as string
            content_type: MIME type of the file

        Returns:
            Mock UploadFile object
        """
        from unittest.mock import MagicMock, AsyncMock

        # Create mock UploadFile
        mock_file = MagicMock()
        mock_file.filename = filename
        mock_file.content_type = content_type
        mock_file.size = len(content.encode("utf-8"))

        # Create a mock file object with seek method
        mock_file_obj = MagicMock()
        mock_file_obj.seek = MagicMock(return_value=None)
        mock_file.file = mock_file_obj

        # Mock the read method
        mock_file.read = AsyncMock(return_value=content.encode("utf-8"))

        # Mock the seek method
        mock_file.seek = MagicMock(return_value=None)

        return mock_file


class MockAWSService:
    """Helper for mocking AWS services."""

    def __init__(self):
        self.dynamodb_responses = {}
        self.s3_responses = {}

    def set_dynamodb_response(self, operation: str, response: Any):
        """Set a mock response for a DynamoDB operation."""
        self.dynamodb_responses[operation] = response

    def set_s3_response(self, operation: str, response: Any):
        """Set a mock response for an S3 operation."""
        self.s3_responses[operation] = response

    def get_dynamodb_mock(self):
        """Get a mock DynamoDB client."""
        mock = MagicMock()

        for operation, response in self.dynamodb_responses.items():
            setattr(mock, operation, MagicMock(return_value=response))

        return mock

    def get_s3_mock(self):
        """Get a mock S3 client."""
        mock = MagicMock()

        for operation, response in self.s3_responses.items():
            setattr(mock, operation, MagicMock(return_value=response))

        return mock


def run_async_test(coro):
    """Run an async test function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestTimer:
    """Helper for timing test operations."""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """Start the timer."""
        import time

        self.start_time = time.time()

    def stop(self):
        """Stop the timer."""
        import time

        self.end_time = time.time()

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    def assert_max_duration(self, max_seconds: float):
        """Assert that the elapsed time is less than max_seconds."""
        assert self.elapsed < max_seconds, f"Test took {self.elapsed:.2f}s, expected < {max_seconds}s"


def parametrize_error_scenarios():
    """Decorator for parametrizing common error scenarios."""
    return pytest.mark.parametrize(
        "error_type,expected_status",
        [("validation_error", 422), ("not_found", 404), ("permission_denied", 403), ("internal_error", 500)],
    )


def skip_if_no_aws():
    """Skip test if AWS credentials are not available."""
    import os

    has_aws = os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY") and os.getenv("AWS_DEFAULT_REGION")

    return pytest.mark.skipif(not has_aws, reason="AWS credentials not available")
