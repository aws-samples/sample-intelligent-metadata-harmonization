# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for ChangeDetectionService.

This module contains comprehensive unit tests for the ChangeDetectionService
class, covering initialization, change detection logic, error handling,
and integration with the ResultSaver interface.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from metadata_harmonization_api.services.change_detection_service import ChangeDetectionService
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.validation import (
    ValidationResults,
    ValidationResultsSummary,
    ValidationErrorDetail,
    ValidationErrorType,
)
from metadata_harmonization_processor.models.schema_alignment_results import SchemaAlignmentResults
from metadata_harmonization_processor.models.job import JobResults
from metadata_harmonization_processor.interfaces.result_saver import ResultSaver


class TestChangeDetectionService:
    """Test cases for ChangeDetectionService."""

    @pytest.fixture
    def service(self):
        """Create a ChangeDetectionService instance for testing."""
        return ChangeDetectionService()

    @pytest.fixture
    def mock_result_saver(self):
        """Create a mock ResultSaver for testing."""
        return AsyncMock(spec=ResultSaver)

    @pytest.fixture
    def sample_validation_results(self):
        """Create sample ValidationResults for testing."""
        return ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 2}, columns_validated=1
            ),
            validation_results=[
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=1,
                    column="test_column",
                    current_value="",
                    recommended_value="test_value",
                )
            ],
        )

    @pytest.fixture
    def sample_schema_alignment_results(self):
        """Create sample SchemaAlignmentResults for testing."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
            SchemaAlignmentChangeDetail,
        )

        summary = SchemaAlignmentResultsSummary(
            job_id="test_job_123",
            version=1,
            original_data_csv="original,data\nrow1,value1",
            aligned_data_csv="aligned,data\nrow1,value1",
            total_changes=2,
            columns_renamed=2,
            columns_added=0,
            columns_removed=0,
            rows_original=1,
            rows_aligned=1,
        )

        changes = [
            SchemaAlignmentChangeDetail(
                change_type="rename", original_column="source_col1", new_column="target_col1", reason="Schema alignment"
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename", original_column="source_col2", new_column="target_col2", reason="Schema alignment"
            ),
        ]

        return SchemaAlignmentResults(schema_alignment_results=changes, summary=summary)

    @pytest.fixture
    def sample_combined_results(self, sample_validation_results, sample_schema_alignment_results):
        """Create sample CombinedResults for testing."""
        return CombinedResults(
            validation_results=sample_validation_results, schema_alignment_results=sample_schema_alignment_results
        )

    @pytest.fixture
    def sample_job_results(self):
        """Create sample JobResults for testing."""
        return [
            JobResults(storage_type="local", location="test_job_123/v1/results.json"),
            JobResults(storage_type="local", location="test_job_123/v2/results.json"),
        ]

    def test_service_initialization(self, service):
        """Test that ChangeDetectionService initializes correctly."""
        assert service is not None
        assert hasattr(service, "logger")
        assert service.logger.name.endswith("ChangeDetectionService")

    @pytest.mark.asyncio
    async def test_detect_changes_no_previous_versions(self, service, mock_result_saver, sample_combined_results):
        """Test change detection when no previous versions exist."""
        # Setup
        job_id = "test_job_123"
        current_version = 1

        # Mock no previous results
        mock_result_saver.list_results.return_value = []

        # Execute
        changes = await service.detect_changes(
            job_id=job_id,
            current_version=current_version,
            current_results=sample_combined_results,
            result_saver=mock_result_saver,
        )

        # Verify
        assert changes == []
        mock_result_saver.list_results.assert_called_once_with(job_id)

    @pytest.mark.asyncio
    async def test_detect_changes_with_previous_version(
        self, service, mock_result_saver, sample_combined_results, sample_job_results
    ):
        """Test change detection with previous versions available."""
        # Setup
        job_id = "test_job_123"
        current_version = 3

        # Create modified validation results for comparison
        previous_validation = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1,  # Different from current (2)
                total_rows=100,
                error_types={ValidationErrorType.REQUIRED_VALUE: 1},
                columns_validated=1,
            ),
            validation_results=[],
        )

        previous_combined = CombinedResults(
            validation_results=previous_validation,
            schema_alignment_results=sample_combined_results.schema_alignment_results,
        )

        # Mock result saver responses
        mock_result_saver.list_results.return_value = sample_job_results
        mock_result_saver.get_results.return_value = previous_combined

        # Execute
        changes = await service.detect_changes(
            job_id=job_id,
            current_version=current_version,
            current_results=sample_combined_results,
            result_saver=mock_result_saver,
        )

        # Verify
        assert len(changes) > 0
        assert any(change.column == "summary.total_errors" for change in changes)
        mock_result_saver.list_results.assert_called_once_with(job_id)
        mock_result_saver.get_results.assert_called()

    @pytest.mark.asyncio
    async def test_load_previous_versions_success(
        self, service, mock_result_saver, sample_job_results, sample_combined_results
    ):
        """Test successful loading of previous versions."""
        # Setup
        job_id = "test_job_123"
        current_version = 3

        mock_result_saver.list_results.return_value = sample_job_results
        mock_result_saver.get_results.return_value = sample_combined_results

        # Execute
        previous_versions = await service._load_previous_versions(
            job_id=job_id, current_version=current_version, result_saver=mock_result_saver
        )

        # Verify
        assert len(previous_versions) == 2  # Both versions 1 and 2 should be loaded
        assert 1 in previous_versions
        assert 2 in previous_versions
        assert all(isinstance(result, CombinedResults) for result in previous_versions.values())

    @pytest.mark.asyncio
    async def test_load_previous_versions_with_corrupted_version(
        self, service, mock_result_saver, sample_job_results, sample_combined_results
    ):
        """Test loading previous versions when one version is corrupted."""
        # Setup
        job_id = "test_job_123"
        current_version = 3

        mock_result_saver.list_results.return_value = sample_job_results

        # Mock get_results to fail for version 1 but succeed for version 2
        def mock_get_results(job_result):
            # Extract version from location to determine which should fail
            if "v1" in job_result.location:
                raise Exception("Corrupted data")
            return sample_combined_results

        mock_result_saver.get_results.side_effect = mock_get_results

        # Execute
        previous_versions = await service._load_previous_versions(
            job_id=job_id, current_version=current_version, result_saver=mock_result_saver
        )

        # Verify - should only have version 2, version 1 should be skipped
        assert len(previous_versions) == 1
        assert 2 in previous_versions
        assert 1 not in previous_versions

    @pytest.mark.asyncio
    async def test_load_previous_versions_no_results(self, service, mock_result_saver):
        """Test loading previous versions when no results exist."""
        # Setup
        job_id = "test_job_123"
        current_version = 1

        mock_result_saver.list_results.return_value = []

        # Execute
        previous_versions = await service._load_previous_versions(
            job_id=job_id, current_version=current_version, result_saver=mock_result_saver
        )

        # Verify
        assert previous_versions == {}

    @pytest.mark.asyncio
    async def test_compare_validation_results_no_changes(self, service):
        """Test validation results comparison when no changes exist."""
        # Setup - identical validation results
        validation_results = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 2}, columns_validated=2
            ),
            validation_results=[],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=validation_results, current=validation_results, source_version=1, target_version=2
        )

        # Verify
        assert changes == []

    @pytest.mark.asyncio
    async def test_compare_validation_results_with_changes(self, service):
        """Test validation results comparison when changes exist."""
        # Setup - different validation results
        previous = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=2
            ),
            validation_results=[],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 2}, columns_validated=2
            ),
            validation_results=[],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify
        assert len(changes) == 2  # total_errors and error_types changes

        # Find the total_errors change
        error_change = next(c for c in changes if c.column == "summary.total_errors")
        assert error_change.change_type == "rename"
        assert error_change.old_value == 1
        assert error_change.new_value == 2
        assert error_change.source_version == 1
        assert error_change.target_version == 2

        # Find the error_types change
        error_type_change = next(c for c in changes if c.column == "summary.error_types.REQUIRED_VALUE")
        assert error_type_change.change_type == "rename"
        assert error_type_change.old_value == 1
        assert error_type_change.new_value == 2

    @pytest.mark.asyncio
    async def test_compare_schema_alignment_results_no_changes(self, service):
        """Test schema alignment results comparison when no changes exist."""
        # Setup - identical schema alignment results
        from metadata_harmonization_processor.models.schema_alignment_results import SchemaAlignmentResultsSummary

        summary = SchemaAlignmentResultsSummary(
            job_id="test_job_123",
            version=1,
            original_data_csv="col1\nvalue1",
            aligned_data_csv="mapped_col1\nvalue1",
            total_changes=1,
            columns_renamed=1,
        )

        schema_results = SchemaAlignmentResults(schema_alignment_results=[], summary=summary)

        # Execute
        changes = await service.compare_schema_alignment_results(
            previous=schema_results, current=schema_results, source_version=1, target_version=2
        )

        # Verify
        assert changes == []

    @pytest.mark.asyncio
    async def test_compare_schema_alignment_results_with_changes(self, service):
        """Test schema alignment results comparison when changes exist."""
        # Setup - different schema alignment results
        from metadata_harmonization_processor.models.schema_alignment_results import SchemaAlignmentResultsSummary

        previous_summary = SchemaAlignmentResultsSummary(
            job_id="test_job_123",
            version=1,
            original_data_csv="col1\nvalue1",
            aligned_data_csv="mapped_col1\nvalue1",
            total_changes=1,
            columns_renamed=1,
        )

        current_summary = SchemaAlignmentResultsSummary(
            job_id="test_job_123",
            version=2,
            original_data_csv="col1,col2\nvalue1,value2",
            aligned_data_csv="mapped_col1,mapped_col2\nvalue1,value2",
            total_changes=2,
            columns_renamed=2,
        )

        previous = SchemaAlignmentResults(schema_alignment_results=[], summary=previous_summary)

        current = SchemaAlignmentResults(schema_alignment_results=[], summary=current_summary)

        # Execute
        changes = await service.compare_schema_alignment_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify
        assert len(changes) == 2  # total_changes and columns_renamed

        total_changes_change = next(c for c in changes if c.column == "summary.total_changes")
        assert total_changes_change.change_type == "rename"
        assert total_changes_change.old_value == 1
        assert total_changes_change.new_value == 2
        assert total_changes_change.source_version == 1
        assert total_changes_change.target_version == 2

        columns_renamed_change = next(c for c in changes if c.column == "summary.columns_renamed")
        assert columns_renamed_change.change_type == "rename"
        assert columns_renamed_change.old_value == 1
        assert columns_renamed_change.new_value == 2

    @pytest.mark.asyncio
    async def test_detect_changes_error_handling(self, service, mock_result_saver, sample_combined_results):
        """Test error handling in change detection."""
        # Setup
        job_id = "test_job_123"
        current_version = 2

        # Mock result saver to raise exception
        mock_result_saver.list_results.side_effect = Exception("Database error")

        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Database error"):
            await service.detect_changes(
                job_id=job_id,
                current_version=current_version,
                current_results=sample_combined_results,
                result_saver=mock_result_saver,
            )

    @pytest.mark.asyncio
    async def test_detect_changes_partial_results(self, service, mock_result_saver, sample_combined_results):
        """Test change detection with partial results (only validation or only schema alignment)."""
        # Setup - current results with only validation
        current_results = CombinedResults(
            validation_results=sample_combined_results.validation_results, schema_alignment_results=None
        )

        # Previous results with only validation
        previous_validation = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1,  # Different from current
                total_rows=100,
                error_types={ValidationErrorType.REQUIRED_VALUE: 1},
                columns_validated=1,
            ),
            validation_results=[],
        )

        previous_results = CombinedResults(validation_results=previous_validation, schema_alignment_results=None)

        job_results = [JobResults(storage_type="local", location="test_job_123/v1/results.json")]

        mock_result_saver.list_results.return_value = job_results
        mock_result_saver.get_results.return_value = previous_results

        # Execute
        changes = await service.detect_changes(
            job_id="test_job_123", current_version=2, current_results=current_results, result_saver=mock_result_saver
        )

        # Verify - should have changes
        # Note: Summary changes use schema_alignment component, cell changes use validation
        assert len(changes) > 0

    @pytest.mark.asyncio
    async def test_change_object_properties(self, service):
        """Test that generated change objects have correct properties."""
        # Setup
        previous = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=2
            ),
            validation_results=[],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 2}, columns_validated=2
            ),
            validation_results=[],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify change object properties - should have 2 changes (total_errors and error_types)
        assert len(changes) == 2

        # Find the total_errors change
        total_errors_change = next(c for c in changes if c.column == "summary.total_errors")

        assert total_errors_change.change_type == "rename"
        assert total_errors_change.source_type == "system"
        assert total_errors_change.component == "schema_alignment"  # Summary changes use schema_alignment
        assert total_errors_change.column == "summary.total_errors"
        assert total_errors_change.old_value == 1
        assert total_errors_change.new_value == 2
        assert total_errors_change.source_version == 1
        assert total_errors_change.target_version == 2
        assert total_errors_change.timestamp is not None
        assert total_errors_change.change_id is not None

        # Verify timestamp is valid ISO format
        datetime.fromisoformat(total_errors_change.timestamp.replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_compare_validation_results_cell_level_add_error(self, service):
        """Test cell-level comparison when new validation errors are added."""
        # Setup - previous has no errors, current has one error
        previous = ValidationResults(
            summary=ValidationResultsSummary(total_errors=0, total_rows=100, error_types={}, columns_validated=1),
            validation_results=[],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
            validation_results=[
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=1,
                    column="test_column",
                    current_value="",
                    recommended_value="test_value",
                    confidence_score=0.8,
                )
            ],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify - should have summary changes and one cell-level add
        assert len(changes) >= 3  # total_errors, error_types, and cell add

        # Find the cell-level add change
        cell_changes = [c for c in changes if c.column == "test_column" and c.row == 1]
        assert len(cell_changes) == 1

        cell_change = cell_changes[0]
        assert cell_change.change_type == "add"
        assert cell_change.source_type == "system"  # High confidence score
        assert cell_change.component == "validation"
        assert cell_change.row == 1
        assert cell_change.column == "test_column"
        assert cell_change.old_value is None
        assert cell_change.new_value == ""
        assert cell_change.confidence_score == 0.8

    @pytest.mark.asyncio
    async def test_compare_validation_results_cell_level_remove_error(self, service):
        """Test cell-level comparison when validation errors are removed (fixed)."""
        # Setup - previous has error, current has no errors
        previous = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
            validation_results=[
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=2,
                    column="fixed_column",
                    current_value="invalid",
                    recommended_value="valid_value",
                    confidence_score=0.9,
                )
            ],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(total_errors=0, total_rows=100, error_types={}, columns_validated=1),
            validation_results=[],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify - should have summary changes and one cell-level remove
        assert len(changes) >= 3  # total_errors, error_types, and cell remove

        # Find the cell-level remove change
        cell_changes = [c for c in changes if c.column == "fixed_column" and c.row == 2]
        assert len(cell_changes) == 1

        cell_change = cell_changes[0]
        assert cell_change.change_type == "remove"
        assert cell_change.source_type == "system"  # High confidence score
        assert cell_change.component == "validation"
        assert cell_change.row == 2
        assert cell_change.column == "fixed_column"
        assert cell_change.new_value is None
        assert cell_change.old_value == "invalid"
        assert cell_change.confidence_score == 0.9

    @pytest.mark.asyncio
    async def test_compare_validation_results_cell_level_modify_error(self, service):
        """Test cell-level comparison when validation error details are modified."""
        # Setup - same cell has different error details
        previous = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
            validation_results=[
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=3,
                    column="modified_column",
                    current_value="old_value",
                    recommended_value="old_recommendation",
                    confidence_score=0.6,
                )
            ],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=1
            ),
            validation_results=[
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=3,
                    column="modified_column",
                    current_value="new_value",
                    recommended_value="new_recommendation",
                    confidence_score=0.8,
                )
            ],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify - should have changes for current_value
        cell_changes = [c for c in changes if c.column == "modified_column" and c.row == 3]
        # Note: The service creates a single change object with old_value and new_value
        # representing the current_value changes
        assert len(cell_changes) >= 1

        # Check current_value change
        current_value_change = next(c for c in cell_changes if c.change_type == "rename")
        assert current_value_change.source_type == "user"  # Value changes are user-driven
        assert current_value_change.row == 3
        assert current_value_change.column == "modified_column"
        assert current_value_change.old_value == "old_value"
        assert current_value_change.new_value == "new_value"

    @pytest.mark.asyncio
    async def test_compare_validation_results_error_type_changes(self, service):
        """Test comparison of error type changes in summary."""
        # Setup - different error type distributions
        previous = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2,
                total_rows=100,
                error_types={ValidationErrorType.REQUIRED_VALUE: 2, ValidationErrorType.INVALID_OPTION: 0},
                columns_validated=2,
            ),
            validation_results=[],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2,
                total_rows=100,
                error_types={ValidationErrorType.REQUIRED_VALUE: 1, ValidationErrorType.INVALID_OPTION: 1},
                columns_validated=2,
            ),
            validation_results=[],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify - should have changes for both error types
        error_type_changes = [c for c in changes if "error_types" in c.column]
        assert len(error_type_changes) == 2

        # Check REQUIRED_VALUE change
        required_value_change = next(c for c in error_type_changes if "REQUIRED_VALUE" in c.column)
        assert required_value_change.change_type == "rename"
        assert required_value_change.old_value == 2
        assert required_value_change.new_value == 1

        # Check INVALID_OPTION change
        invalid_option_change = next(c for c in error_type_changes if "INVALID_OPTION" in c.column)
        assert invalid_option_change.change_type == "rename"
        assert invalid_option_change.old_value == 0
        assert invalid_option_change.new_value == 1

    @pytest.mark.asyncio
    async def test_compare_validation_results_removed_error_type(self, service):
        """Test comparison when an error type is completely removed."""
        # Setup - previous has error type, current doesn't
        previous = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1,
                total_rows=100,
                error_types={ValidationErrorType.REQUIRED_VALUE: 1, ValidationErrorType.INVALID_PATTERN: 1},
                columns_validated=2,
            ),
            validation_results=[],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=1, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 1}, columns_validated=2
            ),
            validation_results=[],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify - should have a remove change for INVALID_PATTERN
        removed_changes = [c for c in changes if c.change_type == "remove"]
        assert len(removed_changes) == 1

        removed_change = removed_changes[0]
        assert "INVALID_PATTERN" in removed_change.column
        assert removed_change.old_value == 1
        assert removed_change.new_value is None

    @pytest.mark.asyncio
    async def test_compare_validation_results_multiple_cells_complex_scenario(self, service):
        """Test complex scenario with multiple cell changes of different types."""
        # Setup - complex scenario with adds, removes, and modifications
        previous = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2, total_rows=100, error_types={ValidationErrorType.REQUIRED_VALUE: 2}, columns_validated=3
            ),
            validation_results=[
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=1,
                    column="col1",
                    current_value="",
                    recommended_value="value1",
                    confidence_score=0.7,
                ),
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=2,
                    column="col2",
                    current_value="old",
                    recommended_value="old_rec",
                    confidence_score=0.5,
                ),
            ],
        )

        current = ValidationResults(
            summary=ValidationResultsSummary(
                total_errors=2,
                total_rows=100,
                error_types={ValidationErrorType.REQUIRED_VALUE: 1, ValidationErrorType.INVALID_OPTION: 1},
                columns_validated=3,
            ),
            validation_results=[
                ValidationErrorDetail(
                    error_type=ValidationErrorType.REQUIRED_VALUE,
                    row=2,
                    column="col2",
                    current_value="new",
                    recommended_value="new_rec",
                    confidence_score=0.9,
                ),
                ValidationErrorDetail(
                    error_type=ValidationErrorType.INVALID_OPTION,
                    row=3,
                    column="col3",
                    current_value="invalid",
                    recommended_value="valid",
                    confidence_score=0.8,
                ),
            ],
        )

        # Execute
        changes = await service.compare_validation_results(
            previous=previous, current=current, source_version=1, target_version=2
        )

        # Verify complex changes
        # Should have: summary changes + cell remove (1:col1) + cell modifications (2:col2) + cell add (3:col3)
        assert len(changes) > 5

        # Check cell removal (1:col1)
        removed_cells = [c for c in changes if c.change_type == "remove" and c.column == "col1" and c.row == 1]
        assert len(removed_cells) == 1

        # Check cell addition (3:col3)
        added_cells = [c for c in changes if c.change_type == "add" and c.column == "col3" and c.row == 3]
        assert len(added_cells) == 1

        # Check cell modifications (2:col2)
        modified_cells = [c for c in changes if c.column == "col2" and c.row == 2 and c.change_type == "rename"]
        assert len(modified_cells) == 3  # current_value, recommended_value, confidence_score

    def test_create_error_coordinate_map(self, service):
        """Test creation of error coordinate mapping."""
        # Setup
        errors = [
            ValidationErrorDetail(
                error_type=ValidationErrorType.REQUIRED_VALUE,
                row=1,
                column="col1",
                current_value="",
                recommended_value="value1",
            ),
            ValidationErrorDetail(
                error_type=ValidationErrorType.INVALID_OPTION,
                row=2,
                column="col2",
                current_value="invalid",
                recommended_value="valid",
            ),
        ]

        # Execute
        error_map = service._create_error_coordinate_map(errors)

        # Verify
        assert len(error_map) == 2
        assert "1:col1" in error_map
        assert "2:col2" in error_map
        assert error_map["1:col1"].current_value == ""
        assert error_map["2:col2"].current_value == "invalid"

    def test_extract_version_from_location(self, service):
        """Test version extraction from location paths."""
        # Test valid version paths
        assert service._extract_version_from_location("job_123/v1/results.json") == 1
        assert service._extract_version_from_location("job_123/v10/results.json") == 10
        assert service._extract_version_from_location("some/path/v5/file.json") == 5

        # Test invalid paths
        assert service._extract_version_from_location("job_123/results.json") is None
        assert service._extract_version_from_location("job_123/version1/results.json") is None
        assert service._extract_version_from_location("") is None
        assert service._extract_version_from_location("invalid") is None
