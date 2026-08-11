# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for core data models."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from metadata_harmonization_processor.models.job import ProgramSchema, MetadataUploadJob, JobResults, MetadataSchema
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class TestProgramSchema:
    """Test cases for ProgramSchema model."""

    def test_program_schema_creation(self):
        """Test creating a valid ProgramSchema."""
        program_schema = ProgramSchema(
            program_name="Test Program",
            s3_location="schemas/programs/test/v1.0/schema.json",
            s3_bucket="test-schemas",
            program_schema_id="test_program_v1",
        )

        assert program_schema.program_name == "Test Program"
        assert program_schema.s3_location == "schemas/programs/test/v1.0/schema.json"
        assert program_schema.s3_bucket == "test-schemas"
        assert program_schema.program_schema_id == "test_program_v1"

    def test_program_schema_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            ProgramSchema()

        with pytest.raises(ValueError):
            ProgramSchema(program_name="Test")

    def test_program_schema_serialization(self):
        """Test ProgramSchema serialization."""
        program_schema = ProgramSchema(
            program_name="Test Program",
            s3_location="schemas/programs/test/v1.0/schema.json",
            s3_bucket="test-schemas",
            program_schema_id="test_program_v1",
        )

        data = program_schema.model_dump()
        assert data["program_name"] == "Test Program"
        assert data["s3_location"] == "schemas/programs/test/v1.0/schema.json"
        assert data["s3_bucket"] == "test-schemas"
        assert data["program_schema_id"] == "test_program_v1"


class TestMetadataSchema:
    """Test cases for MetadataSchema model."""

    def test_metadata_schema_creation(self):
        """Test creating a valid MetadataSchema."""
        program_schemas = [
            ProgramSchema(
                program_name="Cancer Registry",
                s3_location="schemas/programs/cancer/v1.0/schema.json",
                s3_bucket="test-schemas",
                program_schema_id="cancer_v1",
            )
        ]

        schema = MetadataSchema(
            core_schema_id="core_v1",
            name="Core Schema v1",
            core_schema_path="schemas/core/v1.0/schema.json",
            core_schema_s3_bucket="test-schemas",
            program_schemas=program_schemas,
        )

        assert schema.core_schema_id == "core_v1"
        assert schema.name == "Core Schema v1"
        assert schema.core_schema_path == "schemas/core/v1.0/schema.json"
        assert schema.core_schema_s3_bucket == "test-schemas"
        assert len(schema.program_schemas) == 1
        assert schema.program_schemas[0].program_name == "Cancer Registry"

    def test_metadata_schema_empty_program_schemas(self):
        """Test MetadataSchema with empty program schemas list."""
        schema = MetadataSchema(
            core_schema_id="core_v1",
            name="Core Schema v1",
            core_schema_path="schemas/core/v1.0/schema.json",
            core_schema_s3_bucket="test-schemas",
        )

        assert len(schema.program_schemas) == 0

    def test_metadata_schema_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            MetadataSchema()

        with pytest.raises(ValueError):
            MetadataSchema(core_schema_id="core_v1")

    def test_metadata_schema_serialization(self):
        """Test MetadataSchema serialization."""
        program_schemas = [
            ProgramSchema(
                program_name="Cancer Registry",
                s3_location="schemas/programs/cancer/v1.0/schema.json",
                s3_bucket="test-schemas",
                program_schema_id="cancer_v1",
            )
        ]

        schema = MetadataSchema(
            core_schema_id="core_v1",
            name="Core Schema v1",
            core_schema_path="schemas/core/v1.0/schema.json",
            core_schema_s3_bucket="test-schemas",
            program_schemas=program_schemas,
        )

        data = schema.model_dump()
        assert data["core_schema_id"] == "core_v1"
        assert data["name"] == "Core Schema v1"
        assert len(data["program_schemas"]) == 1
        assert data["program_schemas"][0]["program_name"] == "Cancer Registry"


class TestJobResults:
    """Test cases for JobResults model."""

    def test_job_results_creation(self):
        """Test creating a valid JobResults."""
        results = JobResults(
            storage_type="s3", location="results/job123/v1/validation_results.json", bucket="validation-results"
        )

        assert results.storage_type == "s3"
        assert results.location == "results/job123/v1/validation_results.json"
        assert results.bucket == "validation-results"

    def test_job_results_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            JobResults()

        with pytest.raises(ValueError):
            JobResults(s3_location="test")


class TestMetadataUploadJob:
    """Test cases for MetadataUploadJob model."""

    def test_metadata_upload_job_creation(self):
        """Test creating a valid MetadataUploadJob."""
        job_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        job = MetadataUploadJob(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            status="pending",
            created_at=created_at,
        )

        assert job.job_id == job_id
        assert job.user_id == "test_user_123"
        assert job.core_schema_id == "core_v1"
        assert job.program_schema_id == "cancer_v1"
        assert job.status == "pending"
        assert job.created_at == created_at
        assert job.completed_at is None
        assert job.current_version == 1
        assert len(job.results) == 0

    def test_metadata_upload_job_with_results(self):
        """Test MetadataUploadJob with results."""
        job_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        completed_at = datetime.now(timezone.utc).isoformat()

        results = {
            "1": JobResults(
                storage_type="s3", location="results/job123/v1/validation_results.json", bucket="validation-results"
            ),
            "2": JobResults(
                storage_type="s3", location="results/job123/v2/validation_results.json", bucket="validation-results"
            ),
        }

        job = MetadataUploadJob(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            status="completed",
            created_at=created_at,
            completed_at=completed_at,
            current_version=2,
            results=results,
        )

        assert job.status == "completed"
        assert job.completed_at == completed_at
        assert job.current_version == 2
        assert len(job.results) == 2
        assert "1" in job.results
        assert "2" in job.results
        assert job.results["1"].location == "results/job123/v1/validation_results.json"
        assert job.results["1"].storage_type == "s3"
        assert job.results["1"].bucket == "validation-results"

    def test_metadata_upload_job_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            MetadataUploadJob()

        with pytest.raises(ValueError):
            MetadataUploadJob(job_id="test")

    def test_metadata_upload_job_serialization(self):
        """Test MetadataUploadJob serialization."""
        job_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        job = MetadataUploadJob(
            job_id=job_id,
            user_id="test_user_123",
            core_schema_id="core_v1",
            program_schema_id="cancer_v1",
            status="pending",
            created_at=created_at,
        )

        data = job.model_dump()
        assert data["job_id"] == job_id
        assert data["user_id"] == "test_user_123"
        assert data["status"] == "pending"
        assert data["current_version"] == 1
        assert data["results"] == {}


class TestValidationErrorType:
    """Test cases for ValidationErrorType enum."""

    def test_validation_error_type_values(self):
        """Test ValidationErrorType enum values."""
        assert ValidationErrorType.REQUIRED_VALUE == "REQUIRED_VALUE"
        assert ValidationErrorType.INVALID_OPTION == "INVALID_OPTION"

    def test_validation_error_type_membership(self):
        """Test ValidationErrorType membership."""
        assert "REQUIRED_VALUE" in ValidationErrorType
        assert "INVALID_OPTION" in ValidationErrorType
        assert "UNKNOWN_ERROR" not in ValidationErrorType


class TestValidationErrorDetail:
    """Test cases for ValidationErrorDetail model."""

    def test_validation_error_detail_creation(self):
        """Test creating a valid ValidationErrorDetail."""
        error = ValidationErrorDetail(
            row=1, column="participant_id", current_value="", error_type=ValidationErrorType.REQUIRED_VALUE
        )

        assert error.row == 1
        assert error.column == "participant_id"
        assert error.current_value == ""
        assert error.error_type == ValidationErrorType.REQUIRED_VALUE
        assert error.valid_options is None
        assert error.recommended_value is None

    def test_validation_error_detail_with_options(self):
        """Test ValidationErrorDetail with valid options and recommendation."""
        error = ValidationErrorDetail(
            row=5,
            column="city",
            current_value="NYC",
            valid_options=["New York City", "Brooklyn", "Queens"],
            recommended_value="New York City",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        assert error.row == 5
        assert error.column == "city"
        assert error.current_value == "NYC"
        assert error.valid_options == ["New York City", "Brooklyn", "Queens"]
        assert error.recommended_value == "New York City"
        assert error.error_type == ValidationErrorType.INVALID_OPTION

    def test_validation_error_detail_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            ValidationErrorDetail()

        with pytest.raises(ValueError):
            ValidationErrorDetail(row=1)

    def test_validation_error_detail_serialization(self):
        """Test ValidationErrorDetail serialization."""
        error = ValidationErrorDetail(
            row=1, column="participant_id", current_value="", error_type=ValidationErrorType.REQUIRED_VALUE
        )

        data = error.model_dump()
        assert data["row"] == 1
        assert data["column"] == "participant_id"
        assert data["current_value"] == ""
        assert data["error_type"] == "REQUIRED_VALUE"
        assert data["valid_options"] is None
        assert data["recommended_value"] is None


class TestValidationResultsSummary:
    """Test cases for ValidationResultsSummary model."""

    def test_validation_results_summary_creation(self):
        """Test creating a valid ValidationResultsSummary."""
        summary = ValidationResultsSummary(
            total_rows=100,
            total_errors=15,
            error_types={ValidationErrorType.REQUIRED_VALUE: 8, ValidationErrorType.INVALID_OPTION: 7},
            columns_validated=3,
        )

        assert summary.total_rows == 100
        assert summary.total_errors == 15
        assert len(summary.error_types) == 2
        assert summary.error_types[ValidationErrorType.REQUIRED_VALUE] == 8
        assert summary.error_types[ValidationErrorType.INVALID_OPTION] == 7

    def test_validation_results_summary_empty_errors(self):
        """Test ValidationResultsSummary with no errors."""
        summary = ValidationResultsSummary(total_rows=100, total_errors=0, error_types={}, columns_validated=0)

        assert summary.total_rows == 100
        assert summary.total_errors == 0
        assert len(summary.error_types) == 0

    def test_validation_results_summary_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            ValidationResultsSummary()

        with pytest.raises(ValueError):
            ValidationResultsSummary(total_rows=100)


class TestValidationResults:
    """Test cases for ValidationResults model."""

    def test_validation_results_creation(self):
        """Test creating a valid ValidationResults."""
        errors = [
            ValidationErrorDetail(
                row=1, column="participant_id", current_value="", error_type=ValidationErrorType.REQUIRED_VALUE
            ),
            ValidationErrorDetail(
                row=5,
                column="city",
                current_value="NYC",
                recommended_value="New York City",
                error_type=ValidationErrorType.INVALID_OPTION,
            ),
        ]

        summary = ValidationResultsSummary(
            total_rows=100,
            total_errors=2,
            error_types={ValidationErrorType.REQUIRED_VALUE: 1, ValidationErrorType.INVALID_OPTION: 1},
            columns_validated=2,
        )

        results = ValidationResults(validation_results=errors, summary=summary)

        assert len(results.validation_results) == 2
        assert results.validation_results[0].row == 1
        assert results.validation_results[1].row == 5
        assert results.summary.total_rows == 100
        assert results.summary.total_errors == 2

    def test_validation_results_empty(self):
        """Test ValidationResults with no errors."""
        summary = ValidationResultsSummary(total_rows=100, total_errors=0, error_types={}, columns_validated=0)

        results = ValidationResults(validation_results=[], summary=summary)

        assert len(results.validation_results) == 0
        assert results.summary.total_errors == 0

    def test_validation_results_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            ValidationResults()

        with pytest.raises(ValueError):
            ValidationResults(validation_results=[])

    def test_validation_results_serialization(self):
        """Test ValidationResults serialization."""
        errors = [
            ValidationErrorDetail(
                row=1, column="participant_id", current_value="", error_type=ValidationErrorType.REQUIRED_VALUE
            )
        ]

        summary = ValidationResultsSummary(
            total_rows=100, total_errors=1, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
        )

        results = ValidationResults(validation_results=errors, summary=summary)

        data = results.model_dump()
        assert len(data["validation_results"]) == 1
        assert data["validation_results"][0]["row"] == 1
        assert data["summary"]["total_rows"] == 100
        assert data["summary"]["total_errors"] == 1
