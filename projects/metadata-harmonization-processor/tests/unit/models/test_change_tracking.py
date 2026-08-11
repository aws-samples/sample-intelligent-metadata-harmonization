# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for change tracking models.

This module tests the ChangeObject, ChangesSummary, and ChangeTrackingResults
models to ensure proper validation, serialization, and consistency checking.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from metadata_harmonization_processor.models.change_tracking import (
    ChangeObject,
    ChangesSummary,
    ChangeTrackingResults,
)


class TestChangeObject:
    """Test cases for ChangeObject model."""

    def test_valid_change_object_creation(self):
        """Test creating a valid ChangeObject with row and column."""
        change = ChangeObject(
            change_type="rename",
            source_type="user",
            component="validation",
            row=1,
            column="status",
            old_value="old",
            new_value="new",
            source_version=1,
            target_version=2,
        )

        assert change.change_type == "rename"
        assert change.source_type == "user"
        assert change.component == "validation"
        assert change.row == 1
        assert change.column == "status"
        assert change.old_value == "old"
        assert change.new_value == "new"
        assert change.source_version == 1
        assert change.target_version == 2
        assert change.change_id.startswith("chg_")
        assert len(change.change_id) == 12  # "chg_" + 8 hex chars

    def test_change_object_schema_alignment_without_row(self):
        """Test ChangeObject for schema_alignment component (row is optional)."""
        change = ChangeObject(
            change_type="add",
            source_type="system",
            component="schema_alignment",
            column="new_column",
            new_value="default_value",
            source_version=1,
            target_version=2,
            confidence_score=0.85,
        )

        assert change.column == "new_column"
        assert change.row is None
        assert change.confidence_score == 0.85

    def test_add_change_validation(self):
        """Test validation for 'add' change type."""
        change = ChangeObject(
            change_type="add",
            source_type="system",
            component="validation",
            row=2,
            column="sample_id",
            new_value="added_value",
            source_version=1,
            target_version=2,
        )
        assert change.old_value is None
        assert change.new_value == "added_value"

        with pytest.raises(ValidationError, match="'add' changes should not have old_value"):
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=2,
                column="sample_id",
                old_value="should_not_exist",
                new_value="added_value",
                source_version=1,
                target_version=2,
            )

        with pytest.raises(ValidationError, match="'add' changes must have new_value"):
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=2,
                column="sample_id",
                source_version=1,
                target_version=2,
            )

    def test_remove_change_validation(self):
        """Test validation for 'remove' change type."""
        change = ChangeObject(
            change_type="remove",
            source_type="user",
            component="validation",
            row=3,
            column="deprecated_field",
            old_value="removed_value",
            source_version=1,
            target_version=2,
        )
        assert change.old_value == "removed_value"
        assert change.new_value is None

        with pytest.raises(ValidationError, match="'remove' changes should not have new_value"):
            ChangeObject(
                change_type="remove",
                source_type="user",
                component="validation",
                row=3,
                column="deprecated_field",
                old_value="removed_value",
                new_value="should_not_exist",
                source_version=1,
                target_version=2,
            )

        with pytest.raises(ValidationError, match="'remove' changes must have old_value"):
            ChangeObject(
                change_type="remove",
                source_type="user",
                component="validation",
                row=3,
                column="deprecated_field",
                source_version=1,
                target_version=2,
            )

    def test_rename_change_validation(self):
        """Test validation for 'rename' change type."""
        change = ChangeObject(
            change_type="rename",
            source_type="user",
            component="validation",
            row=4,
            column="category",
            old_value="old_value",
            new_value="new_value",
            source_version=1,
            target_version=2,
        )
        assert change.old_value == "old_value"
        assert change.new_value == "new_value"

        with pytest.raises(
            ValidationError,
            match="'rename' changes must have both old_value and new_value",
        ):
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=4,
                column="category",
                old_value="old_value",
                source_version=1,
                target_version=2,
            )

        with pytest.raises(
            ValidationError,
            match="'rename' changes must have different old_value and new_value",
        ):
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=4,
                column="category",
                old_value="same_value",
                new_value="same_value",
                source_version=1,
                target_version=2,
            )

    def test_version_sequence_validation(self):
        """Test version sequence validation."""
        change = ChangeObject(
            change_type="add",
            source_type="system",
            component="validation",
            row=5,
            column="priority",
            new_value="test",
            source_version=1,
            target_version=3,
        )
        assert change.target_version > change.source_version

        with pytest.raises(ValidationError, match="target_version must be greater than source_version"):
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=5,
                column="priority",
                new_value="test",
                source_version=2,
                target_version=2,
            )

    def test_validation_component_requires_row(self):
        """Test that validation component requires a row number."""
        with pytest.raises(
            ValidationError,
            match="Row must be provided for validation component changes",
        ):
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                column="some_column",
                new_value="test",
                source_version=1,
                target_version=2,
            )

    def test_schema_alignment_component_row_optional(self):
        """Test that schema_alignment component doesn't require row."""
        change = ChangeObject(
            change_type="add",
            source_type="system",
            component="schema_alignment",
            column="new_field",
            new_value="test",
            source_version=1,
            target_version=2,
        )
        assert change.row is None
        assert change.column == "new_field"

    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        change = ChangeObject(
            change_type="add",
            source_type="system",
            component="validation",
            row=7,
            column="test_col",
            new_value="test",
            source_version=1,
            target_version=2,
            confidence_score=0.75,
        )
        assert change.confidence_score == 0.75

        with pytest.raises(
            ValidationError,
            match="confidence_score should only be present for system changes",
        ):
            ChangeObject(
                change_type="add",
                source_type="user",
                component="validation",
                row=7,
                column="test_col",
                new_value="test",
                source_version=1,
                target_version=2,
                confidence_score=0.75,
            )

    def test_column_min_length_validation(self):
        """Test that column name must be non-empty."""
        with pytest.raises(ValidationError):
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=1,
                column="",
                new_value="test",
                source_version=1,
                target_version=2,
            )

    def test_row_ge_1_validation(self):
        """Test that row must be >= 1 when provided."""
        with pytest.raises(ValidationError):
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=0,
                column="test_col",
                new_value="test",
                source_version=1,
                target_version=2,
            )

    def test_timestamp_validation(self):
        """Test timestamp format validation."""
        valid_timestamps = [
            "2025-09-30T12:00:00Z",
            "2025-09-30T12:00:00+00:00",
            "2025-09-30T12:00:00.123Z",
            datetime.now(timezone.utc).isoformat(),
        ]

        for timestamp in valid_timestamps:
            change = ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=8,
                column="date_field",
                new_value="test",
                source_version=1,
                target_version=2,
                timestamp=timestamp,
            )
            assert change.timestamp == timestamp

        with pytest.raises(ValidationError, match="timestamp must be in ISO-8601 format"):
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=8,
                column="date_field",
                new_value="test",
                source_version=1,
                target_version=2,
                timestamp="invalid-timestamp",
            )


class TestChangesSummary:
    """Test cases for ChangesSummary model."""

    def test_valid_summary_creation(self):
        """Test creating a valid ChangesSummary."""
        summary = ChangesSummary(
            total_changes=5,
            adds=2,
            removes=1,
            renames=2,
            system_changes=3,
            user_changes=2,
        )

        assert summary.total_changes == 5
        assert summary.adds == 2
        assert summary.removes == 1
        assert summary.renames == 2
        assert summary.system_changes == 3
        assert summary.user_changes == 2

    def test_total_changes_validation(self):
        """Test total_changes consistency validation."""
        summary = ChangesSummary(
            total_changes=3,
            adds=1,
            removes=1,
            renames=1,
            system_changes=2,
            user_changes=1,
        )
        assert summary.total_changes == 3

        with pytest.raises(
            ValidationError,
            match="total_changes \\(5\\) must equal sum of adds \\+ removes \\+ renames \\(3\\)",
        ):
            ChangesSummary(
                total_changes=5,
                adds=1,
                removes=1,
                renames=1,
                system_changes=2,
                user_changes=1,
            )

    def test_source_totals_validation(self):
        """Test system_changes + user_changes validation."""
        summary = ChangesSummary(
            total_changes=4,
            adds=2,
            removes=1,
            renames=1,
            system_changes=2,
            user_changes=2,
        )
        assert summary.system_changes + summary.user_changes == summary.total_changes

        with pytest.raises(
            ValidationError,
            match="system_changes \\(3\\) \\+ user_changes \\(2\\) must equal total_changes \\(4\\)",
        ):
            ChangesSummary(
                total_changes=4,
                adds=2,
                removes=1,
                renames=1,
                system_changes=3,
                user_changes=2,
            )

    def test_from_changes_factory_method(self):
        """Test creating summary from change objects."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=1,
                column="col_a",
                new_value="test1",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=2,
                column="col_b",
                old_value="old",
                new_value="new",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_type="remove",
                source_type="system",
                component="validation",
                row=3,
                column="col_c",
                old_value="removed",
                source_version=1,
                target_version=2,
            ),
        ]

        summary = ChangesSummary.from_changes(changes)

        assert summary.total_changes == 3
        assert summary.adds == 1
        assert summary.removes == 1
        assert summary.renames == 1
        assert summary.system_changes == 2
        assert summary.user_changes == 1

    def test_empty_changes_summary(self):
        """Test summary with no changes."""
        summary = ChangesSummary.from_changes([])

        assert summary.total_changes == 0
        assert summary.adds == 0
        assert summary.removes == 0
        assert summary.renames == 0
        assert summary.system_changes == 0
        assert summary.user_changes == 0


class TestChangeTrackingResults:
    """Test cases for ChangeTrackingResults model."""

    def test_valid_tracking_results_creation(self):
        """Test creating valid ChangeTrackingResults."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=1,
                column="test_col",
                new_value="test",
                source_version=1,
                target_version=2,
            )
        ]

        summary = ChangesSummary.from_changes(changes)

        tracking_results = ChangeTrackingResults(
            changes=changes, summary=summary, comparison_metadata={"test": "metadata"}
        )

        assert len(tracking_results.changes) == 1
        assert tracking_results.summary.total_changes == 1
        assert tracking_results.comparison_metadata["test"] == "metadata"

    def test_summary_consistency_validation(self):
        """Test summary consistency with changes list."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=1,
                column="test_col",
                new_value="test",
                source_version=1,
                target_version=2,
            )
        ]

        correct_summary = ChangesSummary.from_changes(changes)
        tracking_results = ChangeTrackingResults(changes=changes, summary=correct_summary, comparison_metadata={})
        assert tracking_results.summary.total_changes == 1

        incorrect_summary = ChangesSummary(
            total_changes=2,
            adds=1,
            removes=1,
            renames=0,
            system_changes=1,
            user_changes=1,
        )

        with pytest.raises(ValidationError, match="Summary statistics do not match the changes list"):
            ChangeTrackingResults(changes=changes, summary=incorrect_summary, comparison_metadata={})

    def test_create_from_changes_factory_method(self):
        """Test creating tracking results from changes."""
        changes = [
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=2,
                column="col_b",
                old_value="old",
                new_value="new",
                source_version=1,
                target_version=2,
            ),
            ChangeObject(
                change_type="add",
                source_type="system",
                component="schema_alignment",
                column="col_c",
                new_value="added",
                source_version=1,
                target_version=2,
            ),
        ]

        tracking_results = ChangeTrackingResults.create_from_changes(
            changes=changes, comparison_metadata={"detection_method": "automated"}
        )

        assert len(tracking_results.changes) == 2
        assert tracking_results.summary.total_changes == 2
        assert tracking_results.summary.renames == 1
        assert tracking_results.summary.adds == 1
        assert tracking_results.summary.user_changes == 1
        assert tracking_results.summary.system_changes == 1
        assert tracking_results.comparison_metadata["detection_method"] == "automated"

    def test_create_from_changes_with_default_metadata(self):
        """Test factory method with default metadata."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=4,
                column="col_d",
                new_value="test",
                source_version=1,
                target_version=2,
            )
        ]

        tracking_results = ChangeTrackingResults.create_from_changes(changes)

        assert "detection_timestamp" in tracking_results.comparison_metadata
        assert "total_changes_detected" in tracking_results.comparison_metadata
        assert tracking_results.comparison_metadata["total_changes_detected"] == 1

    def test_serialization_methods(self):
        """Test to_dict and from_dict methods."""
        changes = [
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=5,
                column="col_e",
                old_value="original",
                new_value="updated",
                source_version=1,
                target_version=2,
                user_context={"reason": "correction"},
            )
        ]

        original_tracking = ChangeTrackingResults.create_from_changes(
            changes=changes, comparison_metadata={"test_key": "test_value"}
        )

        data_dict = original_tracking.to_dict()

        assert "changes" in data_dict
        assert "summary" in data_dict
        assert "comparison_metadata" in data_dict
        assert len(data_dict["changes"]) == 1
        assert data_dict["summary"]["total_changes"] == 1
        assert data_dict["comparison_metadata"]["test_key"] == "test_value"

        restored_tracking = ChangeTrackingResults.from_dict(data_dict)

        assert len(restored_tracking.changes) == 1
        assert restored_tracking.changes[0].change_type == "rename"
        assert restored_tracking.changes[0].old_value == "original"
        assert restored_tracking.changes[0].new_value == "updated"
        assert restored_tracking.changes[0].user_context["reason"] == "correction"
        assert restored_tracking.summary.total_changes == 1
        assert restored_tracking.comparison_metadata["test_key"] == "test_value"

    def test_empty_tracking_results(self):
        """Test tracking results with no changes."""
        tracking_results = ChangeTrackingResults.create_from_changes([])

        assert len(tracking_results.changes) == 0
        assert tracking_results.summary.total_changes == 0
        assert tracking_results.summary.adds == 0
        assert tracking_results.summary.removes == 0
        assert tracking_results.summary.renames == 0
        assert tracking_results.summary.system_changes == 0
        assert tracking_results.summary.user_changes == 0


class TestChangeTrackingIntegration:
    """Integration tests for change tracking models."""

    def test_complex_change_scenario(self):
        """Test a complex scenario with multiple change types and sources."""
        changes = [
            ChangeObject(
                change_type="add",
                source_type="system",
                component="schema_alignment",
                column="auto_id",
                new_value="auto_generated_id",
                source_version=1,
                target_version=2,
                confidence_score=0.95,
            ),
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=1,
                column="new_column",
                new_value="default_value",
                source_version=1,
                target_version=2,
                confidence_score=0.80,
            ),
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=5,
                column="data_field",
                old_value="incorrect_data",
                new_value="corrected_data",
                source_version=1,
                target_version=2,
                user_context={
                    "correction_method": "manual_edit",
                    "user_id": "analyst_123",
                },
            ),
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=10,
                column="name_field",
                old_value="typo_value",
                new_value="fixed_value",
                source_version=1,
                target_version=2,
                user_context={"correction_method": "bulk_operation"},
            ),
            ChangeObject(
                change_type="remove",
                source_type="system",
                component="schema_alignment",
                column="deprecated_col",
                old_value="deprecated_field",
                source_version=1,
                target_version=2,
                confidence_score=0.90,
            ),
        ]

        tracking_results = ChangeTrackingResults.create_from_changes(
            changes=changes,
            comparison_metadata={
                "detection_timestamp": "2025-09-30T12:00:00Z",
                "compared_versions": [1, 2],
                "detection_algorithm": "cell_level_comparison",
                "processing_duration_ms": 1250,
            },
        )

        assert tracking_results.summary.total_changes == 5
        assert tracking_results.summary.adds == 2
        assert tracking_results.summary.removes == 1
        assert tracking_results.summary.renames == 2
        assert tracking_results.summary.system_changes == 3
        assert tracking_results.summary.user_changes == 2

        data_dict = tracking_results.to_dict()
        restored_tracking = ChangeTrackingResults.from_dict(data_dict)

        assert len(restored_tracking.changes) == 5
        assert restored_tracking.summary.total_changes == 5
        assert restored_tracking.comparison_metadata["detection_algorithm"] == "cell_level_comparison"

        system_adds = [c for c in restored_tracking.changes if c.change_type == "add" and c.source_type == "system"]
        assert len(system_adds) == 2
        assert all(c.confidence_score is not None for c in system_adds)

        user_renames = [c for c in restored_tracking.changes if c.change_type == "rename" and c.source_type == "user"]
        assert len(user_renames) == 2
        assert all(c.user_context is not None for c in user_renames)

    def test_version_progression_tracking(self):
        """Test tracking changes across multiple versions."""
        v1_to_v2_changes = [
            ChangeObject(
                change_type="add",
                source_type="system",
                component="validation",
                row=1,
                column="col_a",
                new_value="initial_value",
                source_version=1,
                target_version=2,
            )
        ]

        v2_to_v3_changes = [
            ChangeObject(
                change_type="rename",
                source_type="user",
                component="validation",
                row=1,
                column="col_a",
                old_value="initial_value",
                new_value="updated_value",
                source_version=2,
                target_version=3,
            ),
            ChangeObject(
                change_type="add",
                source_type="system",
                component="schema_alignment",
                column="col_b",
                new_value="new_field",
                source_version=2,
                target_version=3,
            ),
        ]

        v1_to_v2_tracking = ChangeTrackingResults.create_from_changes(
            v1_to_v2_changes, {"version_transition": "1_to_2"}
        )

        v2_to_v3_tracking = ChangeTrackingResults.create_from_changes(
            v2_to_v3_changes, {"version_transition": "2_to_3"}
        )

        assert v1_to_v2_tracking.summary.total_changes == 1
        assert v1_to_v2_tracking.summary.adds == 1

        assert v2_to_v3_tracking.summary.total_changes == 2
        assert v2_to_v3_tracking.summary.adds == 1
        assert v2_to_v3_tracking.summary.renames == 1
        assert v2_to_v3_tracking.summary.system_changes == 1
        assert v2_to_v3_tracking.summary.user_changes == 1

        for change in v1_to_v2_tracking.changes:
            assert change.source_version == 1
            assert change.target_version == 2

        for change in v2_to_v3_tracking.changes:
            assert change.source_version == 2
            assert change.target_version == 3
