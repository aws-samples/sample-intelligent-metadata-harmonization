# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Integration tests for confidence fields in API responses.

This module tests that confidence fields are properly included and serialized
in API responses for both ValidationErrorDetail and SchemaAlignmentChangeDetail.
"""

import pytest
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


def test_validation_error_detail_confidence_fields_in_api_response():
    """Test that ValidationErrorDetail includes confidence fields in API response."""

    # Create ValidationErrorDetail with explicit confidence values
    validation_error = ValidationErrorDetail(
        row=1,
        column="patient_id",
        current_value="invalid_id",
        error_type=ValidationErrorType.INVALID_PATTERN,
        valid_options=None,
        recommended_value="PAT001",
        confidence_score=0.85,
        confidence_level="High",
    )

    validation_results = ValidationResults(
        validation_results=[validation_error],
        summary=ValidationResultsSummary(
            total_rows=10,
            total_errors=1,
            error_types={ValidationErrorType.INVALID_PATTERN: 1},
            columns_validated=1,
        ),
    )

    # Create API response
    combined_results = CombinedResults(validation_results=validation_results, schema_alignment_results=None)

    response = ValidationStatusResponse(
        job_id=uuid4(),
        user_id="test_user",
        core_schema_id="core_schema_1",
        program_schema_id="program_schema_1",
        status="completed",
        created_at=datetime.now(timezone.utc),
        current_version=1,
        latest_results=combined_results,
    )

    # Serialize to dict (simulating JSON response)
    response_dict = response.model_dump(by_alias=True)

    # Verify confidence fields are present in the serialized response
    validation_error_dict = response_dict["latestResults"]["validationResults"]["validationResults"][0]

    assert "confidenceScore" in validation_error_dict
    assert "confidenceLevel" in validation_error_dict
    assert validation_error_dict["confidenceScore"] == 0.85
    assert validation_error_dict["confidenceLevel"] == "High"

    # Verify other fields are still present
    assert validation_error_dict["row"] == 1
    assert validation_error_dict["column"] == "patient_id"
    assert validation_error_dict["currentValue"] == "invalid_id"
    assert validation_error_dict["recommendedValue"] == "PAT001"
    assert validation_error_dict["errorType"] == "INVALID_PATTERN"


def test_schema_alignment_change_detail_confidence_fields_in_api_response():
    """Test that SchemaAlignmentChangeDetail includes confidence fields in API response."""

    # Create SchemaAlignmentChangeDetail with explicit confidence values
    change_detail = SchemaAlignmentChangeDetail(
        change_type="rename",
        original_column="patient_name",
        new_column="name",
        reason="Target: name | Match: patient_name | Confidence: High | Reasoning: Semantic similarity match",
        row_count_affected=100,
        confidence_score=0.92,
        confidence_level="High",
        llm_confidence_level="High",
    )

    schema_alignment_results = SchemaAlignmentResults(
        schema_alignment_results=[change_detail],
        summary=SchemaAlignmentResultsSummary(
            job_id="test_job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="original,data",
            aligned_data_csv="aligned,data",
            total_changes=1,
            columns_renamed=1,
            columns_added=0,
            columns_removed=0,
            rows_original=100,
            rows_aligned=100,
        ),
    )

    # Create API response
    combined_results = CombinedResults(validation_results=None, schema_alignment_results=schema_alignment_results)

    response = ValidationStatusResponse(
        job_id=uuid4(),
        user_id="test_user",
        core_schema_id="core_schema_1",
        program_schema_id="program_schema_1",
        status="completed",
        created_at=datetime.now(timezone.utc),
        current_version=1,
        latest_results=combined_results,
    )

    # Serialize to dict (simulating JSON response)
    response_dict = response.model_dump(by_alias=True)

    # Verify confidence fields are present in the serialized response
    change_detail_dict = response_dict["latestResults"]["schemaAlignmentResults"]["schemaAlignmentResults"][0]

    assert "confidenceScore" in change_detail_dict
    assert "confidenceLevel" in change_detail_dict
    assert "llmConfidenceLevel" in change_detail_dict
    assert change_detail_dict["confidenceScore"] == 0.92
    assert change_detail_dict["confidenceLevel"] == "High"
    assert change_detail_dict["llmConfidenceLevel"] == "High"

    # Verify other fields are still present
    assert change_detail_dict["changeType"] == "rename"
    assert change_detail_dict["originalColumn"] == "patient_name"
    assert change_detail_dict["newColumn"] == "name"
    assert change_detail_dict["rowCountAffected"] == 100


def test_default_confidence_values_in_api_response():
    """Test that default confidence values are properly serialized in API response."""

    # Create ValidationErrorDetail without explicit confidence values (should use defaults)
    validation_error = ValidationErrorDetail(
        row=1,
        column="test_column",
        current_value="test_value",
        error_type=ValidationErrorType.REQUIRED_VALUE,
        valid_options=None,
        recommended_value=None,
        # confidence_score and confidence_level will use defaults (None for processor model)
    )

    validation_results = ValidationResults(
        validation_results=[validation_error],
        summary=ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            error_types={ValidationErrorType.REQUIRED_VALUE: 1},
            columns_validated=0,
        ),
    )

    # Create SchemaAlignmentChangeDetail without explicit confidence values
    change_detail = SchemaAlignmentChangeDetail(
        change_type="add",
        new_column="new_column",
        reason="Required by schema",
        # confidence_score defaults to 0.0 and confidence_level defaults to "Low" for API model
    )

    schema_alignment_results = SchemaAlignmentResults(
        schema_alignment_results=[change_detail],
        summary=SchemaAlignmentResultsSummary(
            job_id="test_job",
            version=1,
            timestamp=datetime.now(timezone.utc),
            original_data_csv="original",
            aligned_data_csv="aligned",
            total_changes=1,
            columns_renamed=0,
            columns_added=1,
            columns_removed=0,
            rows_original=1,
            rows_aligned=1,
        ),
    )

    combined_results = CombinedResults(
        validation_results=validation_results, schema_alignment_results=schema_alignment_results
    )

    response = ValidationStatusResponse(
        job_id=uuid4(),
        user_id="test_user",
        core_schema_id="core_schema_1",
        program_schema_id="program_schema_1",
        status="completed",
        created_at=datetime.now(timezone.utc),
        current_version=1,
        latest_results=combined_results,
    )

    # Serialize to dict (simulating JSON response)
    response_dict = response.model_dump(by_alias=True)

    # Verify default confidence values for ValidationErrorDetail (processor model defaults to None)
    validation_error_dict = response_dict["latestResults"]["validationResults"]["validationResults"][0]
    assert validation_error_dict["confidenceScore"] is None
    assert validation_error_dict["confidenceLevel"] is None

    # Verify default confidence values for SchemaAlignmentChangeDetail (API model defaults to 0.0/"Low")
    change_detail_dict = response_dict["latestResults"]["schemaAlignmentResults"]["schemaAlignmentResults"][0]
    assert change_detail_dict["confidenceScore"] == 0.0
    assert change_detail_dict["confidenceLevel"] == "Low"
    assert change_detail_dict["llmConfidenceLevel"] is None


def test_confidence_field_validation_constraints():
    """Test that confidence field validation constraints are enforced."""

    # Test valid confidence score range
    valid_error = ValidationErrorDetail(
        row=1,
        column="test",
        current_value="test",
        error_type=ValidationErrorType.REQUIRED_VALUE,
        confidence_score=0.5,  # Valid: between 0.0 and 1.0
        confidence_level="Medium",
    )
    assert valid_error.confidence_score == 0.5

    # Test confidence score boundary values
    min_error = ValidationErrorDetail(
        row=1,
        column="test",
        current_value="test",
        error_type=ValidationErrorType.REQUIRED_VALUE,
        confidence_score=0.0,  # Valid: minimum value
        confidence_level="Low",
    )
    assert min_error.confidence_score == 0.0

    max_error = ValidationErrorDetail(
        row=1,
        column="test",
        current_value="test",
        error_type=ValidationErrorType.REQUIRED_VALUE,
        confidence_score=1.0,  # Valid: maximum value
        confidence_level="High",
    )
    assert max_error.confidence_score == 1.0

    # Test invalid confidence score (should raise validation error)
    with pytest.raises(ValueError):
        ValidationErrorDetail(
            row=1,
            column="test",
            current_value="test",
            error_type=ValidationErrorType.REQUIRED_VALUE,
            confidence_score=1.5,  # Invalid: > 1.0
            confidence_level="High",
        )

    with pytest.raises(ValueError):
        ValidationErrorDetail(
            row=1,
            column="test",
            current_value="test",
            error_type=ValidationErrorType.REQUIRED_VALUE,
            confidence_score=-0.1,  # Invalid: < 0.0
            confidence_level="Low",
        )
