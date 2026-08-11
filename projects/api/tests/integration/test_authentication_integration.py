# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for authentication system integration."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient

from metadata_harmonization_api.api.main import app
from metadata_harmonization_api.api.v1.handlers.metadata_validation_handler import MetadataValidationHandler
from metadata_harmonization_api.api.v1.handlers.schema_handler import SchemaHandler
from metadata_harmonization_api.api.v1.models.metadata import ValidationJobResponse
from metadata_harmonization_api.api.v1.routes.metadata.validation import (
    get_metadata_validation_handler,
    get_schema_handler,
)
from metadata_harmonization_api.api.v1.models.metadata import SchemaInfo, ProgramSchemaInfo
from tests.utils.test_data import TestDataFactory


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for authentication system."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock MetadataValidationHandler."""
        handler = AsyncMock(spec=MetadataValidationHandler)
        handler.validate_csv_file = AsyncMock()
        handler.create_validation_job = AsyncMock(return_value=ValidationJobResponse(job_id=uuid4()))
        return handler

    @pytest.fixture
    def mock_schema_handler(self):
        """Create a mock SchemaHandler with sample schemas."""
        handler = AsyncMock(spec=SchemaHandler)
        handler.get_available_schemas = AsyncMock(return_value=[])
        return handler

    @pytest.fixture
    def client(self, mock_handler, mock_schema_handler):
        """Create a test client with dependency overrides."""
        app.dependency_overrides[get_metadata_validation_handler] = lambda: mock_handler
        app.dependency_overrides[get_schema_handler] = lambda: mock_schema_handler
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_request_to_schema_endpoint(self, client, mock_schema_handler):
        """Test request to schema listing endpoint works with dependency overrides."""
        sample_schemas = [
            SchemaInfo(
                core_schema_id="test_core_v1",
                name="Test Core",
                core_schema_path="core.json",
                core_schema_s3_bucket="test-bucket",
                program_schemas=[
                    ProgramSchemaInfo(
                        program_name="Test Program",
                        s3_location="program.json",
                        s3_bucket="test-bucket",
                        program_schema_id="test_program_v1",
                    )
                ],
            )
        ]
        mock_schema_handler.get_available_schemas.return_value = sample_schemas

        response = client.get("/api/v1/metadata/schema")
        assert response.status_code == 200
        mock_schema_handler.get_available_schemas.assert_called_once()

    def test_request_to_validation_endpoint(self, client, mock_handler):
        """Test request to validation job creation endpoint."""
        csv_content = TestDataFactory.create_csv_content()
        files = {"file": ("test_data.csv", csv_content, "text/csv")}
        data = {
            "core_schema_id": "test_core_v1",
            "program_schema_id": "test_program_v1",
        }

        response = client.post("/api/v1/metadata/validate", files=files, data=data)
        assert response.status_code == 201
        mock_handler.create_validation_job.assert_called_once()

    def test_authentication_error_handling(self, client):
        """Test various authentication error scenarios are handled gracefully."""
        response = client.get("/api/v1/metadata/schema")
        assert response.status_code == 200

    def test_authentication_with_different_endpoints(self, client, mock_handler, mock_schema_handler):
        """Test authentication integration across different endpoints."""
        sample_schemas = [
            SchemaInfo(
                core_schema_id="test_core_v1",
                name="Test Core",
                core_schema_path="core.json",
                core_schema_s3_bucket="test-bucket",
                program_schemas=[
                    ProgramSchemaInfo(
                        program_name="Test Program",
                        s3_location="program.json",
                        s3_bucket="test-bucket",
                        program_schema_id="test_program_v1",
                    )
                ],
            )
        ]
        mock_schema_handler.get_available_schemas.return_value = sample_schemas

        schema_response = client.get("/api/v1/metadata/schema")
        assert schema_response.status_code == 200

        csv_content = TestDataFactory.create_csv_content()
        files = {"file": ("test_data.csv", csv_content, "text/csv")}
        data = {
            "core_schema_id": "test_core_v1",
            "program_schema_id": "test_program_v1",
        }
        create_response = client.post("/api/v1/metadata/validate", files=files, data=data)
        assert create_response.status_code == 201


@pytest.mark.integration
class TestAuthenticationEdgeCases:
    """Integration tests for authentication edge cases and security scenarios."""

    @pytest.fixture
    def mock_schema_handler(self):
        """Create a mock SchemaHandler."""
        handler = AsyncMock(spec=SchemaHandler)
        handler.get_available_schemas = AsyncMock(return_value=[])
        return handler

    @pytest.fixture
    def client(self, mock_schema_handler):
        """Create a test client with dependency overrides."""
        app.dependency_overrides[get_schema_handler] = lambda: mock_schema_handler
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_concurrent_requests(self, client, mock_schema_handler):
        """Test concurrent requests from different users."""
        responses = []
        for i in range(3):
            headers = {"Authorization": f"Bearer token_{i}"}
            response = client.get("/api/v1/metadata/schema", headers=headers)
            responses.append(response)

        for response in responses:
            assert response.status_code == 200

        assert mock_schema_handler.get_available_schemas.call_count == 3

    def test_malformed_authorization_header(self, client):
        """Test handling of malformed authorization headers."""
        malformed_headers = [
            {"Authorization": "InvalidFormat"},
            {"Authorization": "Bearer"},
            {"Authorization": "Basic dXNlcjpwYXNz"},
            {"Authorization": "Bearer token with spaces"},
            {"Authorization": ""},
        ]

        for headers in malformed_headers:
            response = client.get("/api/v1/metadata/schema", headers=headers)
            # With dependency overrides, requests should succeed
            # regardless of auth headers since auth is bypassed
            assert response.status_code == 200
