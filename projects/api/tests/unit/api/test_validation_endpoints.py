# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for validation API endpoints and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi import HTTPException
from fastapi.testclient import TestClient

from metadata_harmonization_api.api.v1.routes.metadata.validation import router
from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import (
    MetadataValidationHandler,
)
from tests.utils.test_data import TestDataFactory
from tests.utils.helpers import FileTestHelper, create_async_mock


class TestMetadataValidationHandler:
    """Test cases for MetadataValidationHandler."""

    @pytest.fixture
    def mock_schema_collector(self):
        return create_async_mock()

    @pytest.fixture
    def mock_job_status_saver(self):
        return create_async_mock()

    @pytest.fixture
    def mock_processor_manager(self):
        return create_async_mock()

    @pytest.fixture
    def handler(self, mock_schema_collector, mock_job_status_saver, mock_processor_manager):
        return MetadataValidationHandler(
            schema_collector=mock_schema_collector,
            job_status_saver=mock_job_status_saver,
            processor_manager=mock_processor_manager,
        )

    @pytest.fixture
    def sample_csv_file(self):
        content = TestDataFactory.create_csv_content()
        return FileTestHelper.create_upload_file_mock("test_data.csv", content, "text/csv")

    @pytest.fixture
    def mock_background_tasks(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_validate_csv_file_success(self, handler, sample_csv_file):
        """Test successful CSV file validation."""
        await handler.validate_csv_file(sample_csv_file)

    @pytest.mark.asyncio
    async def test_validate_csv_file_invalid_extension(self, handler):
        """Test CSV file validation with invalid extension."""
        mock_file = FileTestHelper.create_upload_file_mock("test_data.txt", "some,csv,content", "text/csv")
        with pytest.raises(HTTPException) as exc_info:
            await handler.validate_csv_file(mock_file)
        assert exc_info.value.status_code == 400
        assert "Invalid file format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_csv_file_no_filename(self, handler):
        """Test CSV file validation with no filename."""
        mock_file = FileTestHelper.create_upload_file_mock(None, "some,csv,content", "text/csv")
        with pytest.raises(HTTPException) as exc_info:
            await handler.validate_csv_file(mock_file)
        assert exc_info.value.status_code == 400
        assert "Invalid file format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_csv_file_invalid_mime_type(self, handler):
        """Test CSV file validation with invalid MIME type."""
        mock_file = FileTestHelper.create_upload_file_mock("test_data.csv", "some,csv,content", "application/pdf")
        with pytest.raises(HTTPException) as exc_info:
            await handler.validate_csv_file(mock_file)
        assert exc_info.value.status_code == 400
        assert "Invalid MIME type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_csv_file_too_large(self, handler):
        """Test CSV file validation with file too large."""
        large_content = "x" * (51 * 1024 * 1024)
        mock_file = FileTestHelper.create_upload_file_mock("large_file.csv", large_content, "text/csv")
        with pytest.raises(HTTPException) as exc_info:
            await handler.validate_csv_file(mock_file)
        assert exc_info.value.status_code == 413
        assert "File too large" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_csv_file_allowed_mime_types(self, handler):
        """Every configured MIME type is accepted.

        The list is read from the handler's configuration rather than restated here, so
        this test cannot drift away from what the code actually enforces.
        """
        content = "test,csv,content"
        for mime_type in handler.metadata_config.allowed_file_types:
            mock_file = FileTestHelper.create_upload_file_mock("test_data.csv", content, mime_type)
            await handler.validate_csv_file(mock_file)

    @pytest.mark.asyncio
    async def test_validate_csv_file_rejects_text_plain(self, handler):
        """text/plain is not a configured CSV type and must be rejected.

        It used to be accepted by a hardcoded list that bypassed configuration, which let
        arbitrary text files through the CSV upload path.
        """
        assert "text/plain" not in handler.metadata_config.allowed_file_types

        mock_file = FileTestHelper.create_upload_file_mock("test_data.csv", "not,really,csv", "text/plain")
        with pytest.raises(HTTPException) as exc_info:
            await handler.validate_csv_file(mock_file)
        assert exc_info.value.status_code == 400
        assert "Invalid MIME type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_csv_file_honours_configured_limits(self, handler):
        """Configuration drives validation, rather than hardcoded values in the handler."""
        from metadata_harmonization_api.config import MetadataConfig

        # max_file_size_mb carries validation_alias="API_MAX_FILE_SIZE_MB" and the model does
        # not set populate_by_name, so the field name is not accepted at construction --
        # passing it would be silently ignored. Assign it after building the model instead.
        handler.metadata_config = MetadataConfig(allowed_file_types=["application/x-custom"])
        handler.metadata_config.max_file_size_mb = 1

        # The newly configured type is accepted...
        accepted = FileTestHelper.create_upload_file_mock("test_data.csv", "a,b", "application/x-custom")
        await handler.validate_csv_file(accepted)

        # ...while a type that is no longer configured is rejected, even though it is the
        # conventional CSV MIME type.
        rejected = FileTestHelper.create_upload_file_mock("test_data.csv", "a,b", "text/csv")
        with pytest.raises(HTTPException) as exc_info:
            await handler.validate_csv_file(rejected)
        assert exc_info.value.status_code == 400

        # The size cap follows configuration too: 2MB against the 1MB limit set above.
        too_large = FileTestHelper.create_upload_file_mock("big.csv", "x" * (2 * 1024 * 1024), "application/x-custom")
        with pytest.raises(HTTPException) as exc_info:
            await handler.validate_csv_file(too_large)
        assert exc_info.value.status_code == 413
        assert "Maximum size is 1MB" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_trigger_metadata_processing(self, handler, mock_background_tasks):
        """Test triggering metadata processing background task."""
        job_id = "test_job_123"
        csv_content = b"col1,col2\nval1,val2"
        await handler.trigger_metadata_processing(job_id, mock_background_tasks, csv_content, "core_v1", "program_v1")
        mock_background_tasks.add_task.assert_called_once()


class TestCreateValidationJobEndpoint:
    """Test cases for create validation job endpoint."""

    @pytest.fixture
    def mock_handler(self):
        from metadata_harmonization_api.api.v1.models.metadata import ValidationJobResponse

        handler = AsyncMock(spec=MetadataValidationHandler)
        handler.validate_csv_file = AsyncMock()
        handler.create_validation_job = AsyncMock(return_value=ValidationJobResponse(job_id=uuid4()))
        return handler

    @pytest.fixture
    def app_with_router(self, mock_handler):
        from fastapi import FastAPI
        from metadata_harmonization_api.api.v1.routes.metadata.validation import (
            get_metadata_validation_handler,
        )

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/metadata")
        app.dependency_overrides[get_metadata_validation_handler] = lambda: mock_handler
        return app

    @pytest.fixture
    def client(self, app_with_router):
        return TestClient(app_with_router)

    def test_create_validation_job_success(self, client, mock_handler):
        """Test successful validation job creation."""
        csv_content = TestDataFactory.create_csv_content()
        files = {"file": ("test_data.csv", csv_content, "text/csv")}
        data = {
            "core_schema_id": "test_core_v1",
            "program_schema_id": "test_program_v1",
        }
        response = client.post("/api/v1/metadata/validate", files=files, data=data)
        assert response.status_code == 201
        response_data = response.json()
        assert "jobId" in response_data
        mock_handler.create_validation_job.assert_called_once()

    def test_create_validation_job_missing_file(self, client):
        """Test validation job creation with missing file."""
        data = {
            "core_schema_id": "test_core_v1",
            "program_schema_id": "test_program_v1",
        }
        response = client.post("/api/v1/metadata/validate", data=data)
        assert response.status_code == 422

    def test_create_validation_job_missing_schema_ids(self, client):
        """Test validation job creation with missing schema IDs."""
        csv_content = TestDataFactory.create_csv_content()
        files = {"file": ("test_data.csv", csv_content, "text/csv")}
        response = client.post("/api/v1/metadata/validate", files=files)
        assert response.status_code == 422


class TestFileValidationHelpers:
    """Test cases for file validation helper functions via handler."""

    @pytest.fixture
    def handler(self):
        return MetadataValidationHandler(
            schema_collector=create_async_mock(),
            job_status_saver=create_async_mock(),
            processor_manager=create_async_mock(),
        )

    @pytest.mark.asyncio
    async def test_validate_csv_file_case_insensitive_extension(self, handler):
        """Test CSV file validation with case-insensitive extension."""
        extensions = [".csv", ".CSV", ".Csv", ".cSv"]
        content = "test,csv,content"
        for ext in extensions:
            mock_file = FileTestHelper.create_upload_file_mock(f"test_data{ext}", content, "text/csv")
            await handler.validate_csv_file(mock_file)

    @pytest.mark.asyncio
    async def test_validate_csv_file_edge_case_exact_size_limit(self, handler):
        """Test CSV file validation with file exactly at size limit."""
        content = "x" * (50 * 1024 * 1024)
        mock_file = FileTestHelper.create_upload_file_mock("test_data.csv", content, "text/csv")
        await handler.validate_csv_file(mock_file)

    @pytest.mark.asyncio
    async def test_validate_csv_file_file_position_reset(self, handler):
        """Test that file position is reset after validation."""
        content = "test,csv,content"
        mock_file = FileTestHelper.create_upload_file_mock("test_data.csv", content, "text/csv")
        await handler.validate_csv_file(mock_file)
        mock_file.file.seek.assert_called_with(0)
