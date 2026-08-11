# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for complete metadata validation workflows."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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
from metadata_harmonization_api.services.processor_manager import ProcessorManager
from metadata_harmonization_processor.models.job import MetadataUploadJob, JobResults
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentResults,
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResultsSummary,
)
from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.api.v1.models.metadata import SchemaInfo as APISchemaInfo, ProgramSchemaInfo
from metadata_harmonization_api.services.processor_manager import create_processor_manager_from_config
from tests.utils.test_data import TestDataFactory


@pytest.mark.integration
class TestMetadataValidationWorkflow:
    """Integration tests for complete metadata validation workflows."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock MetadataValidationHandler."""
        handler = AsyncMock(spec=MetadataValidationHandler)
        handler.validate_csv_file = AsyncMock()
        handler.create_validation_job = AsyncMock(return_value=ValidationJobResponse(job_id=uuid4()))
        return handler

    @pytest.fixture
    def real_handler(self):
        """Create a real MetadataValidationHandler with mocked dependencies for file validation tests."""
        mock_schema_collector = AsyncMock()
        mock_job_status_saver = AsyncMock()
        mock_processor_manager = AsyncMock()
        return MetadataValidationHandler(
            schema_collector=mock_schema_collector,
            job_status_saver=mock_job_status_saver,
            processor_manager=mock_processor_manager,
        )

    @pytest.fixture
    def mock_schema_handler(self):
        """Create a mock SchemaHandler."""
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

    @pytest.fixture
    def file_validation_client(self, real_handler, mock_schema_handler):
        """Create a test client with real handler for file validation tests."""
        app.dependency_overrides[get_metadata_validation_handler] = lambda: real_handler
        app.dependency_overrides[get_schema_handler] = lambda: mock_schema_handler
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    @pytest.fixture
    def sample_schemas(self):
        """Sample schemas for testing."""
        return [
            APISchemaInfo(
                core_schema_id="core_v1",
                name="Core Schema v1",
                core_schema_path="core_v1.json",
                core_schema_s3_bucket="test-bucket",
                program_schemas=[
                    ProgramSchemaInfo(
                        program_name="Cancer Program v1",
                        s3_location="cancer_v1.json",
                        s3_bucket="test-bucket",
                        program_schema_id="cancer_v1",
                    )
                ],
            ),
            APISchemaInfo(
                core_schema_id="core_v2",
                name="Core Schema v2",
                core_schema_path="core_v2.json",
                core_schema_s3_bucket="test-bucket",
                program_schemas=[
                    ProgramSchemaInfo(
                        program_name="Flu Program v1",
                        s3_location="flu_v1.json",
                        s3_bucket="test-bucket",
                        program_schema_id="flu_v1",
                    )
                ],
            ),
        ]

    @pytest.fixture
    def processor_config(self):
        """Create a test processor configuration."""
        return ProcessorConfig(
            schema_directory="./test_schemas",
            local_development_mode=True,
            job_status_saver_type="local",
            result_saver_type="local",
            session_saver_type="file",
            file_session_directory="./test_sessions",
            enable_redis_cache=False,
            enable_memory_cache=True,
        )

    def test_create_validation_job_workflow(self, client, mock_handler):
        """Test the create validation job workflow via API."""
        csv_content = TestDataFactory.create_csv_content()
        files = {"file": ("test_data.csv", csv_content, "text/csv")}
        data = {
            "core_schema_id": "core_v1",
            "program_schema_id": "cancer_v1",
        }

        response = client.post("/api/v1/metadata/validate", files=files, data=data)

        assert response.status_code == 201
        response_data = response.json()
        assert "jobId" in response_data
        mock_handler.create_validation_job.assert_called_once()

    def test_file_validation_workflow(self, file_validation_client):
        """Test file validation error scenarios."""
        data = {
            "core_schema_id": "core_v1",
            "program_schema_id": "cancer_v1",
        }

        # PDF file fails extension check first (not .csv)
        files = {"file": ("test_data.pdf", "fake pdf content", "application/pdf")}
        pdf_response = file_validation_client.post("/api/v1/metadata/validate", files=files, data=data)
        assert pdf_response.status_code == 400
        assert "Invalid file format" in pdf_response.json()["detail"]

        large_content = "x" * (51 * 1024 * 1024)
        large_files = {"file": ("large_file.csv", large_content, "text/csv")}
        large_response = file_validation_client.post("/api/v1/metadata/validate", files=large_files, data=data)
        assert large_response.status_code == 413
        assert "File too large" in large_response.json()["detail"]

        # TXT extension fails extension check (.txt is not .csv)
        txt_files = {"file": ("test_data.txt", "some,csv,content", "text/csv")}
        txt_response = file_validation_client.post("/api/v1/metadata/validate", files=txt_files, data=data)
        assert txt_response.status_code == 400
        assert "Invalid file format" in txt_response.json()["detail"]

    def test_schema_listing_workflow(self, client, mock_schema_handler, sample_schemas):
        """Test schema listing workflow."""
        mock_schema_handler.get_available_schemas.return_value = sample_schemas

        response = client.get("/api/v1/metadata/schema")
        assert response.status_code == 200
        mock_schema_handler.get_available_schemas.assert_called_once()

    @pytest.mark.asyncio
    async def test_processor_session_management_integration(self):
        """Test processor session management in integration workflow."""
        mock_manager = AsyncMock(spec=ProcessorManager)
        mock_processor = AsyncMock()
        mock_manager.get_processor.return_value = mock_processor

        session_ids = ["session_1", "session_2", "session_3"]

        for session_id in session_ids:
            processor = await mock_manager.get_processor(session_id)
            assert processor == mock_processor

        assert mock_manager.get_processor.call_count == 3

        for session_id in session_ids:
            await mock_manager.cleanup_processor(session_id)

        assert mock_manager.cleanup_processor.call_count == 3

    @pytest.mark.asyncio
    async def test_local_vs_cloud_configuration_switching(self):
        """Test switching between local and cloud configurations."""
        with patch.dict("os.environ", {"PROCESSOR_ENVIRONMENT": "local"}):
            with patch("metadata_harmonization_api.services.processor_manager.load_processor_settings") as mock_load:
                local_config = ProcessorConfig(
                    schema_directory="./test_schemas",
                    job_status_saver_type="local",
                    result_saver_type="local",
                    session_saver_type="file",
                    file_session_directory="./test_sessions",
                    local_development_mode=True,
                    enable_redis_cache=False,
                    enable_memory_cache=True,
                )
                mock_load.return_value = local_config

                manager = create_processor_manager_from_config()
                assert isinstance(manager, ProcessorManager)
                assert manager.processor_config.job_status_saver_type == "local"
                assert manager.processor_config.result_saver_type == "local"

    @pytest.mark.asyncio
    async def test_combined_results_integration(self):
        """Test integration of combined validation and schema alignment results in unified storage."""
        mock_schema_collector = AsyncMock()
        mock_job_status_saver = AsyncMock()
        mock_processor_manager = AsyncMock()
        mock_processor = AsyncMock()
        mock_processor.data_saver = AsyncMock()
        mock_processor_manager.get_processor.return_value = mock_processor
        mock_processor_manager.cleanup_processor = AsyncMock()

        job_id = str(uuid4())
        completed_job = MetadataUploadJob(
            job_id=job_id,
            user_id="test_user",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            status="completed",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            current_version=1,
            results={
                "1": JobResults(
                    storage_type="s3",
                    location=f"validation-results/{job_id}/v1/",
                    bucket="test-results-bucket",
                )
            },
        )
        mock_job_status_saver.get_job.return_value = completed_job

        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="aligned_col1",
                    current_value="val1",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=2,
                total_errors=1,
                error_types={ValidationErrorType.REQUIRED_VALUE: 1},
                columns_validated=1,
            ),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[
                SchemaAlignmentChangeDetail(
                    change_type="rename",
                    original_column="col1",
                    new_column="aligned_col1",
                    reason="Schema alignment",
                    row_count_affected=2,
                )
            ],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2\nval3,val4",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2\nval3,val4",
                total_changes=2,
                columns_renamed=2,
                columns_added=0,
                columns_removed=0,
                rows_original=2,
                rows_aligned=2,
            ),
        )

        combined = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )
        mock_processor.data_saver.get_results.return_value = combined

        handler = MetadataValidationHandler(
            schema_collector=mock_schema_collector,
            job_status_saver=mock_job_status_saver,
            processor_manager=mock_processor_manager,
        )

        request = MagicMock()
        request.state.user_id = "test_user"
        response = await handler.get_validation_status(metadata_id=job_id, request=request)

        response_dict = response.model_dump(by_alias=True)
        assert str(response_dict["jobId"]) == job_id
        assert response_dict["status"] == "completed"
        assert response_dict["latestResults"] is not None

        latest_results = response_dict["latestResults"]
        assert latest_results["validationResults"] is not None
        assert latest_results["schemaAlignmentResults"] is not None

        validation_data = latest_results["validationResults"]
        assert validation_data["summary"]["totalErrors"] == 1

        mock_processor_manager.get_processor.assert_called_with(job_id)
        mock_processor_manager.cleanup_processor.assert_called()

    @pytest.mark.asyncio
    async def test_combined_results_validation_only(self):
        """Test validation status response when only validation results are available."""
        mock_schema_collector = AsyncMock()
        mock_job_status_saver = AsyncMock()
        mock_processor_manager = AsyncMock()
        mock_processor = AsyncMock()
        mock_processor.data_saver = AsyncMock()
        mock_processor_manager.get_processor.return_value = mock_processor
        mock_processor_manager.cleanup_processor = AsyncMock()

        job_id = str(uuid4())
        completed_job = MetadataUploadJob(
            job_id=job_id,
            user_id="test_user",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            status="completed",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            current_version=1,
            results={
                "1": JobResults(
                    storage_type="s3",
                    location=f"validation-results/{job_id}/v1/",
                    bucket="test-results-bucket",
                )
            },
        )
        mock_job_status_saver.get_job.return_value = completed_job

        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(
                total_rows=2,
                total_errors=0,
                error_types={},
                columns_validated=0,
            ),
        )
        combined = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=None,
        )
        mock_processor.data_saver.get_results.return_value = combined

        handler = MetadataValidationHandler(
            schema_collector=mock_schema_collector,
            job_status_saver=mock_job_status_saver,
            processor_manager=mock_processor_manager,
        )

        request = MagicMock()
        request.state.user_id = "test_user"
        response = await handler.get_validation_status(metadata_id=job_id, request=request)

        response_dict = response.model_dump(by_alias=True)
        assert response_dict["latestResults"] is not None
        latest_results = response_dict["latestResults"]
        assert latest_results["validationResults"] is not None
        assert latest_results["validationResults"]["summary"]["totalErrors"] == 0
        assert latest_results["schemaAlignmentResults"] is None

    @pytest.mark.asyncio
    async def test_combined_results_error_handling(self):
        """Test error handling when retrieving combined results fails."""
        mock_schema_collector = AsyncMock()
        mock_job_status_saver = AsyncMock()
        mock_processor_manager = AsyncMock()
        mock_processor = AsyncMock()
        mock_processor.data_saver = AsyncMock()
        mock_processor.data_saver.get_results.side_effect = Exception("S3 retrieval failed")
        mock_processor_manager.get_processor.return_value = mock_processor
        mock_processor_manager.cleanup_processor = AsyncMock()

        job_id = str(uuid4())
        completed_job = MetadataUploadJob(
            job_id=job_id,
            user_id="test_user",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            status="completed",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            current_version=1,
            results={
                "1": JobResults(
                    storage_type="s3",
                    location=f"validation-results/{job_id}/v1/",
                    bucket="test-results-bucket",
                )
            },
        )
        mock_job_status_saver.get_job.return_value = completed_job

        handler = MetadataValidationHandler(
            schema_collector=mock_schema_collector,
            job_status_saver=mock_job_status_saver,
            processor_manager=mock_processor_manager,
        )

        request = MagicMock()
        request.state.user_id = "test_user"
        response = await handler.get_validation_status(metadata_id=job_id, request=request)

        response_dict = response.model_dump(by_alias=True)
        assert str(response_dict["jobId"]) == job_id
        assert response_dict["status"] == "completed"
        assert response_dict["latestResults"] is None

        mock_processor_manager.cleanup_processor.assert_called()
