# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for CombinedResults model.

Tests cover model initialization, validation, serialization, and utility methods
for managing combined validation and schema alignment results.
"""

import json


from metadata_harmonization_processor.models.change_tracking import (
    ChangeObject,
    ChangesSummary,
    ChangeTrackingResults,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResults,
    SchemaAlignmentResultsSummary,
)
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class TestCombinedResultsInitialization:
    """Test CombinedResults model initialization and basic functionality."""

    def test_empty_initialization(self):
        """Test creating CombinedResults with default values."""
        combined_results = CombinedResults()

        assert combined_results.validation_results is None
        assert combined_results.schema_alignment_results is None
        assert combined_results.change_tracking is None
        assert not combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()
        assert not combined_results.has_change_tracking()

    def test_initialization_with_validation_results_only(self):
        """Test creating CombinedResults with validation results only."""
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_column",
                    current_value="invalid",
                    error_type=ValidationErrorType.INVALID_OPTION,
                    valid_options=["valid1", "valid2"],
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=10,
                total_errors=1,
                columns_validated=1,
                error_types={ValidationErrorType.INVALID_OPTION: 1},
            ),
        )

        combined_results = CombinedResults(validation_results=validation_results)

        assert combined_results.validation_results == validation_results
        assert combined_results.schema_alignment_results is None
        assert combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()

    def test_initialization_with_schema_alignment_results_only(self):
        """Test creating CombinedResults with schema alignment results only."""
        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[
                SchemaAlignmentChangeDetail(
                    change_type="rename",
                    original_column="old_col",
                    new_column="new_col",
                    reason="Schema alignment",
                    row_count_affected=100,
                )
            ],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="old_col\nvalue1\nvalue2",
                aligned_data_csv="new_col\nvalue1\nvalue2",
                columns_renamed=1,
                rows_original=2,
                rows_aligned=2,
            ),
        )

        combined_results = CombinedResults(schema_alignment_results=schema_alignment_results)

        assert combined_results.validation_results is None
        assert combined_results.schema_alignment_results == schema_alignment_results
        assert not combined_results.has_validation_results()
        assert combined_results.has_schema_alignment_results()

    def test_initialization_with_both_results(self):
        """Test creating CombinedResults with both result types."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=5, total_errors=0, columns_validated=0, error_types={}),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
                rows_original=1,
                rows_aligned=1,
            ),
        )

        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )

        assert combined_results.validation_results == validation_results
        assert combined_results.schema_alignment_results == schema_alignment_results
        assert combined_results.has_validation_results()
        assert combined_results.has_schema_alignment_results()


class TestCombinedResultsUtilityMethods:
    """Test CombinedResults utility methods."""

    def test_has_validation_results_with_none(self):
        """Test has_validation_results with None validation results."""
        combined_results = CombinedResults(validation_results=None)
        assert not combined_results.has_validation_results()

    def test_has_validation_results_with_valid_results(self):
        """Test has_validation_results with valid validation results."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=0, total_errors=0, columns_validated=0, error_types={}),
        )
        combined_results = CombinedResults(validation_results=validation_results)
        assert combined_results.has_validation_results()

    def test_has_schema_alignment_results_with_none(self):
        """Test has_schema_alignment_results with None schema alignment results."""
        combined_results = CombinedResults(schema_alignment_results=None)
        assert not combined_results.has_schema_alignment_results()

    def test_has_schema_alignment_results_with_valid_results(self):
        """Test has_schema_alignment_results with valid schema alignment results."""
        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1\nval1",
                aligned_data_csv="aligned_col1\nval1",
                rows_original=1,
                rows_aligned=1,
            ),
        )
        combined_results = CombinedResults(schema_alignment_results=schema_alignment_results)
        assert combined_results.has_schema_alignment_results()


class TestCombinedResultsSerialization:
    """Test CombinedResults serialization and deserialization."""

    def test_to_dict_with_empty_results(self):
        """Test to_dict with empty CombinedResults."""
        combined_results = CombinedResults()
        result_dict = combined_results.to_dict()

        assert result_dict == {}

    def test_to_dict_with_validation_results_only(self):
        """Test to_dict with validation results only."""
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_col",
                    current_value="invalid",
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=1,
                total_errors=1,
                columns_validated=1,
                error_types={ValidationErrorType.REQUIRED_VALUE: 1},
            ),
        )

        combined_results = CombinedResults(validation_results=validation_results)
        result_dict = combined_results.to_dict()

        assert "validation_results" in result_dict
        assert "schema_alignment_results" not in result_dict
        assert result_dict["validation_results"]["summary"]["total_errors"] == 1

    def test_to_dict_with_schema_alignment_results_only(self):
        """Test to_dict with schema alignment results only."""
        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[
                SchemaAlignmentChangeDetail(
                    change_type="add",
                    new_column="new_col",
                    reason="Added for alignment",
                    row_count_affected=50,
                )
            ],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1\nval1",
                aligned_data_csv="col1,new_col\nval1,",
                columns_added=1,
                rows_original=1,
                rows_aligned=1,
            ),
        )

        combined_results = CombinedResults(schema_alignment_results=schema_alignment_results)
        result_dict = combined_results.to_dict()

        assert "schema_alignment_results" in result_dict
        assert "validation_results" not in result_dict
        assert result_dict["schema_alignment_results"]["summary"]["columns_added"] == 1

    def test_to_dict_with_both_results(self):
        """Test to_dict with both result types."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=2, total_errors=0, columns_validated=0, error_types={}),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="new_col1,new_col2\nval1,val2",
                columns_renamed=2,
                rows_original=1,
                rows_aligned=1,
            ),
        )

        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )
        result_dict = combined_results.to_dict()

        assert "validation_results" in result_dict
        assert "schema_alignment_results" in result_dict
        assert result_dict["validation_results"]["summary"]["total_errors"] == 0
        assert result_dict["schema_alignment_results"]["summary"]["columns_renamed"] == 2

    def test_from_dict_with_empty_data(self):
        """Test from_dict with empty data."""
        combined_results = CombinedResults.from_dict({})

        assert combined_results.validation_results is None
        assert combined_results.schema_alignment_results is None
        assert not combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()

    def test_from_dict_with_validation_results_only(self):
        """Test from_dict with validation results only."""
        data = {
            "validation_results": {
                "validationResults": [
                    {
                        "row": 1,
                        "column": "test_col",
                        "currentValue": "invalid",
                        "errorType": "REQUIRED_VALUE",
                        "validOptions": None,
                        "recommendedValue": None,
                    }
                ],
                "summary": {
                    "totalRows": 1,
                    "totalErrors": 1,
                    "columnsValidated": 0,
                    "errorTypes": {"REQUIRED_VALUE": 1},
                },
            }
        }

        combined_results = CombinedResults.from_dict(data)

        assert combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()
        assert combined_results.validation_results.summary.total_errors == 1

    def test_from_dict_with_schema_alignment_results_only(self):
        """Test from_dict with schema alignment results only."""
        data = {
            "schema_alignment_results": {
                "schema_alignment_results": [
                    {
                        "change_type": "rename",
                        "original_column": "old_col",
                        "new_column": "new_col",
                        "reason": "Schema alignment",
                        "row_count_affected": 100,
                    }
                ],
                "summary": {
                    "job_id": "test-job",
                    "version": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "original_data_csv": "old_col\nval1",
                    "aligned_data_csv": "new_col\nval1",
                    "columns_renamed": 1,
                    "rows_original": 1,
                    "rows_aligned": 1,
                },
            }
        }

        combined_results = CombinedResults.from_dict(data)

        assert not combined_results.has_validation_results()
        assert combined_results.has_schema_alignment_results()
        assert combined_results.schema_alignment_results.summary.columns_renamed == 1

    def test_from_dict_with_both_results(self):
        """Test from_dict with both result types."""
        data = {
            "validation_results": {
                "validationResults": [],
                "summary": {
                    "totalRows": 2,
                    "totalErrors": 0,
                    "columnsValidated": 0,
                    "errorTypes": {},
                },
            },
            "schema_alignment_results": {
                "schema_alignment_results": [],
                "summary": {
                    "job_id": "test-job",
                    "version": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "original_data_csv": "col1,col2\nval1,val2",
                    "aligned_data_csv": "new_col1,new_col2\nval1,val2",
                    "columns_renamed": 2,
                    "rows_original": 1,
                    "rows_aligned": 1,
                },
            },
        }

        combined_results = CombinedResults.from_dict(data)

        assert combined_results.has_validation_results()
        assert combined_results.has_schema_alignment_results()
        assert combined_results.validation_results.summary.total_errors == 0
        assert combined_results.schema_alignment_results.summary.columns_renamed == 2

    def test_round_trip_serialization(self):
        """Test round-trip serialization (to_dict -> from_dict)."""
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_column",
                    current_value="invalid",
                    error_type=ValidationErrorType.INVALID_PATTERN,
                    recommended_value="valid_pattern",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=5,
                total_errors=1,
                columns_validated=1,
                error_types={ValidationErrorType.INVALID_PATTERN: 1},
            ),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[
                SchemaAlignmentChangeDetail(
                    change_type="remove",
                    original_column="old_col",
                    reason="Column not needed",
                    row_count_affected=5,
                )
            ],
            summary=SchemaAlignmentResultsSummary(
                job_id="round-trip-test",
                version=2,
                original_data_csv="col1,old_col\nval1,val2",
                aligned_data_csv="col1\nval1",
                columns_removed=1,
                rows_original=1,
                rows_aligned=1,
            ),
        )

        original = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )

        # Serialize to dict
        data = original.to_dict()

        # Deserialize from dict
        reconstructed = CombinedResults.from_dict(data)

        # Verify equality
        assert reconstructed.has_validation_results() == original.has_validation_results()
        assert reconstructed.has_schema_alignment_results() == original.has_schema_alignment_results()

        # Verify validation results
        assert reconstructed.validation_results.summary.total_errors == original.validation_results.summary.total_errors
        assert len(reconstructed.validation_results.validation_results) == len(
            original.validation_results.validation_results
        )

        # Verify schema alignment results
        assert reconstructed.schema_alignment_results.summary.job_id == original.schema_alignment_results.summary.job_id
        assert (
            reconstructed.schema_alignment_results.summary.columns_removed
            == original.schema_alignment_results.summary.columns_removed
        )
        assert len(reconstructed.schema_alignment_results.schema_alignment_results) == len(
            original.schema_alignment_results.schema_alignment_results
        )


class TestCombinedResultsComplexScenarios:
    """Test CombinedResults in complex scenarios."""

    def test_json_serialization_compatibility(self):
        """Test that CombinedResults can be serialized to JSON."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=10, total_errors=0, columns_validated=0, error_types={}),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="json-test",
                version=1,
                original_data_csv="col1\nval1",
                aligned_data_csv="aligned_col1\nval1",
                rows_original=1,
                rows_aligned=1,
            ),
        )

        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )

        # Convert to dict and then to JSON
        data = combined_results.to_dict()
        json_str = json.dumps(data, default=str)  # default=str handles datetime objects

        # Verify JSON can be parsed
        parsed_data = json.loads(json_str)

        # Verify structure is preserved
        assert "validation_results" in parsed_data
        assert "schema_alignment_results" in parsed_data
        assert parsed_data["validation_results"]["summary"]["total_rows"] == 10
        assert parsed_data["schema_alignment_results"]["summary"]["job_id"] == "json-test"

    def test_model_dump_compatibility(self):
        """Test that CombinedResults works with Pydantic model_dump."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=5, total_errors=0, columns_validated=0, error_types={}),
        )

        combined_results = CombinedResults(validation_results=validation_results)

        # Test model_dump
        data = combined_results.model_dump()

        assert "validation_results" in data
        assert "schema_alignment_results" in data
        assert data["validation_results"]["summary"]["total_rows"] == 5
        assert data["schema_alignment_results"] is None

    def test_partial_data_handling(self):
        """Test handling of partial or missing data in from_dict."""
        # Test with null validation_results
        data_with_null_validation = {
            "validation_results": None,
            "schema_alignment_results": {
                "schema_alignment_results": [],
                "summary": {
                    "job_id": "partial-test",
                    "version": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "original_data_csv": "col1\nval1",
                    "aligned_data_csv": "col1\nval1",
                    "rows_original": 1,
                    "rows_aligned": 1,
                },
            },
        }

        combined_results = CombinedResults.from_dict(data_with_null_validation)

        assert not combined_results.has_validation_results()
        assert combined_results.has_schema_alignment_results()
        assert combined_results.schema_alignment_results.summary.job_id == "partial-test"

        # Test with missing schema_alignment_results key
        data_missing_schema = {
            "validation_results": {
                "validationResults": [],
                "summary": {
                    "totalRows": 3,
                    "totalErrors": 0,
                    "columnsValidated": 0,
                    "errorTypes": {},
                },
            }
        }

        combined_results = CombinedResults.from_dict(data_missing_schema)

        assert combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()
        assert combined_results.validation_results.summary.total_rows == 3


class TestCombinedResultsChangeTracking:
    """Test CombinedResults change tracking functionality."""

    def test_initialization_with_change_tracking_only(self):
        """Test creating CombinedResults with change tracking only."""
        change_tracking = ChangeTrackingResults(
            changes=[
                ChangeObject(
                    change_type="add",
                    source_type="system",
                    component="validation",
                    row=1,
                    column="col_a",
                    new_value="new_value",
                    source_version=1,
                    target_version=2,
                )
            ],
            summary=ChangesSummary(
                total_changes=1,
                adds=1,
                removes=0,
                renames=0,
                system_changes=1,
                user_changes=0,
            ),
        )

        combined_results = CombinedResults(change_tracking=change_tracking)

        assert combined_results.validation_results is None
        assert combined_results.schema_alignment_results is None
        assert combined_results.change_tracking == change_tracking
        assert not combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()
        assert combined_results.has_change_tracking()

    def test_initialization_with_all_results(self):
        """Test creating CombinedResults with all result types including change tracking."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=5, total_errors=0, columns_validated=0, error_types={}),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
                rows_original=1,
                rows_aligned=1,
            ),
        )

        change_tracking = ChangeTrackingResults(
            changes=[
                ChangeObject(
                    change_type="rename",
                    source_type="user",
                    component="validation",
                    row=2,
                    column="col_b",
                    old_value="old_value",
                    new_value="new_value",
                    source_version=1,
                    target_version=2,
                )
            ],
            summary=ChangesSummary(
                total_changes=1,
                adds=0,
                removes=0,
                renames=1,
                system_changes=0,
                user_changes=1,
            ),
        )

        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
            change_tracking=change_tracking,
        )

        assert combined_results.validation_results == validation_results
        assert combined_results.schema_alignment_results == schema_alignment_results
        assert combined_results.change_tracking == change_tracking
        assert combined_results.has_validation_results()
        assert combined_results.has_schema_alignment_results()
        assert combined_results.has_change_tracking()

    def test_has_change_tracking_with_none(self):
        """Test has_change_tracking with None change tracking."""
        combined_results = CombinedResults(change_tracking=None)
        assert not combined_results.has_change_tracking()

    def test_has_change_tracking_with_valid_results(self):
        """Test has_change_tracking with valid change tracking results."""
        change_tracking = ChangeTrackingResults(
            changes=[],
            summary=ChangesSummary(
                total_changes=0,
                adds=0,
                removes=0,
                renames=0,
                system_changes=0,
                user_changes=0,
            ),
        )
        combined_results = CombinedResults(change_tracking=change_tracking)
        assert combined_results.has_change_tracking()

    def test_to_dict_with_change_tracking_only(self):
        """Test to_dict with change tracking only."""
        change_tracking = ChangeTrackingResults(
            changes=[
                ChangeObject(
                    change_type="remove",
                    source_type="system",
                    component="schema_alignment",
                    column="removed_col",
                    old_value="removed_column",
                    source_version=1,
                    target_version=2,
                )
            ],
            summary=ChangesSummary(
                total_changes=1,
                adds=0,
                removes=1,
                renames=0,
                system_changes=1,
                user_changes=0,
            ),
        )

        combined_results = CombinedResults(change_tracking=change_tracking)
        result_dict = combined_results.to_dict()

        assert "change_tracking" in result_dict
        assert "validation_results" not in result_dict
        assert "schema_alignment_results" not in result_dict
        assert result_dict["change_tracking"]["summary"]["total_changes"] == 1
        assert result_dict["change_tracking"]["summary"]["removes"] == 1

    def test_to_dict_with_all_results_including_change_tracking(self):
        """Test to_dict with all result types including change tracking."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=2, total_errors=0, columns_validated=0, error_types={}),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="new_col1,new_col2\nval1,val2",
                columns_renamed=2,
                rows_original=1,
                rows_aligned=1,
            ),
        )

        change_tracking = ChangeTrackingResults(
            changes=[
                ChangeObject(
                    change_type="add",
                    source_type="user",
                    component="validation",
                    row=3,
                    column="col_c",
                    new_value="added_value",
                    source_version=1,
                    target_version=2,
                )
            ],
            summary=ChangesSummary(
                total_changes=1,
                adds=1,
                removes=0,
                renames=0,
                system_changes=0,
                user_changes=1,
            ),
        )

        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
            change_tracking=change_tracking,
        )
        result_dict = combined_results.to_dict()

        assert "validation_results" in result_dict
        assert "schema_alignment_results" in result_dict
        assert "change_tracking" in result_dict
        assert result_dict["validation_results"]["summary"]["total_errors"] == 0
        assert result_dict["schema_alignment_results"]["summary"]["columns_renamed"] == 2
        assert result_dict["change_tracking"]["summary"]["total_changes"] == 1
        assert result_dict["change_tracking"]["summary"]["adds"] == 1

    def test_from_dict_with_change_tracking_only(self):
        """Test from_dict with change tracking only."""
        data = {
            "change_tracking": {
                "changes": [
                    {
                        "change_id": "chg_12345678",
                        "change_type": "rename",
                        "source_type": "user",
                        "component": "validation",
                        "row": 1,
                        "column": "col_a",
                        "old_value": "old_name",
                        "new_value": "new_name",
                        "timestamp": "2025-09-30T12:00:00+00:00",
                        "source_version": 1,
                        "target_version": 2,
                    }
                ],
                "summary": {
                    "total_changes": 1,
                    "adds": 0,
                    "removes": 0,
                    "renames": 1,
                    "system_changes": 0,
                    "user_changes": 1,
                },
                "comparison_metadata": {"detection_timestamp": "2025-09-30T12:00:00+00:00"},
            }
        }

        combined_results = CombinedResults.from_dict(data)

        assert not combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()
        assert combined_results.has_change_tracking()
        assert combined_results.change_tracking.summary.total_changes == 1
        assert combined_results.change_tracking.summary.renames == 1
        assert len(combined_results.change_tracking.changes) == 1
        assert combined_results.change_tracking.changes[0].change_type == "rename"

    def test_from_dict_with_all_results_including_change_tracking(self):
        """Test from_dict with all result types including change tracking."""
        data = {
            "validation_results": {
                "validationResults": [],
                "summary": {
                    "totalRows": 2,
                    "totalErrors": 0,
                    "columnsValidated": 0,
                    "errorTypes": {},
                },
            },
            "schema_alignment_results": {
                "schema_alignment_results": [],
                "summary": {
                    "job_id": "test-job",
                    "version": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "original_data_csv": "col1,col2\nval1,val2",
                    "aligned_data_csv": "new_col1,new_col2\nval1,val2",
                    "columns_renamed": 2,
                    "rows_original": 1,
                    "rows_aligned": 1,
                },
            },
            "change_tracking": {
                "changes": [
                    {
                        "change_id": "chg_87654321",
                        "change_type": "add",
                        "source_type": "system",
                        "component": "schema_alignment",
                        "column": "new_column",
                        "new_value": "system_added",
                        "timestamp": "2025-09-30T12:00:00+00:00",
                        "source_version": 1,
                        "target_version": 2,
                        "confidence_score": 0.95,
                    }
                ],
                "summary": {
                    "total_changes": 1,
                    "adds": 1,
                    "removes": 0,
                    "renames": 0,
                    "system_changes": 1,
                    "user_changes": 0,
                },
                "comparison_metadata": {"detection_timestamp": "2025-09-30T12:00:00+00:00"},
            },
        }

        combined_results = CombinedResults.from_dict(data)

        assert combined_results.has_validation_results()
        assert combined_results.has_schema_alignment_results()
        assert combined_results.has_change_tracking()
        assert combined_results.validation_results.summary.total_errors == 0
        assert combined_results.schema_alignment_results.summary.columns_renamed == 2
        assert combined_results.change_tracking.summary.total_changes == 1
        assert combined_results.change_tracking.summary.system_changes == 1
        assert combined_results.change_tracking.changes[0].confidence_score == 0.95

    def test_round_trip_serialization_with_change_tracking(self):
        """Test round-trip serialization with change tracking included."""
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="test_column",
                    current_value="invalid",
                    error_type=ValidationErrorType.INVALID_PATTERN,
                    recommended_value="valid_pattern",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=5,
                total_errors=1,
                columns_validated=1,
                error_types={ValidationErrorType.INVALID_PATTERN: 1},
            ),
        )

        change_tracking = ChangeTrackingResults(
            changes=[
                ChangeObject(
                    change_type="rename",
                    source_type="user",
                    component="validation",
                    row=1,
                    column="col_a",
                    old_value="old_value",
                    new_value="new_value",
                    source_version=1,
                    target_version=2,
                ),
                ChangeObject(
                    change_type="add",
                    source_type="system",
                    component="schema_alignment",
                    column="new_field",
                    new_value="system_value",
                    source_version=1,
                    target_version=2,
                    confidence_score=0.85,
                ),
            ],
            summary=ChangesSummary(
                total_changes=2,
                adds=1,
                removes=0,
                renames=1,
                system_changes=1,
                user_changes=1,
            ),
            comparison_metadata={
                "detection_timestamp": "2025-09-30T12:00:00+00:00",
                "compared_versions": [1, 2],
            },
        )

        original = CombinedResults(validation_results=validation_results, change_tracking=change_tracking)

        # Serialize to dict
        data = original.to_dict()

        # Deserialize from dict
        reconstructed = CombinedResults.from_dict(data)

        # Verify equality
        assert reconstructed.has_validation_results() == original.has_validation_results()
        assert reconstructed.has_schema_alignment_results() == original.has_schema_alignment_results()
        assert reconstructed.has_change_tracking() == original.has_change_tracking()

        # Verify validation results
        assert reconstructed.validation_results.summary.total_errors == original.validation_results.summary.total_errors
        assert len(reconstructed.validation_results.validation_results) == len(
            original.validation_results.validation_results
        )

        # Verify change tracking results
        assert reconstructed.change_tracking.summary.total_changes == original.change_tracking.summary.total_changes
        assert reconstructed.change_tracking.summary.adds == original.change_tracking.summary.adds
        assert reconstructed.change_tracking.summary.renames == original.change_tracking.summary.renames
        assert reconstructed.change_tracking.summary.system_changes == original.change_tracking.summary.system_changes
        assert reconstructed.change_tracking.summary.user_changes == original.change_tracking.summary.user_changes
        assert len(reconstructed.change_tracking.changes) == len(original.change_tracking.changes)

        # Verify individual changes
        for orig_change, recon_change in zip(original.change_tracking.changes, reconstructed.change_tracking.changes):
            assert recon_change.change_type == orig_change.change_type
            assert recon_change.source_type == orig_change.source_type
            assert recon_change.component == orig_change.component
            assert recon_change.old_value == orig_change.old_value
            assert recon_change.new_value == orig_change.new_value
            assert recon_change.confidence_score == orig_change.confidence_score

    def test_partial_change_tracking_data_handling(self):
        """Test handling of partial or missing change tracking data in from_dict."""
        # Test with null change_tracking
        data_with_null_change_tracking = {
            "validation_results": {
                "validationResults": [],
                "summary": {
                    "totalRows": 3,
                    "totalErrors": 0,
                    "columnsValidated": 0,
                    "errorTypes": {},
                },
            },
            "change_tracking": None,
        }

        combined_results = CombinedResults.from_dict(data_with_null_change_tracking)

        assert combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()
        assert not combined_results.has_change_tracking()
        assert combined_results.validation_results.summary.total_rows == 3

        # Test with missing change_tracking key
        data_missing_change_tracking = {
            "validation_results": {
                "validationResults": [],
                "summary": {
                    "totalRows": 5,
                    "totalErrors": 0,
                    "columnsValidated": 0,
                    "errorTypes": {},
                },
            }
        }

        combined_results = CombinedResults.from_dict(data_missing_change_tracking)

        assert combined_results.has_validation_results()
        assert not combined_results.has_schema_alignment_results()
        assert not combined_results.has_change_tracking()
        assert combined_results.validation_results.summary.total_rows == 5
