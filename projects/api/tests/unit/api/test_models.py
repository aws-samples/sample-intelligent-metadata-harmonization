# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for API models."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID

from metadata_harmonization_api.api.v1.models.metadata import (
    SchemaAlignmentResults,
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResultsSummary,
    ValidationCreateRequest,
    ValidationJobResponse,
    ValidationStatusResponse,
    ProgramSchemaInfo,
    SchemaInfo,
    ErrorResponse,
    FileValidationError,
    FileValidationRequest,
    FileValidationResponse,
)
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationResults,
    ValidationResultsSummary,
    ValidationErrorType,
)


class TestSchemaAlignmentResults:
    """Test cases for SchemaAlignmentResults model."""

    def test_schema_alignment_results_empty(self):
        """Test creating SchemaAlignmentResults with minimal data."""
        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-123",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
        )

        data = SchemaAlignmentResults(schema_alignment_results=[], summary=summary)

        assert len(data.schema_alignment_results) == 0
        assert data.summary.job_id == "test-job-123"
        assert data.summary.version == 1
        assert data.summary.total_changes == 0

    def test_schema_alignment_results_full(self):
        """Test creating a complete SchemaAlignmentResults."""
        change_details = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="id",
                new_column="participant_id",
                reason="Schema alignment to match target schema",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add", new_column="status", reason="Required field in target schema", row_count_affected=2
            ),
        ]

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-456",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="id,name\n1,John\n2,Jane",
            aligned_data_csv="participant_id,name,status\n1,John,\n2,Jane,",
            total_changes=2,
            columns_renamed=1,
            columns_added=1,
            columns_removed=0,
            rows_original=2,
            rows_aligned=2,
        )

        data = SchemaAlignmentResults(schema_alignment_results=change_details, summary=summary)

        assert len(data.schema_alignment_results) == 2
        assert data.schema_alignment_results[0].change_type == "rename"
        assert data.schema_alignment_results[0].original_column == "id"
        assert data.schema_alignment_results[0].new_column == "participant_id"
        assert data.schema_alignment_results[1].change_type == "add"
        assert data.schema_alignment_results[1].new_column == "status"

        assert data.summary.job_id == "test-job-456"
        assert data.summary.total_changes == 2
        assert data.summary.columns_renamed == 1
        assert data.summary.columns_added == 1

    def test_schema_alignment_change_detail_serialization(self):
        """Test SchemaAlignmentChangeDetail serialization with camelCase aliases."""

        change = SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="id",
            new_column="participant_id",
            reason="Schema alignment",
            row_count_affected=10,
        )

        # Test model_dump with by_alias=True for camelCase
        serialized = change.model_dump(by_alias=True)

        expected = {
            "changeType": "rename",
            "originalColumn": "id",
            "newColumn": "participant_id",
            "reason": "Schema alignment",
            "rowCountAffected": 10,
            "confidenceScore": 0.0,
            "confidenceLevel": "Low",
            "llmConfidenceLevel": None,
        }

        assert serialized == expected

    def test_schema_alignment_results_summary_serialization(self):
        """Test SchemaAlignmentResultsSummary serialization with camelCase aliases."""
        timestamp = datetime.now(timezone.utc)
        summary = SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            timestamp=timestamp,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
            total_changes=1,
            columns_renamed=1,
            columns_added=0,
            columns_removed=0,
            rows_original=1,
            rows_aligned=1,
        )

        # Test model_dump with by_alias=True for camelCase
        serialized = summary.model_dump(by_alias=True)

        expected = {
            "jobId": "test-job",
            "version": 1,
            "timestamp": timestamp,
            "originalDataCsv": "id,name\n1,John",
            "alignedDataCsv": "participant_id,participant_name\n1,John",
            "totalChanges": 1,
            "columnsRenamed": 1,
            "columnsAdded": 0,
            "columnsRemoved": 0,
            "rowsOriginal": 1,
            "rowsAligned": 1,
        }

        assert serialized == expected

    def test_schema_alignment_results_serialization(self):
        """Test SchemaAlignmentResults serialization with camelCase aliases."""
        change = SchemaAlignmentChangeDetail(change_type="rename", original_column="id", new_column="participant_id")

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
        )

        data = SchemaAlignmentResults(schema_alignment_results=[change], summary=summary)

        # Test model_dump with by_alias=True for camelCase
        serialized = data.model_dump(by_alias=True)

        assert "schemaAlignmentResults" in serialized
        assert "summary" in serialized
        assert len(serialized["schemaAlignmentResults"]) == 1
        assert serialized["schemaAlignmentResults"][0]["changeType"] == "rename"


class TestValidationCreateRequest:
    """Test cases for ValidationCreateRequest model."""

    def test_validation_create_request_valid(self):
        """Test creating a valid ValidationCreateRequest."""
        request = ValidationCreateRequest(core_schema_id="core_v1", program_schema_id="program_v1")

        assert request.core_schema_id == "core_v1"
        assert request.program_schema_id == "program_v1"

    def test_validation_create_request_missing_fields(self):
        """Test ValidationCreateRequest with missing required fields."""
        with pytest.raises(ValueError):
            ValidationCreateRequest()

        with pytest.raises(ValueError):
            ValidationCreateRequest(core_schema_id="core_v1")

    def test_validation_create_request_serialization(self):
        """Test ValidationCreateRequest serialization."""
        request = ValidationCreateRequest(core_schema_id="core_v1", program_schema_id="program_v1")

        data = request.model_dump()
        assert data["core_schema_id"] == "core_v1"
        assert data["program_schema_id"] == "program_v1"

    def test_validation_create_request_from_dict(self):
        """Test creating ValidationCreateRequest from dictionary."""
        data = {"core_schema_id": "core_v1", "program_schema_id": "program_v1"}

        request = ValidationCreateRequest(**data)
        assert request.core_schema_id == "core_v1"
        assert request.program_schema_id == "program_v1"


class TestValidationJobResponse:
    """Test cases for ValidationJobResponse model."""

    def test_validation_job_response_valid(self):
        """Test creating a valid ValidationJobResponse."""
        job_id = uuid4()
        response = ValidationJobResponse(job_id=job_id)

        assert response.job_id == job_id
        assert isinstance(response.job_id, UUID)

    def test_validation_job_response_string_uuid(self):
        """Test ValidationJobResponse with string UUID."""
        job_id_str = str(uuid4())
        response = ValidationJobResponse(job_id=job_id_str)

        assert str(response.job_id) == job_id_str
        assert isinstance(response.job_id, UUID)

    def test_validation_job_response_invalid_uuid(self):
        """Test ValidationJobResponse with invalid UUID."""
        with pytest.raises(ValueError):
            ValidationJobResponse(job_id="not-a-uuid")

    def test_validation_job_response_serialization(self):
        """Test ValidationJobResponse serialization."""
        job_id = uuid4()
        response = ValidationJobResponse(job_id=job_id)

        data = response.model_dump()
        assert data["job_id"] == job_id


class TestCombinedResults:
    """Test cases for CombinedResults model."""

    def test_combined_results_empty(self):
        """Test creating an empty CombinedResults."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        results = CombinedResults()

        assert results.validation_results is None
        assert results.schema_alignment_results is None

    def test_combined_results_validation_only(self):
        """Test CombinedResults with validation results only."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_column",
                    current_value="",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    valid_options=None,
                    recommended_value="Non-empty string",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=10, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
        )

        results = CombinedResults(validation_results=validation_results)

        assert results.validation_results is not None
        assert len(results.validation_results.validation_results) == 1
        assert results.schema_alignment_results is None

    def test_combined_results_schema_alignment_only(self):
        """Test CombinedResults with schema alignment results only."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        change_detail = SchemaAlignmentChangeDetail(
            change_type="rename", original_column="id", new_column="participant_id", reason="Schema alignment"
        )

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
            total_changes=1,
            columns_renamed=1,
        )

        schema_alignment_data = SchemaAlignmentResults(schema_alignment_results=[change_detail], summary=summary)

        results = CombinedResults(schema_alignment_results=schema_alignment_data)

        assert results.validation_results is None
        assert results.schema_alignment_results is not None
        assert results.schema_alignment_results.summary.original_data_csv == "id,name\n1,John"

    def test_combined_results_full(self):
        """Test CombinedResults with both validation and schema alignment results."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_column",
                    current_value="",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    valid_options=None,
                    recommended_value="Non-empty string",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=10, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
        )

        change_detail = SchemaAlignmentChangeDetail(
            change_type="rename", original_column="id", new_column="participant_id", reason="Schema alignment"
        )

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
            total_changes=1,
            columns_renamed=1,
        )

        schema_alignment_data = SchemaAlignmentResults(schema_alignment_results=[change_detail], summary=summary)

        results = CombinedResults(validation_results=validation_results, schema_alignment_results=schema_alignment_data)

        assert results.validation_results is not None
        assert results.schema_alignment_results is not None
        assert len(results.validation_results.validation_results) == 1
        assert results.schema_alignment_results.summary.original_data_csv == "id,name\n1,John"

    def test_combined_results_serialization(self):
        """Test CombinedResults serialization with camelCase aliases."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=0, total_errors=0, error_types={}, columns_validated=0),
        )

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
        )

        schema_alignment_data = SchemaAlignmentResults(schema_alignment_results=[], summary=summary)

        results = CombinedResults(validation_results=validation_results, schema_alignment_results=schema_alignment_data)

        # Test serialization with camelCase aliases
        data = results.model_dump(by_alias=True)
        assert "validationResults" in data
        assert "schemaAlignmentResults" in data
        assert data["schemaAlignmentResults"]["summary"]["originalDataCsv"] == "id,name\n1,John"


class TestValidationStatusResponse:
    """Test cases for ValidationStatusResponse model."""

    def test_validation_status_response_pending(self):
        """Test ValidationStatusResponse for pending job."""
        job_id = uuid4()
        created_at = datetime.now(timezone.utc)

        response = ValidationStatusResponse(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="program_v1",
            status="pending",
            created_at=created_at,
            current_version=1,
        )

        assert response.job_id == job_id
        assert response.user_id == "test_user_123"
        assert response.status == "pending"
        assert response.created_at == created_at
        assert response.completed_at is None
        assert response.current_version == 1
        assert response.latest_results is None

    def test_validation_status_response_completed(self):
        """Test ValidationStatusResponse for completed job."""
        job_id = uuid4()
        created_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)

        # Create ValidationResults object
        from metadata_harmonization_processor.models.validation import (
            ValidationResults,
            ValidationResultsSummary,
            ValidationErrorDetail,
            ValidationErrorType,
        )

        results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1, column="participant_id", current_value="", error_type=ValidationErrorType.REQUIRED_VALUE
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=10, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
        )

        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        combined_results = CombinedResults(validation_results=results)

        response = ValidationStatusResponse(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="program_v1",
            status="completed",
            created_at=created_at,
            completed_at=completed_at,
            current_version=2,
            latest_results=combined_results,
        )

        assert response.status == "completed"
        assert response.completed_at == completed_at
        assert response.current_version == 2
        assert response.latest_results is not None
        assert response.latest_results.validation_results is not None
        assert len(response.latest_results.validation_results.validation_results) == 1
        assert response.latest_results.schema_alignment_results is None  # Default value

    def test_validation_status_response_with_combined_results(self):
        """Test ValidationStatusResponse with combined validation and schema alignment results."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        job_id = uuid4()
        created_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)

        # Create validation results
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_column",
                    current_value="",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    valid_options=None,
                    recommended_value="Non-empty string",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=10, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
        )

        # Create schema alignment data
        change_detail = SchemaAlignmentChangeDetail(
            change_type="rename", original_column="id", new_column="participant_id", reason="Schema alignment"
        )

        summary = SchemaAlignmentResultsSummary(
            job_id=str(job_id),
            version=1,
            timestamp=created_at,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
            total_changes=1,
            columns_renamed=1,
            columns_added=0,
            columns_removed=0,
        )

        schema_alignment_data = SchemaAlignmentResults(schema_alignment_results=[change_detail], summary=summary)

        # Create combined results
        combined_results = CombinedResults(
            validation_results=validation_results, schema_alignment_results=schema_alignment_data
        )

        response = ValidationStatusResponse(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="program_v1",
            status="completed",
            created_at=created_at,
            completed_at=completed_at,
            current_version=2,
            latest_results=combined_results,
        )

        assert response.latest_results is not None
        assert response.latest_results.validation_results is not None
        assert response.latest_results.schema_alignment_results is not None
        assert response.latest_results.schema_alignment_results.summary.original_data_csv == "id,name\n1,John"
        assert (
            response.latest_results.schema_alignment_results.summary.aligned_data_csv
            == "participant_id,participant_name\n1,John"
        )
        assert len(response.latest_results.schema_alignment_results.schema_alignment_results) == 1
        assert response.latest_results.schema_alignment_results.schema_alignment_results[0].change_type == "rename"

    def test_validation_status_response_missing_fields(self):
        """Test ValidationStatusResponse with missing required fields."""
        with pytest.raises(ValueError):
            ValidationStatusResponse()

        with pytest.raises(ValueError):
            ValidationStatusResponse(job_id=uuid4())

    def test_validation_status_response_serialization(self):
        """Test ValidationStatusResponse serialization."""
        job_id = uuid4()
        created_at = datetime.now(timezone.utc)

        response = ValidationStatusResponse(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="program_v1",
            status="pending",
            created_at=created_at,
            current_version=1,
        )

        data = response.model_dump()
        assert data["job_id"] == job_id
        assert data["user_id"] == "test_user_123"
        assert data["status"] == "pending"
        assert data["current_version"] == 1
        assert data["latest_results"] is None

    def test_validation_status_response_serialization_with_camel_case(self):
        """Test ValidationStatusResponse serialization with camelCase aliases."""
        job_id = uuid4()
        created_at = datetime.now(timezone.utc)

        summary = SchemaAlignmentResultsSummary(
            job_id=str(job_id),
            version=1,
            timestamp=created_at,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
        )

        schema_alignment_data = SchemaAlignmentResults(schema_alignment_results=[], summary=summary)

        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults

        combined_results = CombinedResults(schema_alignment_results=schema_alignment_data)

        response = ValidationStatusResponse(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="program_v1",
            status="completed",
            created_at=created_at,
            current_version=1,
            latest_results=combined_results,
        )

        # Test serialization with camelCase aliases
        data = response.model_dump(by_alias=True)
        assert "jobId" in data
        assert "userId" in data
        assert "coreSchemaId" in data
        assert "programSchemaId" in data
        assert "createdAt" in data
        assert "currentVersion" in data
        assert "latestResults" in data
        assert data["latestResults"]["schemaAlignmentResults"]["summary"]["originalDataCsv"] == "id,name\n1,John"
        assert (
            data["latestResults"]["schemaAlignmentResults"]["summary"]["alignedDataCsv"]
            == "participant_id,participant_name\n1,John"
        )


class TestProgramSchemaInfo:
    """Test cases for ProgramSchemaInfo model."""

    def test_program_schema_info_valid(self):
        """Test creating a valid ProgramSchemaInfo."""
        info = ProgramSchemaInfo(
            program_name="Cancer Registry",
            s3_location="schemas/programs/cancer/v1.0/schema.json",
            s3_bucket="metadata-schemas",
            program_schema_id="cancer_v1",
        )

        assert info.program_name == "Cancer Registry"
        assert info.s3_location == "schemas/programs/cancer/v1.0/schema.json"
        assert info.s3_bucket == "metadata-schemas"
        assert info.program_schema_id == "cancer_v1"

    def test_program_schema_info_missing_fields(self):
        """Test ProgramSchemaInfo with missing required fields."""
        with pytest.raises(ValueError):
            ProgramSchemaInfo()

        with pytest.raises(ValueError):
            ProgramSchemaInfo(program_name="Cancer Registry")

    def test_program_schema_info_serialization(self):
        """Test ProgramSchemaInfo serialization."""
        info = ProgramSchemaInfo(
            program_name="Cancer Registry",
            s3_location="schemas/programs/cancer/v1.0/schema.json",
            s3_bucket="metadata-schemas",
            program_schema_id="cancer_v1",
        )

        data = info.model_dump()
        assert data["program_name"] == "Cancer Registry"
        assert data["s3_location"] == "schemas/programs/cancer/v1.0/schema.json"
        assert data["s3_bucket"] == "metadata-schemas"
        assert data["program_schema_id"] == "cancer_v1"


class TestSchemaInfo:
    """Test cases for SchemaInfo model."""

    def test_schema_info_valid(self):
        """Test creating a valid SchemaInfo."""
        program_schemas = [
            ProgramSchemaInfo(
                program_name="Cancer Registry",
                s3_location="schemas/programs/cancer/v1.0/schema.json",
                s3_bucket="metadata-schemas",
                program_schema_id="cancer_v1",
            ),
            ProgramSchemaInfo(
                program_name="Birth Defects",
                s3_location="schemas/programs/birth_defects/v1.0/schema.json",
                s3_bucket="metadata-schemas",
                program_schema_id="birth_defects_v1",
            ),
        ]

        info = SchemaInfo(
            core_schema_id="core_v1",
            name="Core Metadata Schema v1.0",
            core_schema_path="schemas/core/v1.0/schema.json",
            core_schema_s3_bucket="metadata-schemas",
            program_schemas=program_schemas,
        )

        assert info.core_schema_id == "core_v1"
        assert info.name == "Core Metadata Schema v1.0"
        assert info.core_schema_path == "schemas/core/v1.0/schema.json"
        assert info.core_schema_s3_bucket == "metadata-schemas"
        assert len(info.program_schemas) == 2
        assert info.program_schemas[0].program_name == "Cancer Registry"
        assert info.program_schemas[1].program_name == "Birth Defects"

    def test_schema_info_empty_program_schemas(self):
        """Test SchemaInfo with empty program schemas list."""
        info = SchemaInfo(
            core_schema_id="core_v1",
            name="Core Metadata Schema v1.0",
            core_schema_path="schemas/core/v1.0/schema.json",
            core_schema_s3_bucket="metadata-schemas",
            program_schemas=[],
        )

        assert len(info.program_schemas) == 0

    def test_schema_info_missing_fields(self):
        """Test SchemaInfo with missing required fields."""
        with pytest.raises(ValueError):
            SchemaInfo()

        with pytest.raises(ValueError):
            SchemaInfo(core_schema_id="core_v1")

    def test_schema_info_serialization(self):
        """Test SchemaInfo serialization."""
        program_schemas = [
            ProgramSchemaInfo(
                program_name="Cancer Registry",
                s3_location="schemas/programs/cancer/v1.0/schema.json",
                s3_bucket="metadata-schemas",
                program_schema_id="cancer_v1",
            )
        ]

        info = SchemaInfo(
            core_schema_id="core_v1",
            name="Core Metadata Schema v1.0",
            core_schema_path="schemas/core/v1.0/schema.json",
            core_schema_s3_bucket="metadata-schemas",
            program_schemas=program_schemas,
        )

        data = info.model_dump()
        assert data["core_schema_id"] == "core_v1"
        assert data["name"] == "Core Metadata Schema v1.0"
        assert len(data["program_schemas"]) == 1
        assert data["program_schemas"][0]["program_name"] == "Cancer Registry"


class TestChangeObject:
    """Test cases for ChangeObject model."""

    def test_change_object_add_valid(self):
        """Test creating a valid ChangeObject for add operation."""
        from metadata_harmonization_processor.models.change_tracking import ChangeObject

        change = ChangeObject(
            change_id="chg_001",
            change_type="add",
            source_type="system",
            component="validation",
            column="A1",
            row=1,
            new_value="new_value",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
            confidence_score=0.8,
        )

        assert change.change_id == "chg_001"
        assert change.change_type == "add"
        assert change.source_type == "system"
        assert change.component == "validation"
        assert change.column == "A1"
        assert change.new_value == "new_value"
        assert change.old_value is None
        assert change.confidence_score == 0.8

    def test_change_object_remove_valid(self):
        """Test creating a valid ChangeObject for remove operation."""
        from metadata_harmonization_processor.models.change_tracking import ChangeObject

        change = ChangeObject(
            change_id="chg_002",
            change_type="remove",
            source_type="user",
            component="schema_alignment",
            column="$.data[0].name",
            old_value="old_value",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
        )

        assert change.change_type == "remove"
        assert change.source_type == "user"
        assert change.old_value == "old_value"
        assert change.new_value is None
        assert change.confidence_score is None

    def test_change_object_rename_valid(self):
        """Test creating a valid ChangeObject for rename operation."""
        from metadata_harmonization_processor.models.change_tracking import ChangeObject

        change = ChangeObject(
            change_id="chg_003",
            change_type="rename",
            source_type="system",
            component="validation",
            column="B2",
            row=2,
            old_value="old_name",
            new_value="new_name",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
            confidence_score=0.9,
        )

        assert change.change_type == "rename"
        assert change.old_value == "old_name"
        assert change.new_value == "new_name"
        assert change.confidence_score == 0.9

    def test_change_object_serialization(self):
        """Test ChangeObject serialization with camelCase aliases."""
        from metadata_harmonization_processor.models.change_tracking import ChangeObject

        change = ChangeObject(
            change_id="chg_001",
            change_type="add",
            source_type="system",
            component="validation",
            column="A1",
            row=1,
            new_value="test_value",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
            confidence_score=0.8,
            user_context={"note": "test"},
        )

        # Test serialization with camelCase aliases
        data = change.model_dump(by_alias=True)

        expected_keys = {
            "changeId",
            "changeType",
            "sourceType",
            "component",
            "column",
            "row",
            "oldValue",
            "newValue",
            "timestamp",
            "sourceVersion",
            "targetVersion",
            "confidenceScore",
            "userContext",
        }

        assert set(data.keys()) == expected_keys
        assert data["changeId"] == "chg_001"
        assert data["changeType"] == "add"
        assert data["sourceType"] == "system"
        assert data["column"] == "A1"
        assert data["newValue"] == "test_value"
        assert data["confidenceScore"] == 0.8
        assert data["userContext"] == {"note": "test"}


class TestChangesSummary:
    """Test cases for ChangesSummary model."""

    def test_changes_summary_valid(self):
        """Test creating a valid ChangesSummary."""
        from metadata_harmonization_processor.models.change_tracking import ChangesSummary

        summary = ChangesSummary(total_changes=5, adds=2, removes=1, renames=2, system_changes=3, user_changes=2)

        assert summary.total_changes == 5
        assert summary.adds == 2
        assert summary.removes == 1
        assert summary.renames == 2
        assert summary.system_changes == 3
        assert summary.user_changes == 2

    def test_changes_summary_empty(self):
        """Test creating an empty ChangesSummary."""
        from metadata_harmonization_processor.models.change_tracking import ChangesSummary

        summary = ChangesSummary()

        assert summary.total_changes == 0
        assert summary.adds == 0
        assert summary.removes == 0
        assert summary.renames == 0
        assert summary.system_changes == 0
        assert summary.user_changes == 0

    def test_changes_summary_serialization(self):
        """Test ChangesSummary serialization with camelCase aliases."""
        from metadata_harmonization_processor.models.change_tracking import ChangesSummary

        summary = ChangesSummary(total_changes=3, adds=1, removes=1, renames=1, system_changes=2, user_changes=1)

        # Test serialization with camelCase aliases
        data = summary.model_dump(by_alias=True)

        expected = {"totalChanges": 3, "adds": 1, "removes": 1, "renames": 1, "systemChanges": 2, "userChanges": 1}

        assert data == expected


class TestChangeTrackingResults:
    """Test cases for ChangeTrackingResults model."""

    def test_change_tracking_results_empty(self):
        """Test creating empty ChangeTrackingResults."""
        from metadata_harmonization_processor.models.change_tracking import ChangeTrackingResults, ChangesSummary

        summary = ChangesSummary()
        tracking = ChangeTrackingResults(changes=[], summary=summary, comparison_metadata={})

        assert len(tracking.changes) == 0
        assert tracking.summary.total_changes == 0
        assert tracking.comparison_metadata == {}

    def test_change_tracking_results_with_changes(self):
        """Test ChangeTrackingResults with actual changes."""
        from metadata_harmonization_processor.models.change_tracking import (
            ChangeTrackingResults,
            ChangeObject,
            ChangesSummary,
        )

        changes = [
            ChangeObject(
                change_id="chg_001",
                change_type="add",
                source_type="system",
                component="validation",
                column="A1",
                row=1,
                new_value="test_value",
                timestamp="2025-01-01T12:00:00Z",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_id="chg_002",
                change_type="rename",
                source_type="user",
                component="schema_alignment",
                column="$.data[0].name",
                old_value="old_name",
                new_value="new_name",
                timestamp="2025-01-01T12:00:00Z",
                source_version=1,
                target_version=2,
            ),
        ]

        summary = ChangesSummary(total_changes=2, adds=1, removes=0, renames=1, system_changes=1, user_changes=1)

        metadata = {"detection_timestamp": "2025-01-01T12:00:00Z", "compared_versions": [1, 2]}

        tracking = ChangeTrackingResults(changes=changes, summary=summary, comparison_metadata=metadata)

        assert len(tracking.changes) == 2
        assert tracking.summary.total_changes == 2
        assert tracking.summary.adds == 1
        assert tracking.summary.renames == 1
        assert tracking.comparison_metadata["detection_timestamp"] == "2025-01-01T12:00:00Z"

    def test_change_tracking_results_serialization(self):
        """Test ChangeTrackingResults serialization with camelCase aliases."""
        from metadata_harmonization_processor.models.change_tracking import (
            ChangeTrackingResults,
            ChangeObject,
            ChangesSummary,
        )

        change = ChangeObject(
            change_id="chg_001",
            change_type="add",
            source_type="system",
            component="validation",
            column="A1",
            row=1,
            new_value="test_value",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
        )

        summary = ChangesSummary(total_changes=1, adds=1, removes=0, renames=0, system_changes=1, user_changes=0)

        tracking = ChangeTrackingResults(changes=[change], summary=summary, comparison_metadata={"test": "data"})

        # Test serialization with camelCase aliases
        data = tracking.model_dump(by_alias=True)

        assert "changes" in data
        assert "summary" in data
        assert "comparisonMetadata" in data
        assert len(data["changes"]) == 1
        assert data["changes"][0]["changeId"] == "chg_001"
        assert data["summary"]["totalChanges"] == 1
        assert data["comparisonMetadata"] == {"test": "data"}


class TestCombinedResultsWithChangeTracking:
    """Test cases for CombinedResults with change tracking."""

    def test_combined_results_with_change_tracking(self):
        """Test CombinedResults with change tracking data."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults
        from metadata_harmonization_processor.models.change_tracking import (
            ChangeTrackingResults,
            ChangeObject,
            ChangesSummary,
        )

        # Create change tracking data
        change = ChangeObject(
            change_id="chg_001",
            change_type="rename",
            source_type="system",
            component="validation",
            column="A1",
            row=1,
            old_value="old_value",
            new_value="new_value",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
            confidence_score=0.8,
        )

        summary = ChangesSummary(total_changes=1, adds=0, removes=0, renames=1, system_changes=1, user_changes=0)

        change_tracking = ChangeTrackingResults(
            changes=[change], summary=summary, comparison_metadata={"detection_timestamp": "2025-01-01T12:00:00Z"}
        )

        # Create combined results with change tracking
        results = CombinedResults(
            validation_results=None, schema_alignment_results=None, change_tracking=change_tracking
        )

        assert results.validation_results is None
        assert results.schema_alignment_results is None
        assert results.change_tracking is not None
        assert len(results.change_tracking.changes) == 1
        assert results.change_tracking.summary.total_changes == 1

    def test_combined_results_full_with_change_tracking(self):
        """Test CombinedResults with all components including change tracking."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults
        from metadata_harmonization_processor.models.change_tracking import (
            ChangeTrackingResults,
            ChangeObject,
            ChangesSummary,
        )

        # Create validation results
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_column",
                    current_value="",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    valid_options=None,
                    recommended_value="Non-empty string",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=10, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
        )

        # Create schema alignment results
        change_detail = SchemaAlignmentChangeDetail(
            change_type="rename", original_column="id", new_column="participant_id", reason="Schema alignment"
        )

        schema_summary = SchemaAlignmentResultsSummary(
            job_id="test-job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
            total_changes=1,
            columns_renamed=1,
        )

        schema_alignment_data = SchemaAlignmentResults(schema_alignment_results=[change_detail], summary=schema_summary)

        # Create change tracking data
        change = ChangeObject(
            change_id="chg_001",
            change_type="rename",
            source_type="user",
            component="validation",
            column="B1",
            row=1,
            old_value="",
            new_value="corrected_value",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
        )

        changes_summary = ChangesSummary(
            total_changes=1, adds=0, removes=0, renames=1, system_changes=0, user_changes=1
        )

        change_tracking = ChangeTrackingResults(
            changes=[change],
            summary=changes_summary,
            comparison_metadata={"detection_timestamp": "2025-01-01T12:00:00Z"},
        )

        # Create combined results with all components
        results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_data,
            change_tracking=change_tracking,
        )

        assert results.validation_results is not None
        assert results.schema_alignment_results is not None
        assert results.change_tracking is not None
        assert len(results.validation_results.validation_results) == 1
        assert len(results.schema_alignment_results.schema_alignment_results) == 1
        assert len(results.change_tracking.changes) == 1

    def test_combined_results_change_tracking_serialization(self):
        """Test CombinedResults serialization with change tracking and camelCase aliases."""
        from metadata_harmonization_api.api.v1.models.metadata import CombinedResults
        from metadata_harmonization_processor.models.change_tracking import (
            ChangeTrackingResults,
            ChangeObject,
            ChangesSummary,
        )

        change = ChangeObject(
            change_id="chg_001",
            change_type="add",
            source_type="system",
            component="validation",
            column="A1",
            row=1,
            new_value="test_value",
            timestamp="2025-01-01T12:00:00Z",
            source_version=1,
            target_version=2,
            confidence_score=0.9,
        )

        summary = ChangesSummary(total_changes=1, adds=1, removes=0, renames=0, system_changes=1, user_changes=0)

        change_tracking = ChangeTrackingResults(
            changes=[change], summary=summary, comparison_metadata={"detection_timestamp": "2025-01-01T12:00:00Z"}
        )

        results = CombinedResults(change_tracking=change_tracking)

        # Test serialization with camelCase aliases
        data = results.model_dump(by_alias=True)

        assert "changeTracking" in data
        assert data["validationResults"] is None
        assert data["schemaAlignmentResults"] is None
        assert data["changeTracking"]["changes"][0]["changeId"] == "chg_001"
        assert data["changeTracking"]["summary"]["totalChanges"] == 1
        assert data["changeTracking"]["comparisonMetadata"]["detection_timestamp"] == "2025-01-01T12:00:00Z"


class TestErrorResponse:
    """Test cases for ErrorResponse model."""

    def test_error_response_valid(self):
        """Test creating a valid ErrorResponse."""
        response = ErrorResponse(detail="Validation failed", error_code="VALIDATION_ERROR", request_id="req_123456")

        assert response.detail == "Validation failed"
        assert response.error_code == "VALIDATION_ERROR"
        assert response.request_id == "req_123456"

    def test_error_response_without_error_code(self):
        """Test ErrorResponse without error code."""
        response = ErrorResponse(detail="Internal server error", request_id="req_123456")

        assert response.detail == "Internal server error"
        assert response.error_code is None
        assert response.request_id == "req_123456"

    def test_error_response_missing_required_fields(self):
        """Test ErrorResponse with missing required fields."""
        with pytest.raises(ValueError):
            ErrorResponse()

        with pytest.raises(ValueError):
            ErrorResponse(detail="Error message")

    def test_error_response_serialization(self):
        """Test ErrorResponse serialization."""
        response = ErrorResponse(detail="Validation failed", error_code="VALIDATION_ERROR", request_id="req_123456")

        data = response.model_dump()
        assert data["detail"] == "Validation failed"
        assert data["error_code"] == "VALIDATION_ERROR"
        assert data["request_id"] == "req_123456"


class TestFileValidationError:
    """Test cases for FileValidationError model."""

    def test_file_validation_error_valid(self):
        """Test creating a valid FileValidationError."""
        error = FileValidationError(
            field="file_size", message="File size exceeds maximum limit of 50MB", error_type="SIZE_LIMIT_EXCEEDED"
        )

        assert error.field == "file_size"
        assert error.message == "File size exceeds maximum limit of 50MB"
        assert error.error_type == "SIZE_LIMIT_EXCEEDED"

    def test_file_validation_error_missing_fields(self):
        """Test FileValidationError with missing required fields."""
        with pytest.raises(ValueError):
            FileValidationError()

        with pytest.raises(ValueError):
            FileValidationError(field="file_size")


class TestFileValidationRequest:
    """Test cases for FileValidationRequest model."""

    def test_file_validation_request_defaults(self):
        """Test FileValidationRequest with default values."""
        request = FileValidationRequest()

        assert request.max_size_mb == 50
        assert request.allowed_mime_types == ["text/csv", "application/csv"]
        assert request.required_extensions == [".csv"]

    def test_file_validation_request_custom_values(self):
        """Test FileValidationRequest with custom values."""
        request = FileValidationRequest(
            max_size_mb=100, allowed_mime_types=["text/csv"], required_extensions=[".csv", ".txt"]
        )

        assert request.max_size_mb == 100
        assert request.allowed_mime_types == ["text/csv"]
        assert request.required_extensions == [".csv", ".txt"]

    def test_file_validation_request_serialization(self):
        """Test FileValidationRequest serialization."""
        request = FileValidationRequest(max_size_mb=25)

        data = request.model_dump()
        assert data["max_size_mb"] == 25
        assert data["allowed_mime_types"] == ["text/csv", "application/csv"]
        assert data["required_extensions"] == [".csv"]


class TestFileValidationResponse:
    """Test cases for FileValidationResponse model."""

    def test_file_validation_response_valid_file(self):
        """Test FileValidationResponse for valid file."""
        response = FileValidationResponse(is_valid=True, file_size_mb=2.5, mime_type="text/csv")

        assert response.is_valid is True
        assert response.file_size_mb == 2.5
        assert response.mime_type == "text/csv"
        assert len(response.errors) == 0

    def test_file_validation_response_invalid_file(self):
        """Test FileValidationResponse for invalid file."""
        errors = [
            FileValidationError(
                field="file_size", message="File size exceeds maximum limit", error_type="SIZE_LIMIT_EXCEEDED"
            ),
            FileValidationError(field="mime_type", message="Invalid file type", error_type="INVALID_MIME_TYPE"),
        ]

        response = FileValidationResponse(is_valid=False, file_size_mb=75.0, mime_type="application/pdf", errors=errors)

        assert response.is_valid is False
        assert response.file_size_mb == 75.0
        assert response.mime_type == "application/pdf"
        assert len(response.errors) == 2
        assert response.errors[0].field == "file_size"
        assert response.errors[1].field == "mime_type"

    def test_file_validation_response_missing_fields(self):
        """Test FileValidationResponse with missing required fields."""
        with pytest.raises(ValueError):
            FileValidationResponse()

        with pytest.raises(ValueError):
            FileValidationResponse(is_valid=True)

    def test_file_validation_response_serialization(self):
        """Test FileValidationResponse serialization."""
        response = FileValidationResponse(is_valid=True, file_size_mb=2.5, mime_type="text/csv")

        data = response.model_dump()
        assert data["is_valid"] is True
        assert data["file_size_mb"] == 2.5
        assert data["mime_type"] == "text/csv"
        assert data["errors"] == []


class TestValidationErrorDetail:
    """Test cases for ValidationErrorDetail API model."""

    def test_validation_error_detail_basic(self):
        """Test creating a basic ValidationErrorDetail."""
        error = ValidationErrorDetail(
            row=1, column="participant_id", current_value="", error_type=ValidationErrorType.REQUIRED_VALUE
        )

        assert error.row == 1
        assert error.column == "participant_id"
        assert error.current_value == ""
        assert error.error_type == ValidationErrorType.REQUIRED_VALUE
        assert error.valid_options is None
        assert error.recommended_value is None
        assert error.error_message is None
        assert error.schema_field_name is None

    def test_validation_error_detail_with_custom_message(self):
        """Test ValidationErrorDetail with custom error message."""
        error = ValidationErrorDetail(
            row=2,
            column="library_strategy",
            current_value="Invalid",
            valid_options=["Amplicon"],
            recommended_value="Amplicon",
            error_type=ValidationErrorType.INVALID_OPTION,
            error_message='library_strategy is a required field. Valid input(s) are: ["Amplicon"]',
            schema_field_name="library_strategy",
        )

        assert error.row == 2
        assert error.column == "library_strategy"
        assert error.current_value == "Invalid"
        assert error.valid_options == ["Amplicon"]
        assert error.recommended_value == "Amplicon"
        assert error.error_type == ValidationErrorType.INVALID_OPTION
        assert error.error_message == 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
        assert error.schema_field_name == "library_strategy"

    def test_validation_error_detail_serialization(self):
        """Test ValidationErrorDetail serialization with camelCase aliases."""
        error = ValidationErrorDetail(
            row=3,
            column="sequence_id",
            current_value="invalid-format",
            error_type=ValidationErrorType.INVALID_PATTERN,
            error_message="sequence_id is a required field that must follow the proper formatting",
            schema_field_name="sequence_id",
        )

        data = error.model_dump(by_alias=True)
        expected = {
            "row": 3,
            "column": "sequence_id",
            "currentValue": "invalid-format",
            "validOptions": None,
            "recommendedValue": None,
            "errorType": "INVALID_PATTERN",
            "errorMessage": "sequence_id is a required field that must follow the proper formatting",
            "schemaFieldName": "sequence_id",
            "confidenceScore": None,
            "confidenceLevel": None,
            "correctionNode": None,
        }

        assert data == expected

    def test_validation_error_detail_deserialization(self):
        """Test ValidationErrorDetail deserialization from camelCase data."""
        data = {
            "row": 1,
            "column": "CSID",
            "currentValue": "123",
            "validOptions": None,
            "recommendedValue": None,
            "errorType": "INVALID_PATTERN",
            "errorMessage": "CSID is a required field and must be a ten-digit numerical string with no special characters",
            "schemaFieldName": "CSID",
        }

        error = ValidationErrorDetail(**data)

        assert error.row == 1
        assert error.column == "CSID"
        assert error.current_value == "123"
        assert error.error_type == ValidationErrorType.INVALID_PATTERN
        assert (
            error.error_message
            == "CSID is a required field and must be a ten-digit numerical string with no special characters"
        )
        assert error.schema_field_name == "CSID"

    def test_validation_error_detail_validation(self):
        """Test ValidationErrorDetail field validation."""
        # Test invalid row number
        with pytest.raises(ValueError):
            ValidationErrorDetail(
                row=0, column="test", current_value="test", error_type=ValidationErrorType.REQUIRED_VALUE
            )

        # Test empty column name
        with pytest.raises(ValueError):
            ValidationErrorDetail(row=1, column="", current_value="test", error_type=ValidationErrorType.REQUIRED_VALUE)


class TestValidationResultsSummary:
    """Test cases for ValidationResultsSummary API model."""

    def test_validation_results_summary_basic(self):
        """Test creating a basic ValidationResultsSummary."""
        summary = ValidationResultsSummary(
            total_rows=100,
            total_errors=5,
            error_types={
                ValidationErrorType.REQUIRED_VALUE: 2,
                ValidationErrorType.INVALID_OPTION: 2,
                ValidationErrorType.INVALID_PATTERN: 1,
            },
            columns_validated=3,
        )

        assert summary.total_rows == 100
        assert summary.total_errors == 5
        assert summary.error_types[ValidationErrorType.REQUIRED_VALUE] == 2
        assert summary.error_types[ValidationErrorType.INVALID_OPTION] == 2
        assert summary.error_types[ValidationErrorType.INVALID_PATTERN] == 1

    def test_validation_results_summary_serialization(self):
        """Test ValidationResultsSummary serialization with camelCase aliases."""
        summary = ValidationResultsSummary(
            total_rows=50,
            total_errors=3,
            error_types={ValidationErrorType.REQUIRED_VALUE: 1, ValidationErrorType.INVALID_OPTION: 2},
            columns_validated=2,
        )

        data = summary.model_dump(by_alias=True)
        expected = {
            "totalRows": 50,
            "totalErrors": 3,
            "errorTypes": {"REQUIRED_VALUE": 1, "INVALID_OPTION": 2},
            "columnsValidated": 2,
        }

        assert data == expected


class TestValidationResults:
    """Test cases for ValidationResults API model."""

    def test_validation_results_basic(self):
        """Test creating a basic ValidationResults."""
        error = ValidationErrorDetail(
            row=1,
            column="test_field",
            current_value="invalid",
            error_type=ValidationErrorType.INVALID_OPTION,
            valid_options=["valid1", "valid2"],
        )

        summary = ValidationResultsSummary(
            total_rows=10, total_errors=1, error_types={ValidationErrorType.INVALID_OPTION: 1}, columns_validated=1
        )

        results = ValidationResults(validation_results=[error], summary=summary)

        assert len(results.validation_results) == 1
        assert results.validation_results[0] == error
        assert results.summary == summary

    def test_validation_results_with_custom_messages(self):
        """Test ValidationResults with custom error messages."""
        errors = [
            ValidationErrorDetail(
                row=1,
                column="library_strategy",
                current_value="Invalid",
                valid_options=["Amplicon"],
                error_type=ValidationErrorType.INVALID_OPTION,
                error_message='library_strategy is a required field. Valid input(s) are: ["Amplicon"]',
                schema_field_name="library_strategy",
            ),
            ValidationErrorDetail(
                row=2,
                column="sequence_id",
                current_value="",
                error_type=ValidationErrorType.REQUIRED_VALUE,
                error_message="sequence_id is a required field that must follow the proper formatting",
                schema_field_name="sequence_id",
            ),
        ]

        summary = ValidationResultsSummary(
            total_rows=10,
            total_errors=2,
            error_types={ValidationErrorType.INVALID_OPTION: 1, ValidationErrorType.REQUIRED_VALUE: 1},
            columns_validated=2,
        )

        results = ValidationResults(validation_results=errors, summary=summary)

        assert len(results.validation_results) == 2
        assert (
            results.validation_results[0].error_message
            == 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
        )
        assert (
            results.validation_results[1].error_message
            == "sequence_id is a required field that must follow the proper formatting"
        )
        assert results.summary.total_errors == 2

    def test_validation_results_serialization(self):
        """Test ValidationResults serialization with camelCase aliases."""
        error = ValidationErrorDetail(
            row=1,
            column="test_field",
            current_value="test",
            error_type=ValidationErrorType.REQUIRED_VALUE,
            error_message="Custom error message",
            schema_field_name="testField",
        )

        summary = ValidationResultsSummary(
            total_rows=1, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
        )

        results = ValidationResults(validation_results=[error], summary=summary)

        data = results.model_dump(by_alias=True)

        assert "validationResults" in data
        assert "summary" in data
        assert len(data["validationResults"]) == 1
        assert data["validationResults"][0]["errorMessage"] == "Custom error message"
        assert data["validationResults"][0]["schemaFieldName"] == "testField"
        assert data["summary"]["totalRows"] == 1
        assert data["summary"]["totalErrors"] == 1
