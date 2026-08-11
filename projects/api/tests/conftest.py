# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Pytest configuration and shared fixtures."""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Test configuration
os.environ["ENVIRONMENT"] = "test"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDB client for testing."""
    with patch("boto3.client") as mock_client:
        mock_dynamodb = MagicMock()
        mock_client.return_value = mock_dynamodb

        # Mock common DynamoDB operations
        mock_dynamodb.get_item.return_value = {"Item": {}}
        mock_dynamodb.put_item.return_value = {}
        mock_dynamodb.update_item.return_value = {}
        mock_dynamodb.scan.return_value = {"Items": []}
        mock_dynamodb.query.return_value = {"Items": []}

        yield mock_dynamodb


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing."""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        # Mock common S3 operations
        mock_s3.put_object.return_value = {}
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b'{"test": "data"}')}
        mock_s3.head_object.return_value = {"ContentLength": 1024}

        yield mock_s3


@pytest.fixture
def mock_aws_clients(mock_dynamodb_client, mock_s3_client):
    """Combined AWS clients fixture."""
    return {"dynamodb": mock_dynamodb_client, "s3": mock_s3_client}


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """participant_id,age,city,state
ABC123,25,New York City,NY
DEF456,30,Los Angeles,CA
GHI789,35,Chicago,IL"""


@pytest.fixture
def sample_csv_file(sample_csv_content):
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(sample_csv_content)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def invalid_csv_content():
    """Invalid CSV content for testing."""
    return """participant_id,age,city
ABC123,25  # Missing city value
DEF456,invalid_age,Los Angeles"""


@pytest.fixture
def sample_metadata_schema():
    """Sample metadata schema for testing."""
    return {
        "core_schema_id": "core_schema_v1",
        "name": "Core Metadata Schema v1.0",
        "core_schema_path": "schemas/core/v1.0/schema.json",
        "core_schema_s3_bucket": "metadata-schemas",
        "program_schemas": [
            {
                "program_name": "Cancer Registry",
                "s3_location": "schemas/programs/cancer/v1.0/schema.json",
                "s3_bucket": "metadata-schemas",
                "program_schema_id": "cancer_registry_v1",
            },
            {
                "program_name": "Birth Defects",
                "s3_location": "schemas/programs/birth_defects/v1.0/schema.json",
                "s3_bucket": "metadata-schemas",
                "program_schema_id": "birth_defects_v1",
            },
        ],
    }


@pytest.fixture
def sample_upload_job():
    """Sample upload job for testing."""
    job_id = str(uuid4())
    return {
        "job_id": job_id,
        "user_id": "test_user_123",
        "core_schema_id": "core_schema_v1",
        "program_schema_id": "cancer_registry_v1",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "current_version": 1,
        "results": {},
    }


@pytest.fixture
def sample_validation_results():
    """Sample validation results for testing."""
    return {
        "validation_results": [
            {
                "row": 1,
                "column": "participant_id",
                "current_value": "",
                "valid_options": None,
                "recommended_value": None,
                "error_type": "REQUIRED_VALUE",
            },
            {
                "row": 2,
                "column": "city",
                "current_value": "NYC",
                "valid_options": None,
                "recommended_value": "New York City",
                "error_type": "INVALID_OPTION",
            },
        ],
        "summary": {"total_rows": 3, "total_errors": 2, "error_types": {"REQUIRED_VALUE": 1, "INVALID_OPTION": 1}},
    }


@pytest.fixture
def mock_schema_collector():
    """Mock schema collector for testing."""
    with patch("metadata_harmonization_processor.interfaces.schema_collector.SchemaCollector") as mock_interface:
        mock_instance = AsyncMock()
        mock_interface.return_value = mock_instance

        # Mock schema operations
        mock_instance.get_available_schemas.return_value = []
        mock_instance.get_schema.return_value = None
        mock_instance.get_schema_columns.return_value = []
        mock_instance.get_validation_rules.return_value = {}

        yield mock_instance


@pytest.fixture
def mock_job_status_saver():
    """Mock job status saver for testing."""
    with patch("metadata_harmonization_processor.interfaces.job_status_saver.JobStatusSaver") as mock_interface:
        mock_instance = AsyncMock()
        mock_interface.return_value = mock_instance

        # Mock job operations
        mock_instance.save_job.return_value = None
        mock_instance.get_job.return_value = None
        mock_instance.update_job_status.return_value = None
        mock_instance.add_job_results.return_value = None

        yield mock_instance


@pytest.fixture
def mock_background_tasks():
    """Mock FastAPI background tasks for testing."""
    with patch("fastapi.BackgroundTasks") as mock_tasks:
        mock_instance = MagicMock()
        mock_tasks.return_value = mock_instance
        mock_instance.add_task = MagicMock()
        yield mock_instance


@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    from metadata_harmonization_api.api.main import app

    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for the FastAPI application."""
    return TestClient(test_app)


@pytest.fixture
def authenticated_headers():
    """Mock authentication headers for testing."""
    return {"Authorization": "Bearer test_token", "Content-Type": "application/json"}


@pytest.fixture
def mock_auth():
    """Mock authentication for testing."""
    with patch("metadata_harmonization_api.api.auth.OIDCHTTPBearer") as mock_auth:
        mock_instance = MagicMock()
        mock_auth.return_value = mock_instance
        mock_instance.__call__ = AsyncMock(return_value="test_user_123")
        yield mock_instance


class MockRequest:
    """Mock request object for testing."""

    def __init__(self, user_id: str = "test_user_123"):
        self.state = MagicMock()
        self.state.user_id = user_id


@pytest.fixture
def mock_request():
    """Mock request object for testing."""
    return MockRequest()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
