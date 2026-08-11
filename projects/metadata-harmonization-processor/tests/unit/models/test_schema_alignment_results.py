# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for SchemaAlignmentResults model.

Tests the SchemaAlignmentResults Pydantic model including the new nested structure
with SchemaAlignmentChangeDetail and SchemaAlignmentResultsSummary models.
"""

from datetime import datetime

import pytest

from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResults,
    SchemaAlignmentResultsSummary,
)


class TestSchemaAlignmentChangeDetail:
    """Test cases for SchemaAlignmentChangeDetail model."""

    def test_rename_change_creation(self):
        """Test creating a rename change detail."""
        change = SchemaAlignmentChangeDetail(
            change_type="rename",
            original_column="id",
            new_column="participant_id",
            reason="Schema alignment requirement",
            row_count_affected=100,
        )

        assert change.change_type == "rename"
        assert change.original_column == "id"
        assert change.new_column == "participant_id"
        assert change.reason == "Schema alignment requirement"
        assert change.row_count_affected == 100

    def test_add_change_creation(self):
        """Test creating an add change detail."""
        change = SchemaAlignmentChangeDetail(
            change_type="add",
            new_column="status",
            reason="Required field for validation",
            row_count_affected=100,
        )

        assert change.change_type == "add"
        assert change.original_column is None
        assert change.new_column == "status"
        assert change.reason == "Required field for validation"
        assert change.row_count_affected == 100

    def test_remove_change_creation(self):
        """Test creating a remove change detail."""
        change = SchemaAlignmentChangeDetail(
            change_type="remove",
            original_column="temp_field",
            reason="Not required for schema",
            row_count_affected=100,
        )

        assert change.change_type == "remove"
        assert change.original_column == "temp_field"
        assert change.new_column is None
        assert change.reason == "Not required for schema"
        assert change.row_count_affected == 100

    def test_minimal_change_creation(self):
        """Test creating change with only required fields."""
        change = SchemaAlignmentChangeDetail(change_type="rename")

        assert change.change_type == "rename"
        assert change.original_column is None
        assert change.new_column is None
        assert change.reason is None
        assert change.row_count_affected is None


class TestSchemaAlignmentResultsSummary:
    """Test cases for SchemaAlignmentResultsSummary model."""

    def test_summary_creation_with_required_fields(self):
        """Test creating summary with required fields."""
        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-123",
            version=1,
            original_data_csv="id,name\n1,John\n2,Jane",
            aligned_data_csv="participant_id,participant_name\n1,John\n2,Jane",
        )

        assert summary.job_id == "test-job-123"
        assert summary.version == 1
        assert summary.original_data_csv == "id,name\n1,John\n2,Jane"
        assert summary.aligned_data_csv == "participant_id,participant_name\n1,John\n2,Jane"
        assert isinstance(summary.timestamp, datetime)
        assert summary.total_changes == 0
        assert summary.columns_renamed == 0
        assert summary.columns_added == 0
        assert summary.columns_removed == 0
        assert summary.rows_original == 0
        assert summary.rows_aligned == 0

    def test_summary_creation_with_all_fields(self):
        """Test creating summary with all fields."""
        timestamp = datetime.utcnow()
        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-456",
            version=2,
            timestamp=timestamp,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
            total_changes=3,
            columns_renamed=2,
            columns_added=1,
            columns_removed=0,
            rows_original=100,
            rows_aligned=100,
        )

        assert summary.job_id == "test-job-456"
        assert summary.version == 2
        assert summary.timestamp == timestamp
        assert summary.total_changes == 3
        assert summary.columns_renamed == 2
        assert summary.columns_added == 1
        assert summary.columns_removed == 0
        assert summary.rows_original == 100
        assert summary.rows_aligned == 100


class TestSchemaAlignmentResults:
    """Test cases for SchemaAlignmentResults model."""

    def test_model_creation_with_empty_changes(self):
        """Test creating SchemaAlignmentResults with empty changes list."""
        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-123",
            version=1,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
        )

        results = SchemaAlignmentResults(summary=summary)

        assert len(results.schema_alignment_results) == 0
        assert results.summary == summary

    def test_model_creation_with_changes(self):
        """Test creating SchemaAlignmentResults with change details."""
        changes = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="id",
                new_column="participant_id",
                reason="Schema alignment",
                row_count_affected=100,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                new_column="status",
                reason="Required field",
                row_count_affected=100,
            ),
        ]

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-456",
            version=1,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name,status\n1,John,active",
            total_changes=2,
            columns_renamed=1,
            columns_added=1,
        )

        results = SchemaAlignmentResults(schema_alignment_results=changes, summary=summary)

        assert len(results.schema_alignment_results) == 2
        assert results.schema_alignment_results[0].change_type == "rename"
        assert results.schema_alignment_results[1].change_type == "add"
        assert results.summary.total_changes == 2

    def test_to_dict_serialization(self):
        """Test to_dict method for storage serialization."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)

        changes = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="id",
                new_column="participant_id",
                reason="Schema alignment",
                row_count_affected=100,
            )
        ]

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-789",
            version=1,
            timestamp=timestamp,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
            total_changes=1,
            columns_renamed=1,
        )

        results = SchemaAlignmentResults(schema_alignment_results=changes, summary=summary)

        result_dict = results.to_dict()

        expected_dict = {
            "schema_alignment_results": [
                {
                    "change_type": "rename",
                    "original_column": "id",
                    "new_column": "participant_id",
                    "reason": "Schema alignment",
                    "row_count_affected": 100,
                    "confidence_score": 0.0,
                    "confidence_level": "Low",
                }
            ],
            "summary": {
                "job_id": "test-job-789",
                "version": 1,
                "timestamp": "2024-01-15T10:30:00",
                "original_data_csv": "id,name\n1,John",
                "aligned_data_csv": "participant_id,participant_name\n1,John",
                "total_changes": 1,
                "columns_renamed": 1,
                "columns_added": 0,
                "columns_removed": 0,
                "rows_original": 0,
                "rows_aligned": 0,
            },
        }

        assert result_dict == expected_dict

    def test_from_dict_deserialization(self):
        """Test from_dict class method for loading from storage."""
        data = {
            "schema_alignment_results": [
                {
                    "change_type": "rename",
                    "original_column": "id",
                    "new_column": "participant_id",
                    "reason": "Schema alignment",
                    "row_count_affected": 100,
                },
                {
                    "change_type": "add",
                    "new_column": "status",
                    "reason": "Required field",
                    "row_count_affected": 100,
                    "original_column": None,
                },
            ],
            "summary": {
                "job_id": "test-job-abc",
                "version": 3,
                "timestamp": "2024-01-15T10:30:00",
                "original_data_csv": "id,name\n1,John",
                "aligned_data_csv": "participant_id,participant_name,status\n1,John,active",
                "total_changes": 2,
                "columns_renamed": 1,
                "columns_added": 1,
                "columns_removed": 0,
                "rows_original": 1,
                "rows_aligned": 1,
            },
        }

        results = SchemaAlignmentResults.from_dict(data)

        assert len(results.schema_alignment_results) == 2
        assert results.schema_alignment_results[0].change_type == "rename"
        assert results.schema_alignment_results[0].original_column == "id"
        assert results.schema_alignment_results[0].new_column == "participant_id"
        assert results.schema_alignment_results[1].change_type == "add"
        assert results.schema_alignment_results[1].new_column == "status"

        assert results.summary.job_id == "test-job-abc"
        assert results.summary.version == 3
        assert results.summary.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert results.summary.total_changes == 2
        assert results.summary.columns_renamed == 1
        assert results.summary.columns_added == 1

    def test_from_dict_with_empty_changes(self):
        """Test from_dict with empty schema_alignment_results."""
        data = {
            "schema_alignment_results": [],
            "summary": {
                "job_id": "test-job-empty",
                "version": 1,
                "timestamp": "2024-01-15T10:30:00",
                "original_data_csv": "id,name\n1,John",
                "aligned_data_csv": "id,name\n1,John",
                "total_changes": 0,
                "columns_renamed": 0,
                "columns_added": 0,
                "columns_removed": 0,
                "rows_original": 1,
                "rows_aligned": 1,
            },
        }

        results = SchemaAlignmentResults.from_dict(data)

        assert len(results.schema_alignment_results) == 0
        assert results.summary.job_id == "test-job-empty"
        assert results.summary.total_changes == 0

    def test_from_dict_missing_changes_key(self):
        """Test from_dict when schema_alignment_results key is missing."""
        data = {
            "summary": {
                "job_id": "test-job-missing",
                "version": 1,
                "timestamp": "2024-01-15T10:30:00",
                "original_data_csv": "id,name\n1,John",
                "aligned_data_csv": "id,name\n1,John",
                "total_changes": 0,
                "columns_renamed": 0,
                "columns_added": 0,
                "columns_removed": 0,
                "rows_original": 1,
                "rows_aligned": 1,
            }
        }

        results = SchemaAlignmentResults.from_dict(data)

        assert len(results.schema_alignment_results) == 0
        assert results.summary.job_id == "test-job-missing"

    def test_round_trip_serialization(self):
        """Test round-trip serialization (to_dict -> from_dict)."""
        changes = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="id",
                new_column="participant_id",
                reason="Schema alignment",
                row_count_affected=100,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                new_column="status",
                reason="Required field",
                row_count_affected=100,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="temp_field",
                reason="Not needed",
                row_count_affected=100,
            ),
        ]

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-round-trip",
            version=1,
            original_data_csv="id,name,temp_field\n1,John,temp\n2,Jane,temp",
            aligned_data_csv="participant_id,participant_name,status\n1,John,active\n2,Jane,active",
            total_changes=3,
            columns_renamed=1,
            columns_added=1,
            columns_removed=1,
            rows_original=2,
            rows_aligned=2,
        )

        original_results = SchemaAlignmentResults(schema_alignment_results=changes, summary=summary)

        # Serialize to dict
        data_dict = original_results.to_dict()

        # Deserialize from dict
        restored_results = SchemaAlignmentResults.from_dict(data_dict)

        # Compare changes
        assert len(restored_results.schema_alignment_results) == len(original_results.schema_alignment_results)
        for i, change in enumerate(restored_results.schema_alignment_results):
            original_change = original_results.schema_alignment_results[i]
            assert change.change_type == original_change.change_type
            assert change.original_column == original_change.original_column
            assert change.new_column == original_change.new_column
            assert change.reason == original_change.reason
            assert change.row_count_affected == original_change.row_count_affected

        # Compare summary
        assert restored_results.summary.job_id == original_results.summary.job_id
        assert restored_results.summary.version == original_results.summary.version
        assert restored_results.summary.timestamp == original_results.summary.timestamp
        assert restored_results.summary.total_changes == original_results.summary.total_changes
        assert restored_results.summary.columns_renamed == original_results.summary.columns_renamed
        assert restored_results.summary.columns_added == original_results.summary.columns_added
        assert restored_results.summary.columns_removed == original_results.summary.columns_removed

    def test_json_encoding(self):
        """Test JSON encoding with datetime handling."""
        import json

        summary = SchemaAlignmentResultsSummary(
            job_id="test-job-json",
            version=1,
            original_data_csv="id,name\n1,John",
            aligned_data_csv="participant_id,participant_name\n1,John",
        )

        results = SchemaAlignmentResults(summary=summary)

        # Test that the model can be JSON serialized
        json_str = results.model_dump_json()
        parsed_data = json.loads(json_str)

        assert "schema_alignment_results" in parsed_data
        assert "summary" in parsed_data
        assert parsed_data["summary"]["job_id"] == "test-job-json"
        assert parsed_data["summary"]["version"] == 1
        assert "timestamp" in parsed_data["summary"]
        assert isinstance(parsed_data["summary"]["timestamp"], str)  # Should be ISO format string

    def test_field_validation(self):
        """Test field validation and constraints."""
        # Test that summary is required
        with pytest.raises(ValueError):
            SchemaAlignmentResults()  # Missing required summary field

    def test_default_values(self):
        """Test default values for optional fields."""
        summary = SchemaAlignmentResultsSummary(
            job_id="test-defaults",
            version=1,
            original_data_csv="test",
            aligned_data_csv="test",
        )

        results = SchemaAlignmentResults(summary=summary)

        # Check default values
        assert len(results.schema_alignment_results) == 0
        assert isinstance(results.summary.timestamp, datetime)
        assert results.summary.total_changes == 0
        assert results.summary.columns_renamed == 0
        assert results.summary.columns_added == 0
        assert results.summary.columns_removed == 0

    def test_complex_changes_scenario(self):
        """Test with complex schema alignment scenario."""
        changes = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="sample_id",
                new_column="participant_id",
                reason="Schema standardization",
                row_count_affected=1000,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="sample_name",
                new_column="participant_name",
                reason="Schema standardization",
                row_count_affected=1000,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                new_column="status",
                reason="Required for validation",
                row_count_affected=1000,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                new_column="created_date",
                reason="Audit trail requirement",
                row_count_affected=1000,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="temp_field",
                reason="Not part of target schema",
                row_count_affected=1000,
            ),
        ]

        summary = SchemaAlignmentResultsSummary(
            job_id="test-complex",
            version=1,
            original_data_csv="sample_id,sample_name,age,temp_field\n1,John,25,temp\n2,Jane,30,temp",
            aligned_data_csv="participant_id,participant_name,age,status,created_date\n1,John,25,active,2024-01-15\n2,Jane,30,active,2024-01-15",
            total_changes=5,
            columns_renamed=2,
            columns_added=2,
            columns_removed=1,
            rows_original=2,
            rows_aligned=2,
        )

        results = SchemaAlignmentResults(schema_alignment_results=changes, summary=summary)

        assert len(results.schema_alignment_results) == 5
        assert results.summary.total_changes == 5
        assert results.summary.columns_renamed == 2
        assert results.summary.columns_added == 2
        assert results.summary.columns_removed == 1

        # Test round-trip with complex data
        data_dict = results.to_dict()
        restored = SchemaAlignmentResults.from_dict(data_dict)
        assert len(restored.schema_alignment_results) == 5
        assert restored.summary.total_changes == 5
