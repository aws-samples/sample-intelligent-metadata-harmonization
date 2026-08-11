# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for validation models.

Tests the validation data models including ValidationErrorType enum,
ValidationErrorDetail, ValidationResultsSummary, and ValidationResults.
"""

import pytest
from pydantic import ValidationError

from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class TestValidationErrorType:
    """Test cases for ValidationErrorType enum."""

    def test_enum_values(self):
        """Test that enum has correct values."""
        assert ValidationErrorType.REQUIRED_VALUE == "REQUIRED_VALUE"
        assert ValidationErrorType.INVALID_OPTION == "INVALID_OPTION"
        assert ValidationErrorType.INVALID_PATTERN == "INVALID_PATTERN"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert "REQUIRED_VALUE" in ValidationErrorType
        assert "INVALID_OPTION" in ValidationErrorType
        assert "INVALID_PATTERN" in ValidationErrorType
        assert "UNKNOWN_ERROR" not in ValidationErrorType


class TestValidationErrorDetail:
    """Test cases for ValidationErrorDetail model."""

    def test_valid_error_detail_creation(self):
        """Test creating a valid ValidationErrorDetail."""
        error_detail = ValidationErrorDetail(
            row=5,
            column="test_column",
            current_value="invalid_value",
            valid_options=["option1", "option2", "option3"],
            recommended_value="option1",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        assert error_detail.row == 5
        assert error_detail.column == "test_column"
        assert error_detail.current_value == "invalid_value"
        assert error_detail.valid_options == ["option1", "option2", "option3"]
        assert error_detail.recommended_value == "option1"
        assert error_detail.error_type == ValidationErrorType.INVALID_OPTION
        assert error_detail.error_message is None
        assert error_detail.schema_field_name is None

    def test_error_detail_with_aliases(self):
        """Test creating ValidationErrorDetail using field aliases."""
        error_detail = ValidationErrorDetail(
            row=10,
            column="status",
            currentValue="bad_status",
            validOptions=["active", "inactive"],
            recommendedValue="active",
            errorType=ValidationErrorType.INVALID_OPTION,
        )

        assert error_detail.row == 10
        assert error_detail.column == "status"
        assert error_detail.current_value == "bad_status"
        assert error_detail.valid_options == ["active", "inactive"]
        assert error_detail.recommended_value == "active"
        assert error_detail.error_type == ValidationErrorType.INVALID_OPTION

    def test_error_detail_with_none_values(self):
        """Test ValidationErrorDetail with optional None values."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="free_text",
            current_value="",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.REQUIRED_VALUE,
        )

        assert error_detail.row == 1
        assert error_detail.column == "free_text"
        assert error_detail.current_value == ""
        assert error_detail.valid_options is None
        assert error_detail.recommended_value is None
        assert error_detail.error_type == ValidationErrorType.REQUIRED_VALUE

    def test_error_detail_serialization(self):
        """Test ValidationErrorDetail serialization with aliases."""
        error_detail = ValidationErrorDetail(
            row=3,
            column="category",
            current_value="unknown",
            valid_options=["A", "B", "C"],
            recommended_value="A",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        serialized = error_detail.model_dump(by_alias=True)
        expected = {
            "row": 3,
            "column": "category",
            "currentValue": "unknown",
            "validOptions": ["A", "B", "C"],
            "recommendedValue": "A",
            "errorType": "INVALID_OPTION",
            "errorMessage": None,
            "schemaFieldName": None,
            "confidenceScore": None,
            "confidenceLevel": None,
            "correctionNode": None,
        }

        assert serialized == expected

    def test_error_detail_deserialization(self):
        """Test ValidationErrorDetail deserialization from dict with aliases."""
        data = {
            "row": 7,
            "column": "priority",
            "currentValue": "urgent",
            "validOptions": ["low", "medium", "high"],
            "recommendedValue": "high",
            "errorType": "INVALID_OPTION",
        }

        error_detail = ValidationErrorDetail(**data)

        assert error_detail.row == 7
        assert error_detail.column == "priority"
        assert error_detail.current_value == "urgent"
        assert error_detail.valid_options == ["low", "medium", "high"]
        assert error_detail.recommended_value == "high"
        assert error_detail.error_type == ValidationErrorType.INVALID_OPTION

    def test_invalid_row_number(self):
        """Test validation error for negative row number."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationErrorDetail(
                row=-1,
                column="test_column",
                current_value="test_value",
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_empty_column_name(self):
        """Test validation error for empty column name."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationErrorDetail(
                row=0,
                column="",
                current_value="test_value",
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )

        assert "at least 1 character" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationErrorDetail(
                row=1,
                column="test_column",
                # Missing current_value and error_type
            )

        error_str = str(exc_info.value)
        assert "current_value" in error_str or "currentValue" in error_str
        assert "error_type" in error_str or "errorType" in error_str

    def test_error_detail_with_custom_error_message(self):
        """Test ValidationErrorDetail with custom error message from schema."""
        error_detail = ValidationErrorDetail(
            row=3,
            column="sample_type",
            current_value="invalid_type",
            valid_options=["blood", "urine", "tissue"],
            recommended_value="blood",
            error_type=ValidationErrorType.INVALID_OPTION,
            error_message="Sample type must be one of the approved laboratory sample types",
            schema_field_name="sampleType",
        )

        assert error_detail.error_message == "Sample type must be one of the approved laboratory sample types"
        assert error_detail.schema_field_name == "sampleType"

    def test_error_detail_with_custom_fields_using_aliases(self):
        """Test ValidationErrorDetail with custom fields using camelCase aliases."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="patient_id",
            current_value="",
            error_type=ValidationErrorType.REQUIRED_VALUE,
            errorMessage="Patient ID is required for all samples",
            schemaFieldName="patientId",
        )

        assert error_detail.error_message == "Patient ID is required for all samples"
        assert error_detail.schema_field_name == "patientId"

    def test_error_detail_serialization_with_custom_fields(self):
        """Test ValidationErrorDetail serialization including custom error message fields."""
        error_detail = ValidationErrorDetail(
            row=2,
            column="collection_date",
            current_value="invalid-date",
            error_type=ValidationErrorType.INVALID_PATTERN,
            error_message="Collection date must be in YYYY-MM-DD format",
            schema_field_name="collectionDate",
        )

        serialized = error_detail.model_dump(by_alias=True)
        expected = {
            "row": 2,
            "column": "collection_date",
            "currentValue": "invalid-date",
            "validOptions": None,
            "recommendedValue": None,
            "errorType": "INVALID_PATTERN",
            "errorMessage": "Collection date must be in YYYY-MM-DD format",
            "schemaFieldName": "collectionDate",
            "confidenceScore": None,
            "confidenceLevel": None,
            "correctionNode": None,
        }

        assert serialized == expected

    def test_error_detail_to_dict_method(self):
        """Test ValidationErrorDetail to_dict method."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="test_field",
            current_value="test_value",
            error_type=ValidationErrorType.REQUIRED_VALUE,
            error_message="Custom error from schema",
            schema_field_name="testField",
        )

        result = error_detail.to_dict()

        assert result["row"] == 1
        assert result["column"] == "test_field"
        assert result["currentValue"] == "test_value"
        assert result["errorType"] == "REQUIRED_VALUE"
        assert result["errorMessage"] == "Custom error from schema"
        assert result["schemaFieldName"] == "testField"

    def test_error_detail_from_dict_method(self):
        """Test ValidationErrorDetail from_dict method."""
        data = {
            "row": 5,
            "column": "status",
            "currentValue": "unknown",
            "validOptions": ["active", "inactive"],
            "recommendedValue": "active",
            "errorType": "INVALID_OPTION",
            "errorMessage": "Status must be either active or inactive",
            "schemaFieldName": "status",
        }

        error_detail = ValidationErrorDetail.from_dict(data)

        assert error_detail.row == 5
        assert error_detail.column == "status"
        assert error_detail.current_value == "unknown"
        assert error_detail.valid_options == ["active", "inactive"]
        assert error_detail.recommended_value == "active"
        assert error_detail.error_type == ValidationErrorType.INVALID_OPTION
        assert error_detail.error_message == "Status must be either active or inactive"
        assert error_detail.schema_field_name == "status"

    def test_error_detail_backward_compatibility(self):
        """Test ValidationErrorDetail backward compatibility with data without custom fields."""
        data = {
            "row": 1,
            "column": "name",
            "currentValue": "",
            "validOptions": None,
            "recommendedValue": None,
            "errorType": "REQUIRED_VALUE",
            # No errorMessage or schemaFieldName
        }

        error_detail = ValidationErrorDetail.from_dict(data)

        assert error_detail.row == 1
        assert error_detail.column == "name"
        assert error_detail.current_value == ""
        assert error_detail.error_type == ValidationErrorType.REQUIRED_VALUE
        assert error_detail.error_message is None
        assert error_detail.schema_field_name is None


class TestValidationResultsSummary:
    """Test cases for ValidationResultsSummary model."""

    def test_valid_summary_creation(self):
        """Test creating a valid ValidationResultsSummary."""
        error_types = {
            ValidationErrorType.REQUIRED_VALUE: 5,
            ValidationErrorType.INVALID_OPTION: 3,
            ValidationErrorType.INVALID_PATTERN: 2,
        }

        summary = ValidationResultsSummary(
            total_rows=100,
            total_errors=10,
            columns_validated=5,
            error_types=error_types,
        )

        assert summary.total_rows == 100
        assert summary.total_errors == 10
        assert summary.columns_validated == 5
        assert summary.error_types == error_types

    def test_summary_with_aliases(self):
        """Test creating ValidationResultsSummary using field aliases."""
        error_types = {
            ValidationErrorType.REQUIRED_VALUE: 2,
            ValidationErrorType.INVALID_OPTION: 1,
        }

        summary = ValidationResultsSummary(totalRows=50, totalErrors=3, columnsValidated=4, errorTypes=error_types)

        assert summary.total_rows == 50
        assert summary.total_errors == 3
        assert summary.columns_validated == 4
        assert summary.error_types == error_types

    def test_summary_serialization(self):
        """Test ValidationResultsSummary serialization with aliases."""
        error_types = {
            ValidationErrorType.REQUIRED_VALUE: 1,
            ValidationErrorType.INVALID_PATTERN: 2,
        }

        summary = ValidationResultsSummary(total_rows=25, total_errors=3, columns_validated=3, error_types=error_types)

        serialized = summary.model_dump(by_alias=True)
        expected = {
            "totalRows": 25,
            "totalErrors": 3,
            "columnsValidated": 3,
            "errorTypes": {"REQUIRED_VALUE": 1, "INVALID_PATTERN": 2},
        }

        assert serialized == expected

    def test_empty_error_types(self):
        """Test ValidationResultsSummary with empty error_types dict."""
        summary = ValidationResultsSummary(total_rows=10, total_errors=0, columns_validated=3, error_types={})

        assert summary.total_rows == 10
        assert summary.total_errors == 0
        assert summary.error_types == {}

    def test_invalid_total_rows(self):
        """Test validation error for negative total_rows."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationResultsSummary(total_rows=-1, total_errors=0, columns_validated=0, error_types={})

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_invalid_total_errors(self):
        """Test validation error for negative total_errors."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationResultsSummary(total_rows=10, total_errors=-5, columns_validated=0, error_types={})

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_summary_to_dict_method(self):
        """Test ValidationResultsSummary to_dict method."""
        error_types = {
            ValidationErrorType.REQUIRED_VALUE: 2,
            ValidationErrorType.INVALID_OPTION: 1,
        }

        summary = ValidationResultsSummary(total_rows=50, total_errors=3, columns_validated=4, error_types=error_types)

        result = summary.to_dict()

        assert result["totalRows"] == 50
        assert result["totalErrors"] == 3
        assert result["columnsValidated"] == 4
        assert result["errorTypes"]["REQUIRED_VALUE"] == 2
        assert result["errorTypes"]["INVALID_OPTION"] == 1

    def test_summary_from_dict_method(self):
        """Test ValidationResultsSummary from_dict method."""
        data = {
            "totalRows": 25,
            "totalErrors": 2,
            "columnsValidated": 3,
            "errorTypes": {"INVALID_PATTERN": 1, "REQUIRED_VALUE": 1},
        }

        summary = ValidationResultsSummary.from_dict(data)

        assert summary.total_rows == 25
        assert summary.total_errors == 2
        assert summary.columns_validated == 3
        assert summary.error_types[ValidationErrorType.INVALID_PATTERN] == 1
        assert summary.error_types[ValidationErrorType.REQUIRED_VALUE] == 1


class TestValidationResults:
    """Test cases for ValidationResults model."""

    def test_valid_results_creation(self):
        """Test creating a valid ValidationResults."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="test_column",
            current_value="invalid",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        summary = ValidationResultsSummary(
            total_rows=10,
            total_errors=1,
            columns_validated=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
        )

        results = ValidationResults(validation_results=[error_detail], summary=summary)

        assert len(results.validation_results) == 1
        assert results.validation_results[0] == error_detail
        assert results.summary == summary

    def test_results_with_aliases(self):
        """Test creating ValidationResults using field aliases."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="status",
            current_value="bad",
            error_type=ValidationErrorType.REQUIRED_VALUE,
        )

        summary = ValidationResultsSummary(
            total_rows=5,
            total_errors=1,
            columns_validated=1,
            error_types={ValidationErrorType.REQUIRED_VALUE: 1},
        )

        results = ValidationResults(validationResults=[error_detail], summary=summary)

        assert len(results.validation_results) == 1
        assert results.validation_results[0] == error_detail
        assert results.summary == summary

    def test_empty_validation_results(self):
        """Test ValidationResults with empty validation_results list."""
        summary = ValidationResultsSummary(total_rows=10, total_errors=0, columns_validated=3, error_types={})

        results = ValidationResults(validation_results=[], summary=summary)

        assert len(results.validation_results) == 0
        assert results.summary == summary

    def test_multiple_validation_errors(self):
        """Test ValidationResults with multiple error details."""
        error1 = ValidationErrorDetail(
            row=1,
            column="col1",
            current_value="bad1",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        error2 = ValidationErrorDetail(
            row=2,
            column="col2",
            current_value="bad2",
            error_type=ValidationErrorType.REQUIRED_VALUE,
        )

        error3 = ValidationErrorDetail(
            row=3,
            column="col3",
            current_value="bad3",
            error_type=ValidationErrorType.INVALID_PATTERN,
        )

        summary = ValidationResultsSummary(
            total_rows=10,
            total_errors=3,
            columns_validated=3,
            error_types={
                ValidationErrorType.INVALID_OPTION: 1,
                ValidationErrorType.REQUIRED_VALUE: 1,
                ValidationErrorType.INVALID_PATTERN: 1,
            },
        )

        results = ValidationResults(validation_results=[error1, error2, error3], summary=summary)

        assert len(results.validation_results) == 3
        assert results.validation_results[0] == error1
        assert results.validation_results[1] == error2
        assert results.validation_results[2] == error3
        assert results.summary == summary

    def test_results_serialization(self):
        """Test ValidationResults serialization with aliases."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="test",
            current_value="invalid",
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            columns_validated=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
        )

        results = ValidationResults(validation_results=[error_detail], summary=summary)

        serialized = results.model_dump(by_alias=True)

        assert "validationResults" in serialized
        assert "summary" in serialized
        assert len(serialized["validationResults"]) == 1
        assert serialized["summary"]["totalRows"] == 1
        assert serialized["summary"]["totalErrors"] == 1
        assert serialized["summary"]["columnsValidated"] == 1

    def test_results_deserialization(self):
        """Test ValidationResults deserialization from dict with aliases."""
        data = {
            "validationResults": [
                {
                    "row": 1,
                    "column": "test",
                    "currentValue": "invalid",
                    "validOptions": None,
                    "recommendedValue": None,
                    "errorType": "INVALID_OPTION",
                }
            ],
            "summary": {
                "totalRows": 1,
                "totalErrors": 1,
                "columnsValidated": 1,
                "errorTypes": {"INVALID_OPTION": 1},
            },
        }

        results = ValidationResults(**data)

        assert len(results.validation_results) == 1
        assert results.validation_results[0].row == 1
        assert results.validation_results[0].column == "test"
        assert results.validation_results[0].current_value == "invalid"
        assert results.validation_results[0].error_type == ValidationErrorType.INVALID_OPTION
        assert results.summary.total_rows == 1
        assert results.summary.total_errors == 1
        assert results.summary.columns_validated == 1


class TestValidationModelsIntegration:
    """Integration tests for validation models working together."""

    def test_complete_validation_workflow(self):
        """Test a complete validation workflow with all models."""
        # Create multiple error details
        errors = [
            ValidationErrorDetail(
                row=1,
                column="status",
                current_value="unknown",
                valid_options=["active", "inactive"],
                recommended_value="active",
                error_type=ValidationErrorType.INVALID_OPTION,
            ),
            ValidationErrorDetail(
                row=2,
                column="name",
                current_value="",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.REQUIRED_VALUE,
            ),
            ValidationErrorDetail(
                row=3,
                column="email",
                current_value="invalid-email",
                valid_options=None,
                recommended_value="user@example.com",
                error_type=ValidationErrorType.INVALID_PATTERN,
            ),
        ]

        # Create summary
        summary = ValidationResultsSummary(
            total_rows=100,
            total_errors=3,
            columns_validated=3,
            error_types={
                ValidationErrorType.INVALID_OPTION: 1,
                ValidationErrorType.REQUIRED_VALUE: 1,
                ValidationErrorType.INVALID_PATTERN: 1,
            },
        )

        # Create complete results
        results = ValidationResults(validation_results=errors, summary=summary)

        # Verify structure
        assert len(results.validation_results) == 3
        assert results.summary.total_errors == 3
        assert sum(results.summary.error_types.values()) == 3

        # Test serialization/deserialization round trip
        serialized = results.model_dump(by_alias=True)
        deserialized = ValidationResults(**serialized)

        assert len(deserialized.validation_results) == 3
        assert deserialized.summary.total_errors == 3
        assert deserialized.validation_results[0].error_type == ValidationErrorType.INVALID_OPTION
        assert deserialized.validation_results[1].error_type == ValidationErrorType.REQUIRED_VALUE
        assert deserialized.validation_results[2].error_type == ValidationErrorType.INVALID_PATTERN

    def test_results_to_dict_method(self):
        """Test ValidationResults to_dict method."""
        error_detail = ValidationErrorDetail(
            row=1,
            column="test",
            current_value="invalid",
            error_type=ValidationErrorType.INVALID_OPTION,
            error_message="Custom error message",
            schema_field_name="testField",
        )

        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            columns_validated=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
        )

        results = ValidationResults(validation_results=[error_detail], summary=summary)

        result = results.to_dict()

        assert "validationResults" in result
        assert "summary" in result
        assert len(result["validationResults"]) == 1
        assert result["validationResults"][0]["errorMessage"] == "Custom error message"
        assert result["validationResults"][0]["schemaFieldName"] == "testField"

    def test_results_from_dict_method(self):
        """Test ValidationResults from_dict method."""
        data = {
            "validationResults": [
                {
                    "row": 1,
                    "column": "test",
                    "currentValue": "invalid",
                    "validOptions": None,
                    "recommendedValue": None,
                    "errorType": "INVALID_OPTION",
                    "errorMessage": "Schema-defined error message",
                    "schemaFieldName": "testField",
                }
            ],
            "summary": {
                "totalRows": 1,
                "totalErrors": 1,
                "columnsValidated": 1,
                "errorTypes": {"INVALID_OPTION": 1},
            },
        }

        results = ValidationResults.from_dict(data)

        assert len(results.validation_results) == 1
        assert results.validation_results[0].error_message == "Schema-defined error message"
        assert results.validation_results[0].schema_field_name == "testField"
        assert results.summary.columns_validated == 1
