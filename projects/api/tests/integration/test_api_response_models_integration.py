# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for API response models with unified storage structure."""

from datetime import datetime, timezone
from uuid import uuid4

from metadata_harmonization_api.api.v1.models.metadata import (
    ValidationStatusResponse,
    CombinedResults,
    SchemaAlignmentResults,
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResultsSummary,
)
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResultsSummary,
)


def test_validation_status_response_with_combined_results_serialization():
    """Test ValidationStatusResponse serialization with CombinedResults."""
    # Create sample validation results
    validation_results = ValidationResults(
        validation_results=[
            ValidationErrorDetail(
                row=1,
                column="patient_id",
                current_value="",
                error_type=ValidationErrorType.REQUIRED_VALUE,
                valid_options=None,
                recommended_value="PAT001",
            )
        ],
        summary=ValidationResultsSummary(
            total_rows=10,
            total_errors=1,
            error_types={ValidationErrorType.REQUIRED_VALUE: 1},
            columns_validated=1,
        ),
    )

    # Create sample schema alignment results
    change_details = [
        SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="name",
            new_column="patient_name",
            reason="Schema alignment to match target schema",
        ),
        SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="age",
            new_column="patient_age",
            reason="Schema alignment to match target schema",
        ),
    ]

    summary = SchemaAlignmentResultsSummary(
        job_id="test-job-123",
        version=1,
        timestamp=datetime.now(timezone.utc),
        original_data_csv="name,age\nJohn,25\nJane,30",
        aligned_data_csv="patient_name,patient_age\nJohn,25\nJane,30",
        total_changes=2,
        columns_renamed=2,
        columns_added=0,
        columns_removed=0,
        rows_original=2,
        rows_aligned=2,
    )

    schema_alignment_results = SchemaAlignmentResults(schema_alignment_results=change_details, summary=summary)

    # Create combined results
    combined_results = CombinedResults(
        validation_results=validation_results, schema_alignment_results=schema_alignment_results
    )

    # Create ValidationStatusResponse
    job_id = uuid4()
    response = ValidationStatusResponse(
        job_id=job_id,
        user_id="test_user",
        core_schema_id="core_v1",
        program_schema_id="program_v1",
        status="completed",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        current_version=1,
        latest_results=combined_results,
    )

    # Test serialization with camelCase aliases
    serialized = response.model_dump(by_alias=True)

    # Verify top-level structure
    assert "jobId" in serialized
    assert "latestResults" in serialized
    assert serialized["status"] == "completed"

    # Verify combined results structure
    latest_results = serialized["latestResults"]
    assert "validationResults" in latest_results
    assert "schemaAlignmentResults" in latest_results

    # Verify validation results structure
    validation_data = latest_results["validationResults"]
    assert "validationResults" in validation_data
    assert "summary" in validation_data
    assert len(validation_data["validationResults"]) == 1
    assert validation_data["validationResults"][0]["column"] == "patient_id"
    assert validation_data["summary"]["totalRows"] == 10

    # Verify schema alignment results structure
    schema_data = latest_results["schemaAlignmentResults"]
    assert "schemaAlignmentResults" in schema_data
    assert "summary" in schema_data
    assert len(schema_data["schemaAlignmentResults"]) == 2
    assert "John,25" in schema_data["summary"]["originalDataCsv"]
    assert "patient_name,patient_age" in schema_data["summary"]["alignedDataCsv"]
    assert schema_data["schemaAlignmentResults"][0]["changeType"] == "rename"


def test_validation_status_response_validation_only():
    """Test ValidationStatusResponse with validation results only."""
    validation_results = ValidationResults(
        validation_results=[
            ValidationErrorDetail(
                row=2,
                column="birth_date",
                current_value="invalid-date",
                error_type=ValidationErrorType.INVALID_PATTERN,
                valid_options=None,
                recommended_value="1990-01-01",
            )
        ],
        summary=ValidationResultsSummary(
            total_rows=5,
            total_errors=1,
            error_types={ValidationErrorType.INVALID_PATTERN: 1},
            columns_validated=1,
        ),
    )

    combined_results = CombinedResults(validation_results=validation_results, schema_alignment_results=None)

    response = ValidationStatusResponse(
        job_id=uuid4(),
        user_id="test_user",
        core_schema_id="core_v1",
        program_schema_id="program_v1",
        status="completed",
        created_at=datetime.now(timezone.utc),
        current_version=1,
        latest_results=combined_results,
    )

    serialized = response.model_dump(by_alias=True)
    latest_results = serialized["latestResults"]

    # Verify validation results are present
    assert latest_results["validationResults"] is not None
    assert len(latest_results["validationResults"]["validationResults"]) == 1

    # Verify schema alignment results are null
    assert latest_results["schemaAlignmentResults"] is None


def test_validation_status_response_schema_alignment_only():
    """Test ValidationStatusResponse with schema alignment results only."""
    change_details = [
        SchemaAlignmentChangeDetail(
            change_type="rename", original_column="id", new_column="participant_id", reason="Schema alignment"
        ),
        SchemaAlignmentChangeDetail(
            change_type="rename", original_column="name", new_column="participant_name", reason="Schema alignment"
        ),
    ]

    summary = SchemaAlignmentResultsSummary(
        job_id="test-job-456",
        version=1,
        timestamp=datetime.now(timezone.utc),
        original_data_csv="id,name\n1,John\n2,Jane",
        aligned_data_csv="participant_id,participant_name\n1,John\n2,Jane",
        total_changes=2,
        columns_renamed=2,
        columns_added=0,
        columns_removed=0,
    )

    schema_alignment_results = SchemaAlignmentResults(schema_alignment_results=change_details, summary=summary)

    combined_results = CombinedResults(validation_results=None, schema_alignment_results=schema_alignment_results)

    response = ValidationStatusResponse(
        job_id=uuid4(),
        user_id="test_user",
        core_schema_id="core_v1",
        program_schema_id="program_v1",
        status="completed",
        created_at=datetime.now(timezone.utc),
        current_version=1,
        latest_results=combined_results,
    )

    serialized = response.model_dump(by_alias=True)
    latest_results = serialized["latestResults"]

    # Verify validation results are null
    assert latest_results["validationResults"] is None

    # Verify schema alignment results are present
    assert latest_results["schemaAlignmentResults"] is not None
    assert "participant_id,participant_name" in latest_results["schemaAlignmentResults"]["summary"]["alignedDataCsv"]


def test_validation_status_response_no_results():
    """Test ValidationStatusResponse with no results."""
    response = ValidationStatusResponse(
        job_id=uuid4(),
        user_id="test_user",
        core_schema_id="core_v1",
        program_schema_id="program_v1",
        status="pending",
        created_at=datetime.now(timezone.utc),
        current_version=1,
        latest_results=None,
    )

    serialized = response.model_dump(by_alias=True)

    # Verify no results
    assert serialized["latestResults"] is None
    assert serialized["status"] == "pending"


def test_combined_results_backward_compatibility():
    """Test that CombinedResults maintains backward compatibility."""
    # Test empty combined results
    empty_results = CombinedResults()
    serialized = empty_results.model_dump(by_alias=True)

    assert "validationResults" in serialized
    assert "schemaAlignmentResults" in serialized
    assert serialized["validationResults"] is None
    assert serialized["schemaAlignmentResults"] is None

    # Test deserialization from camelCase with new structure
    camel_case_data = {
        "validationResults": None,
        "schemaAlignmentResults": {
            "schemaAlignmentResults": [
                {
                    "changeType": "rename",
                    "originalColumn": "test",
                    "newColumn": "test_col",
                    "reason": "Schema alignment",
                }
            ],
            "summary": {
                "jobId": "test-job",
                "version": 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "originalDataCsv": "test,data\n1,2",
                "alignedDataCsv": "test_col,data_col\n1,2",
                "totalChanges": 1,
                "columnsRenamed": 1,
                "columnsAdded": 0,
                "columnsRemoved": 0,
                "rowsOriginal": 1,
                "rowsAligned": 1,
            },
        },
    }

    results = CombinedResults(**camel_case_data)
    assert results.validation_results is None
    assert results.schema_alignment_results is not None
    assert results.schema_alignment_results.summary.original_data_csv == "test,data\n1,2"
