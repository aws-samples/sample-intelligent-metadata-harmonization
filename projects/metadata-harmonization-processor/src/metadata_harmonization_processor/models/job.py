# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Job models for metadata harmonization processing.

This module contains Pydantic models for job management, result storage,
and schema information used throughout the metadata harmonization system.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobResults(BaseModel):
    """Results storage information for a specific job version.

    Supports both S3 and local storage backends with appropriate
    location information for each storage type.
    """

    model_config = ConfigDict(populate_by_name=True)

    storage_type: Literal["s3", "local"] = Field(
        ..., alias="storageType", description="Type of storage backend used for results"
    )
    location: str = Field(..., description="Storage location - S3 key path or local file path")
    bucket: Optional[str] = Field(None, description="S3 bucket name (required for S3 storage type)")

    def model_post_init(self, __context) -> None:
        """Validate storage configuration after initialization."""
        if self.storage_type == "s3" and not self.bucket:
            raise ValueError("bucket is required when storage_type is 's3'")


class ProgramSchema(BaseModel):
    """Program schema information within a core schema."""

    model_config = ConfigDict(populate_by_name=True)

    program_name: str = Field(..., alias="programName", description="Name of the program schema")
    s3_location: str = Field(..., alias="s3Location", description="S3 path to the program schema file")
    s3_bucket: str = Field(..., alias="s3Bucket", description="S3 bucket containing the program schema")
    program_schema_id: str = Field(
        ...,
        alias="programSchemaId",
        description="Unique identifier for the program schema",
    )


class MetadataSchema(BaseModel):
    """Model for METADATA_SCHEMAS_TABLE DynamoDB structure.

    This model represents the schema storage structure in DynamoDB.
    It contains core schema information and associated program schemas.
    """

    model_config = ConfigDict(populate_by_name=True)

    core_schema_id: str = Field(
        ...,
        alias="coreSchemaId",
        description="Partition key - unique identifier for core schema",
    )
    name: str = Field(..., description="Human-readable name of the schema")
    core_schema_path: str = Field(..., alias="coreSchemaPath", description="Path to the core schema file")
    core_schema_s3_bucket: str = Field(
        ...,
        alias="coreSchemaS3Bucket",
        description="S3 bucket containing the core schema",
    )
    program_schemas: List[ProgramSchema] = Field(
        default_factory=list,
        alias="programSchemas",
        description="List of associated program schemas",
    )


class MetadataUploadJob(BaseModel):
    """Model for METADATA_UPLOAD_JOB DynamoDB structure.

    Tracks job status, version history, and results storage locations
    for metadata processing jobs.
    """

    job_id: str = Field(..., alias="jobId", description="Partition key - UUID string for the job")
    user_id: str = Field(..., alias="userId", description="User identifier from authentication")
    core_schema_id: str = Field(..., alias="coreSchemaId", description="Core schema used for validation")
    program_schema_id: str = Field(..., alias="programSchemaId", description="Program schema used for validation")
    status: Literal["pending", "processing", "completed", "failed", "completed_with_errors"] = Field(
        ...,
        description="Job status: pending|processing|completed|failed|completed_with_errors",
    )
    created_at: str = Field(..., alias="createdAt", description="ISO-8601 timestamp when job was created")
    completed_at: Optional[str] = Field(
        None,
        alias="completedAt",
        description="ISO-8601 timestamp when job completed (null if not completed)",
    )
    current_version: int = Field(
        default=1,
        alias="currentVersion",
        description="Current version number, incremented for resubmissions",
    )
    results: Dict[str, JobResults] = Field(
        default_factory=dict,
        description="Results for each version, keyed by version number as string",
    )

    model_config = ConfigDict(populate_by_name=True)
