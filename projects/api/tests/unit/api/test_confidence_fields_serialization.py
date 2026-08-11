# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for confidence fields serialization in API models.

This module tests that confidence fields are properly serialized with camelCase
aliases in API responses.
"""

import pytest
from metadata_harmonization_api.api.v1.models.metadata import SchemaAlignmentChangeDetail
from metadata_harmonization_processor.models.validation import ValidationErrorDetail, ValidationErrorType


class TestConfidenceFieldsSerialization:
    """Test confidence fields serialization in API models."""

    def test_validation_error_detail_confidence_serialization(self):
        """Test ValidationErrorDetail confidence fields serialize to camelCase."""

        error = ValidationErrorDetail(
            row=1,
            column="test_column",
            current_value="invalid_value",
            error_type=ValidationErrorType.INVALID_PATTERN,
            recommended_value="valid_value",
            confidence_score=0.75,
            confidence_level="Medium",
        )

        # Test serialization with aliases (camelCase)
        serialized = error.model_dump(by_alias=True)

        # Verify confidence fields are in camelCase
        assert "confidenceScore" in serialized
        assert "confidenceLevel" in serialized
        assert serialized["confidenceScore"] == 0.75
        assert serialized["confidenceLevel"] == "Medium"

        # Verify other fields are also in camelCase
        assert "currentValue" in serialized
        assert "recommendedValue" in serialized
        assert "errorType" in serialized

        # Verify snake_case fields are not present
        assert "confidence_score" not in serialized
        assert "confidence_level" not in serialized
        assert "current_value" not in serialized
        assert "recommended_value" not in serialized
        assert "error_type" not in serialized

    def test_schema_alignment_change_detail_confidence_serialization(self):
        """Test SchemaAlignmentChangeDetail confidence fields serialize to camelCase."""

        change = SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="old_name",
            new_column="new_name",
            reason="LLM match",
            confidence_score=0.88,
            confidence_level="High",
            llm_confidence_level="High",
        )

        # Test serialization with aliases (camelCase)
        serialized = change.model_dump(by_alias=True)

        # Verify confidence fields are in camelCase
        assert "confidenceScore" in serialized
        assert "confidenceLevel" in serialized
        assert "llmConfidenceLevel" in serialized
        assert serialized["confidenceScore"] == 0.88
        assert serialized["confidenceLevel"] == "High"
        assert serialized["llmConfidenceLevel"] == "High"

        # Verify other fields are also in camelCase
        assert "changeType" in serialized
        assert "originalColumn" in serialized
        assert "newColumn" in serialized

        # Verify snake_case fields are not present
        assert "confidence_score" not in serialized
        assert "confidence_level" not in serialized
        assert "llm_confidence_level" not in serialized
        assert "change_type" not in serialized
        assert "original_column" not in serialized
        assert "new_column" not in serialized

    def test_validation_error_detail_default_confidence_serialization(self):
        """Test ValidationErrorDetail default confidence values serialize correctly."""

        error = ValidationErrorDetail(
            row=1,
            column="test_column",
            current_value="test_value",
            error_type=ValidationErrorType.REQUIRED_VALUE,
            # confidence fields will use defaults
        )

        serialized = error.model_dump(by_alias=True)

        # Verify default confidence values (None, not 0.0)
        assert serialized["confidenceScore"] is None
        assert serialized["confidenceLevel"] is None

    def test_schema_alignment_change_detail_default_confidence_serialization(self):
        """Test SchemaAlignmentChangeDetail default confidence values serialize correctly."""

        change = SchemaAlignmentChangeDetail(
            change_type="add",
            new_column="new_column",
            # confidence fields will use defaults
        )

        serialized = change.model_dump(by_alias=True)

        # Verify default confidence values
        assert serialized["confidenceScore"] == 0.0
        assert serialized["confidenceLevel"] == "Low"
        assert serialized["llmConfidenceLevel"] is None

    def test_validation_error_detail_deserialization_from_camel_case(self):
        """Test ValidationErrorDetail can be created from camelCase data."""

        camel_case_data = {
            "row": 1,
            "column": "test_column",
            "currentValue": "test_value",
            "errorType": "INVALID_PATTERN",
            "recommendedValue": "corrected_value",
            "confidenceScore": 0.65,
            "confidenceLevel": "Medium",
        }

        error = ValidationErrorDetail(**camel_case_data)

        # Verify fields are properly mapped
        assert error.row == 1
        assert error.column == "test_column"
        assert error.current_value == "test_value"
        assert error.error_type == ValidationErrorType.INVALID_PATTERN
        assert error.recommended_value == "corrected_value"
        assert error.confidence_score == 0.65
        assert error.confidence_level == "Medium"

    def test_schema_alignment_change_detail_deserialization_from_camel_case(self):
        """Test SchemaAlignmentChangeDetail can be created from camelCase data."""

        camel_case_data = {
            "changeType": "rename",
            "originalColumn": "old_name",
            "newColumn": "new_name",
            "reason": "LLM semantic match",
            "confidenceScore": 0.92,
            "confidenceLevel": "High",
            "llmConfidenceLevel": "High",
        }

        change = SchemaAlignmentChangeDetail(**camel_case_data)

        # Verify fields are properly mapped
        assert change.change_type == "rename"
        assert change.original_column == "old_name"
        assert change.new_column == "new_name"
        assert change.reason == "LLM semantic match"
        assert change.confidence_score == 0.92
        assert change.confidence_level == "High"
        assert change.llm_confidence_level == "High"

    def test_confidence_score_validation_constraints(self):
        """Test that confidence score validation constraints work correctly."""

        # Test valid confidence scores
        valid_scores = [0.0, 0.5, 1.0, 0.123, 0.999]

        for score in valid_scores:
            error = ValidationErrorDetail(
                row=1,
                column="test",
                current_value="test",
                error_type=ValidationErrorType.REQUIRED_VALUE,
                confidence_score=score,
                confidence_level="Medium",
            )
            assert error.confidence_score == score

        # Test invalid confidence scores
        invalid_scores = [-0.1, 1.1, -1.0, 2.0, 10.0]

        for score in invalid_scores:
            with pytest.raises(ValueError):
                ValidationErrorDetail(
                    row=1,
                    column="test",
                    current_value="test",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    confidence_score=score,
                    confidence_level="Medium",
                )

    def test_round_trip_serialization_deserialization(self):
        """Test that confidence fields survive round-trip serialization/deserialization."""

        # Create ValidationErrorDetail with confidence fields
        original_error = ValidationErrorDetail(
            row=5,
            column="patient_id",
            current_value="invalid_id",
            error_type=ValidationErrorType.INVALID_PATTERN,
            recommended_value="PAT123",
            confidence_score=0.82,
            confidence_level="High",
        )

        # Serialize to dict (camelCase)
        serialized = original_error.model_dump(by_alias=True)

        # Deserialize back to object
        deserialized_error = ValidationErrorDetail(**serialized)

        # Verify all fields match
        assert deserialized_error.row == original_error.row
        assert deserialized_error.column == original_error.column
        assert deserialized_error.current_value == original_error.current_value
        assert deserialized_error.error_type == original_error.error_type
        assert deserialized_error.recommended_value == original_error.recommended_value
        assert deserialized_error.confidence_score == original_error.confidence_score
        assert deserialized_error.confidence_level == original_error.confidence_level

        # Create SchemaAlignmentChangeDetail with confidence fields
        original_change = SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="patient_name",
            new_column="name",
            reason="Semantic match",
            confidence_score=0.95,
            confidence_level="High",
            llm_confidence_level="High",
        )

        # Serialize to dict (camelCase)
        serialized_change = original_change.model_dump(by_alias=True)

        # Deserialize back to object
        deserialized_change = SchemaAlignmentChangeDetail(**serialized_change)

        # Verify all fields match
        assert deserialized_change.change_type == original_change.change_type
        assert deserialized_change.original_column == original_change.original_column
        assert deserialized_change.new_column == original_change.new_column
        assert deserialized_change.reason == original_change.reason
        assert deserialized_change.confidence_score == original_change.confidence_score
        assert deserialized_change.confidence_level == original_change.confidence_level
        assert deserialized_change.llm_confidence_level == original_change.llm_confidence_level
