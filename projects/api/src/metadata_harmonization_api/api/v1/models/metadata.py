# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""API request/response models for metadata validation endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from metadata_harmonization_processor.models.validation import ValidationResults
from metadata_harmonization_processor.models.change_tracking import ChangeTrackingResults


class SchemaAlignmentChangeDetail(BaseModel):
    """Model for individual schema alignment change details."""

    model_config = ConfigDict(populate_by_name=True)

    change_type: str = Field(..., alias="changeType", description="Type of change: 'add', 'remove', 'rename'")
    original_column: Optional[str] = Field(
        None, alias="originalColumn", description="Original column name (for rename/remove)"
    )
    new_column: Optional[str] = Field(None, alias="newColumn", description="New column name (for rename/add)")
    reason: Optional[str] = Field(None, description="Reason for the change")
    row_count_affected: Optional[int] = Field(
        None, alias="rowCountAffected", description="Number of rows affected by this change"
    )
    confidence_score: float = Field(
        default=0.0,
        alias="confidenceScore",
        description="Numerical confidence score between 0.0 and 1.0 for the schema alignment change",
        ge=0.0,
        le=1.0,
    )
    confidence_level: str = Field(
        default="Low", alias="confidenceLevel", description="Human-readable confidence level: High, Medium, or Low"
    )
    llm_confidence_level: Optional[str] = Field(
        None,
        alias="llmConfidenceLevel",
        description="Original confidence level from LLM response: High, Medium, or Low",
    )


class SchemaAlignmentResultsSummary(BaseModel):
    """Model for schema alignment results summary."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId", description="Job identifier")
    version: int = Field(..., description="Version number")
    timestamp: datetime = Field(..., description="When results were created")

    original_data_csv: str = Field(..., alias="originalDataCsv", description="Original CSV data")
    aligned_data_csv: str = Field(..., alias="alignedDataCsv", description="Schema-aligned CSV data")

    total_changes: int = Field(0, alias="totalChanges", description="Total number of schema changes")
    columns_renamed: int = Field(0, alias="columnsRenamed", description="Number of columns renamed")
    columns_added: int = Field(0, alias="columnsAdded", description="Number of columns added")
    columns_removed: int = Field(0, alias="columnsRemoved", description="Number of columns removed")
    rows_original: int = Field(0, alias="rowsOriginal", description="Number of rows in original data")
    rows_aligned: int = Field(0, alias="rowsAligned", description="Number of rows in aligned data")


class SchemaAlignmentResults(BaseModel):
    """Model for schema alignment results data."""

    model_config = ConfigDict(populate_by_name=True)

    schema_alignment_results: List[SchemaAlignmentChangeDetail] = Field(
        default_factory=list, alias="schemaAlignmentResults", description="List of detailed schema alignment changes"
    )
    summary: SchemaAlignmentResultsSummary = Field(..., description="Summary of schema alignment results")


class ValidationCreateRequest(BaseModel):
    """Request model for creating a new metadata validation job."""

    model_config = ConfigDict(populate_by_name=True)

    core_schema_id: str = Field(..., alias="coreSchemaId", description="Core schema identifier for validation")
    program_schema_id: str = Field(..., alias="programSchemaId", description="Program schema identifier for validation")


class ValidationJobResponse(BaseModel):
    """Response model for validation job creation and updates."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: UUID = Field(..., alias="jobId", description="Unique identifier for the validation job")


class CombinedResults(BaseModel):
    """Combined results containing both validation and schema alignment data."""

    model_config = ConfigDict(populate_by_name=True)

    validation_results: Optional[ValidationResults] = Field(
        None, alias="validationResults", description="Validation results data"
    )
    schema_alignment_results: Optional[SchemaAlignmentResults] = Field(
        None, alias="schemaAlignmentResults", description="Schema alignment transformation data"
    )
    change_tracking: Optional[ChangeTrackingResults] = Field(
        None, alias="changeTracking", description="Change tracking information between versions"
    )


class ValidationStatusResponse(BaseModel):
    """Response model for validation job status queries with unified storage."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: UUID = Field(..., alias="jobId", description="Unique identifier for the validation job")
    user_id: str = Field(..., alias="userId", description="User identifier who created the job")
    core_schema_id: str = Field(..., alias="coreSchemaId", description="Core schema used for validation")
    program_schema_id: str = Field(..., alias="programSchemaId", description="Program schema used for validation")
    status: str = Field(
        ..., description="Current job status: pending|processing|completed|completed_with_errors|failed"
    )
    created_at: datetime = Field(..., alias="createdAt", description="Timestamp when job was created")
    completed_at: Optional[datetime] = Field(None, alias="completedAt", description="Timestamp when job completed")
    current_version: int = Field(..., alias="currentVersion", description="Current version number of the job")
    latest_results: Optional[CombinedResults] = Field(
        None,
        alias="latestResults",
        description="Combined validation and schema alignment results (only present when status is completed)",
    )


class ProgramSchemaInfo(BaseModel):
    """Information about a program schema for UI selection."""

    model_config = ConfigDict(populate_by_name=True)

    program_name: str = Field(..., alias="programName", description="Human-readable name of the program")
    s3_location: str = Field(..., alias="s3Location", description="S3 path to the program schema file")
    s3_bucket: str = Field(..., alias="s3Bucket", description="S3 bucket containing the program schema")
    program_schema_id: str = Field(..., alias="programSchemaId", description="Unique identifier for the program schema")


class SchemaInfo(BaseModel):
    """Information about available schemas for UI selection."""

    model_config = ConfigDict(populate_by_name=True)

    core_schema_id: str = Field(..., alias="coreSchemaId", description="Unique identifier for the core schema")
    name: str = Field(..., description="Human-readable name of the core schema")
    core_schema_path: str = Field(..., alias="coreSchemaPath", description="Path to the core schema file")
    core_schema_s3_bucket: str = Field(
        ..., alias="coreSchemaS3Bucket", description="S3 bucket containing the core schema"
    )
    program_schemas: List[ProgramSchemaInfo] = Field(
        ..., alias="programSchemas", description="List of associated program schemas"
    )


class ErrorResponse(BaseModel):
    """Standard error response model for consistent API error handling."""

    model_config = ConfigDict(populate_by_name=True)

    detail: str = Field(..., description="Human-readable error message")
    error_code: Optional[str] = Field(None, alias="errorCode", description="Machine-readable error code")
    request_id: str = Field(..., alias="requestId", description="Unique identifier for the request")


class FileValidationError(BaseModel):
    """Error model for file validation failures."""

    model_config = ConfigDict(populate_by_name=True)

    field: str = Field(..., description="Field name that caused the validation error")
    message: str = Field(..., description="Detailed error message")
    error_type: str = Field(..., alias="errorType", description="Type of validation error")


class FileValidationRequest(BaseModel):
    """Model for CSV file upload validation constraints."""

    model_config = ConfigDict(populate_by_name=True)

    max_size_mb: int = Field(default=50, alias="maxSizeMb", description="Maximum file size in megabytes")
    allowed_mime_types: List[str] = Field(
        default=["text/csv", "application/csv"],
        alias="allowedMimeTypes",
        description="Allowed MIME types for uploaded files",
    )
    required_extensions: List[str] = Field(
        default=[".csv"], alias="requiredExtensions", description="Required file extensions"
    )


class FileValidationResponse(BaseModel):
    """Response model for file validation results."""

    model_config = ConfigDict(populate_by_name=True)

    is_valid: bool = Field(..., alias="isValid", description="Whether the file passed validation")
    file_size_mb: float = Field(..., alias="fileSizeMb", description="Actual file size in megabytes")
    mime_type: str = Field(..., alias="mimeType", description="Detected MIME type of the file")
    errors: List[FileValidationError] = Field(
        default_factory=list, description="List of validation errors if file is invalid"
    )
