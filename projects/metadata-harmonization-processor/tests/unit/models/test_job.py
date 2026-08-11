# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for job models.

Tests the job-related Pydantic models including JobResults, ProgramSchema,
MetadataSchema, and MetadataUploadJob with various scenarios including
both S3 and local storage configurations.
"""


import pytest

from metadata_harmonization_processor.models.job import (
    JobResults,
    MetadataSchema,
    MetadataUploadJob,
    ProgramSchema,
)


class TestJobResults:
    """Test JobResults model for result storage information."""

    def test_s3_job_results_success(self):
        """Test successful S3 JobResults creation."""
        job_results = JobResults(
            storage_type="s3",
            location="validation-results/job-123/v1/results.json",
            bucket="my-results-bucket",
        )

        assert job_results.storage_type == "s3"
        assert job_results.location == "validation-results/job-123/v1/results.json"
        assert job_results.bucket == "my-results-bucket"

    def test_s3_job_results_validation_failure(self):
        """Test S3 JobResults validation fails without bucket."""
        with pytest.raises(ValueError, match="bucket is required when storage_type is 's3'"):
            JobResults(storage_type="s3", location="validation-results/job-123/v1/results.json")

    def test_local_job_results_success(self):
        """Test successful local JobResults creation."""
        job_results = JobResults(
            storage_type="local",
            location="/tmp/validation-results/job-123-v1-results.json",
        )

        assert job_results.storage_type == "local"
        assert job_results.location == "/tmp/validation-results/job-123-v1-results.json"
        assert job_results.bucket is None

    def test_local_job_results_with_bucket(self):
        """Test local JobResults can have bucket field (ignored for local storage)."""
        job_results = JobResults(
            storage_type="local",
            location="/tmp/validation-results/job-123-v1-results.json",
            bucket="ignored-for-local",
        )

        assert job_results.storage_type == "local"
        assert job_results.location == "/tmp/validation-results/job-123-v1-results.json"
        assert job_results.bucket == "ignored-for-local"

    def test_job_results_serialization(self):
        """Test JobResults serialization to dict."""
        job_results = JobResults(
            storage_type="s3",
            location="validation-results/job-123/v1/results.json",
            bucket="my-results-bucket",
        )

        data = job_results.model_dump()

        expected = {
            "storage_type": "s3",
            "location": "validation-results/job-123/v1/results.json",
            "bucket": "my-results-bucket",
        }

        assert data == expected

    def test_job_results_deserialization(self):
        """Test JobResults deserialization from dict."""
        data = {
            "storage_type": "local",
            "location": "/tmp/validation-results/job-123-v1-results.json",
        }

        job_results = JobResults(**data)

        assert job_results.storage_type == "local"
        assert job_results.location == "/tmp/validation-results/job-123-v1-results.json"
        assert job_results.bucket is None


class TestProgramSchema:
    """Test ProgramSchema model for program schema information."""

    def test_program_schema_creation(self):
        """Test successful ProgramSchema creation."""
        program_schema = ProgramSchema(
            program_name="Cyclospora Program Schema",
            s3_location="schemas/cyclospora_program_schema.json",
            s3_bucket="metadata-schemas-bucket",
            program_schema_id="cyclospora-program-v1",
        )

        assert program_schema.program_name == "Cyclospora Program Schema"
        assert program_schema.s3_location == "schemas/cyclospora_program_schema.json"
        assert program_schema.s3_bucket == "metadata-schemas-bucket"
        assert program_schema.program_schema_id == "cyclospora-program-v1"

    def test_program_schema_serialization(self):
        """Test ProgramSchema serialization to dict."""
        program_schema = ProgramSchema(
            program_name="Flu Program Schema",
            s3_location="schemas/flu_program_schema.json",
            s3_bucket="metadata-schemas-bucket",
            program_schema_id="flu-program-v2",
        )

        data = program_schema.model_dump()

        expected = {
            "program_name": "Flu Program Schema",
            "s3_location": "schemas/flu_program_schema.json",
            "s3_bucket": "metadata-schemas-bucket",
            "program_schema_id": "flu-program-v2",
        }

        assert data == expected


class TestMetadataSchema:
    """Test MetadataSchema model for DynamoDB schema storage."""

    def test_metadata_schema_creation(self):
        """Test successful MetadataSchema creation."""
        program_schemas = [
            ProgramSchema(
                program_name="Cyclospora Program Schema",
                s3_location="schemas/cyclospora_program_schema.json",
                s3_bucket="metadata-schemas-bucket",
                program_schema_id="cyclospora-program-v1",
            )
        ]

        schema = MetadataSchema(
            core_schema_id="core_v1",
            name="Core Schema v1",
            core_schema_path="schemas/core_schema_v1.json",
            core_schema_s3_bucket="metadata-schemas-bucket",
            program_schemas=program_schemas,
        )

        assert schema.core_schema_id == "core_v1"
        assert schema.name == "Core Schema v1"
        assert schema.core_schema_path == "schemas/core_schema_v1.json"
        assert schema.core_schema_s3_bucket == "metadata-schemas-bucket"
        assert len(schema.program_schemas) == 1
        assert schema.program_schemas[0].program_name == "Cyclospora Program Schema"

    def test_metadata_schema_empty_program_schemas(self):
        """Test MetadataSchema with empty program schemas list."""
        schema = MetadataSchema(
            core_schema_id="core_v1",
            name="Core Schema v1",
            core_schema_path="schemas/core_schema_v1.json",
            core_schema_s3_bucket="metadata-schemas-bucket",
        )

        assert len(schema.program_schemas) == 0

    def test_metadata_schema_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValueError):
            MetadataSchema()

        with pytest.raises(ValueError):
            MetadataSchema(core_schema_id="core_v1")

    def test_metadata_schema_serialization(self):
        """Test MetadataSchema serialization."""
        program_schemas = [
            ProgramSchema(
                program_name="Flu Program Schema",
                s3_location="schemas/flu_program_schema.json",
                s3_bucket="metadata-schemas-bucket",
                program_schema_id="flu-program-v1",
            )
        ]

        schema = MetadataSchema(
            core_schema_id="core_v1",
            name="Core Schema v1",
            core_schema_path="schemas/core_schema_v1.json",
            core_schema_s3_bucket="metadata-schemas-bucket",
            program_schemas=program_schemas,
        )

        data = schema.model_dump()

        expected = {
            "core_schema_id": "core_v1",
            "name": "Core Schema v1",
            "core_schema_path": "schemas/core_schema_v1.json",
            "core_schema_s3_bucket": "metadata-schemas-bucket",
            "program_schemas": [
                {
                    "program_name": "Flu Program Schema",
                    "s3_location": "schemas/flu_program_schema.json",
                    "s3_bucket": "metadata-schemas-bucket",
                    "program_schema_id": "flu-program-v1",
                }
            ],
        }

        assert data == expected


class TestMetadataUploadJob:
    """Test MetadataUploadJob model for job tracking."""

    def test_metadata_upload_job_creation(self):
        """Test successful MetadataUploadJob creation."""
        job = MetadataUploadJob(
            job_id="job-123",
            user_id="user-456",
            core_schema_id="core-schema-v1",
            program_schema_id="program-schema-v1",
            status="pending",
            created_at="2024-01-15T10:30:00Z",
        )

        assert job.job_id == "job-123"
        assert job.user_id == "user-456"
        assert job.core_schema_id == "core-schema-v1"
        assert job.program_schema_id == "program-schema-v1"
        assert job.status == "pending"
        assert job.created_at == "2024-01-15T10:30:00Z"
        assert job.completed_at is None
        assert job.current_version == 1
        assert job.results == {}

    def test_metadata_upload_job_with_results(self):
        """Test MetadataUploadJob with results."""
        s3_results = JobResults(
            storage_type="s3",
            location="validation-results/job-123/v1/results.json",
            bucket="results-bucket",
        )

        local_results = JobResults(
            storage_type="local",
            location="/tmp/validation-results/job-123-v2-results.json",
        )

        job = MetadataUploadJob(
            job_id="job-123",
            user_id="user-456",
            core_schema_id="core-schema-v1",
            program_schema_id="program-schema-v1",
            status="completed",
            created_at="2024-01-15T10:30:00Z",
            completed_at="2024-01-15T10:45:00Z",
            current_version=2,
            results={"1": s3_results, "2": local_results},
        )

        assert job.current_version == 2
        assert len(job.results) == 2
        assert job.results["1"].storage_type == "s3"
        assert job.results["1"].bucket == "results-bucket"
        assert job.results["2"].storage_type == "local"
        assert job.results["2"].bucket is None

    def test_metadata_upload_job_status_progression(self):
        """Test MetadataUploadJob status progression."""
        # Start with pending job
        job = MetadataUploadJob(
            job_id="job-123",
            user_id="user-456",
            core_schema_id="core-schema-v1",
            program_schema_id="program-schema-v1",
            status="pending",
            created_at="2024-01-15T10:30:00Z",
        )

        assert job.status == "pending"
        assert job.completed_at is None

        # Update to processing
        job.status = "processing"
        assert job.status == "processing"

        # Complete the job
        job.status = "completed"
        job.completed_at = "2024-01-15T10:45:00Z"

        assert job.status == "completed"
        assert job.completed_at == "2024-01-15T10:45:00Z"

    def test_metadata_upload_job_serialization(self):
        """Test MetadataUploadJob serialization to dict."""
        results = JobResults(
            storage_type="s3",
            location="validation-results/job-123/v1/results.json",
            bucket="results-bucket",
        )

        job = MetadataUploadJob(
            job_id="job-123",
            user_id="user-456",
            core_schema_id="core-schema-v1",
            program_schema_id="program-schema-v1",
            status="completed",
            created_at="2024-01-15T10:30:00Z",
            completed_at="2024-01-15T10:45:00Z",
            current_version=1,
            results={"1": results},
        )

        data = job.model_dump()

        assert data["job_id"] == "job-123"
        assert data["status"] == "completed"
        assert data["current_version"] == 1
        assert "1" in data["results"]
        assert data["results"]["1"]["storage_type"] == "s3"

    def test_metadata_upload_job_deserialization(self):
        """Test MetadataUploadJob deserialization from dict."""
        data = {
            "job_id": "job-123",
            "user_id": "user-456",
            "core_schema_id": "core-schema-v1",
            "program_schema_id": "program-schema-v1",
            "status": "completed",
            "created_at": "2024-01-15T10:30:00Z",
            "completed_at": "2024-01-15T10:45:00Z",
            "current_version": 1,
            "results": {
                "1": {
                    "storage_type": "s3",
                    "location": "validation-results/job-123/v1/results.json",
                    "bucket": "results-bucket",
                }
            },
        }

        job = MetadataUploadJob(**data)

        assert job.job_id == "job-123"
        assert job.status == "completed"
        assert job.current_version == 1
        assert len(job.results) == 1
        assert job.results["1"].storage_type == "s3"
        assert job.results["1"].bucket == "results-bucket"

    def test_metadata_upload_job_version_increment(self):
        """Test MetadataUploadJob version increment scenario."""
        # Create initial job
        job = MetadataUploadJob(
            job_id="job-123",
            user_id="user-456",
            core_schema_id="core-schema-v1",
            program_schema_id="program-schema-v1",
            status="completed",
            created_at="2024-01-15T10:30:00Z",
            completed_at="2024-01-15T10:45:00Z",
            current_version=1,
            results={
                "1": JobResults(
                    storage_type="s3",
                    location="validation-results/job-123/v1/results.json",
                    bucket="results-bucket",
                )
            },
        )

        # Simulate resubmission with new version
        job.current_version = 2
        job.status = "processing"
        job.completed_at = None

        # Add new results for version 2
        job.results["2"] = JobResults(
            storage_type="s3",
            location="validation-results/job-123/v2/results.json",
            bucket="results-bucket",
        )

        # Complete version 2
        job.status = "completed"
        job.completed_at = "2024-01-15T11:00:00Z"

        assert job.current_version == 2
        assert len(job.results) == 2
        assert "1" in job.results
        assert "2" in job.results
        assert job.status == "completed"
