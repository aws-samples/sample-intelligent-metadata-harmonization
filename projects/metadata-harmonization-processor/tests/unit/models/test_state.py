# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for ProcessorState model.

Tests cover model initialization, validation, serialization, and utility methods
for managing processing state between AWS Strands nodes.
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from pydantic import ValidationError

from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentResults,
)
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class TestProcessorStateInitialization:
    """Test ProcessorState model initialization and basic functionality."""

    def test_empty_initialization(self):
        """Test creating ProcessorState with default values."""
        state = ProcessorState()

        assert state.metadata_df is None
        assert state.program_id is None
        assert state.core_id is None
        assert state.aligned_df is None
        assert state.schema_definition is None
        assert state.combined_results is None
        assert state.job_id == ""
        assert state.current_stage == ""
        assert state.processing_start_time is None

    def test_initialization_with_basic_fields(self):
        """Test creating ProcessorState with basic string fields."""
        job_id = "test-job-123"
        program_id = "test-program"
        core_id = "test-core"
        current_stage = "validation"

        state = ProcessorState(
            job_id=job_id,
            program_id=program_id,
            core_id=core_id,
            current_stage=current_stage,
        )

        assert state.job_id == job_id
        assert state.program_id == program_id
        assert state.core_id == core_id
        assert state.current_stage == current_stage

    def test_initialization_with_datetime(self):
        """Test creating ProcessorState with datetime field."""
        start_time = datetime.now()

        state = ProcessorState(processing_start_time=start_time)

        assert state.processing_start_time == start_time

    def test_initialization_with_dataframe(self):
        """Test creating ProcessorState with pandas DataFrame."""
        df = pd.DataFrame({"column1": ["value1", "value2"], "column2": [1, 2]})

        state = ProcessorState(metadata_df=df)

        assert state.metadata_df is not None
        pd.testing.assert_frame_equal(state.metadata_df, df)

    def test_initialization_with_schema_definition(self):
        """Test creating ProcessorState with schema definition."""
        schema_def = {
            "columns": {
                "column1": {"type": "string", "required": True},
                "column2": {"type": "integer", "required": False},
            }
        }

        state = ProcessorState(schema_definition=schema_def)

        assert state.schema_definition == schema_def

    def test_initialization_with_combined_results(self):
        """Test creating ProcessorState with CombinedResults."""
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
                error_types={ValidationErrorType.INVALID_OPTION: 1},
                columns_validated=1,
            ),
        )

        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(combined_results=combined_results)

        assert state.combined_results == combined_results
        assert state.has_validation_results()
        assert not state.has_schema_alignment_results()


class TestProcessorStateUtilityMethods:
    """Test ProcessorState utility methods for checking state."""

    def test_set_current_stage(self):
        """Test setting current stage."""
        state = ProcessorState()

        state.set_current_stage("schema_alignment")
        assert state.current_stage == "schema_alignment"

        state.set_current_stage("validation")
        assert state.current_stage == "validation"

    def test_has_metadata_with_empty_state(self):
        """Test has_metadata with empty state."""
        state = ProcessorState()
        assert not state.has_metadata()

    def test_has_metadata_with_none_dataframe(self):
        """Test has_metadata with None DataFrame."""
        state = ProcessorState(metadata_df=None)
        assert not state.has_metadata()

    def test_has_metadata_with_empty_dataframe(self):
        """Test has_metadata with empty DataFrame."""
        empty_df = pd.DataFrame()
        state = ProcessorState(metadata_df=empty_df)
        assert not state.has_metadata()

    def test_has_metadata_with_valid_dataframe(self):
        """Test has_metadata with valid DataFrame."""
        df = pd.DataFrame({"column1": ["value1"]})
        state = ProcessorState(metadata_df=df)
        assert state.has_metadata()

    def test_has_schema_ids_with_empty_state(self):
        """Test has_schema_ids with empty state."""
        state = ProcessorState()
        assert not state.has_schema_ids()

    def test_has_schema_ids_with_only_program_id(self):
        """Test has_schema_ids with only program_id set."""
        state = ProcessorState(program_id="test-program")
        assert not state.has_schema_ids()

    def test_has_schema_ids_with_only_core_id(self):
        """Test has_schema_ids with only core_id set."""
        state = ProcessorState(core_id="test-core")
        assert not state.has_schema_ids()

    def test_has_schema_ids_with_both_ids(self):
        """Test has_schema_ids with both IDs set."""
        state = ProcessorState(program_id="test-program", core_id="test-core")
        assert state.has_schema_ids()

    def test_has_aligned_data_with_empty_state(self):
        """Test has_aligned_data with empty state."""
        state = ProcessorState()
        assert not state.has_aligned_data()

    def test_has_aligned_data_with_none_dataframe(self):
        """Test has_aligned_data with None DataFrame."""
        state = ProcessorState(aligned_df=None)
        assert not state.has_aligned_data()

    def test_has_aligned_data_with_empty_dataframe(self):
        """Test has_aligned_data with empty DataFrame."""
        empty_df = pd.DataFrame()
        state = ProcessorState(aligned_df=empty_df)
        assert not state.has_aligned_data()

    def test_has_aligned_data_with_valid_dataframe(self):
        """Test has_aligned_data with valid DataFrame."""
        df = pd.DataFrame({"column1": ["value1"]})
        state = ProcessorState(aligned_df=df)
        assert state.has_aligned_data()

    def test_has_validation_results_with_empty_state(self):
        """Test has_validation_results with empty state."""
        state = ProcessorState()
        assert not state.has_validation_results()

    def test_has_validation_results_with_none_combined_results(self):
        """Test has_validation_results with None combined_results."""
        state = ProcessorState(combined_results=None)
        assert not state.has_validation_results()

    def test_has_validation_results_with_valid_results(self):
        """Test has_validation_results with valid results."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=0, total_errors=0, error_types={}, columns_validated=0),
        )
        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(combined_results=combined_results)
        assert state.has_validation_results()

    def test_has_schema_alignment_results_with_empty_state(self):
        """Test has_schema_alignment_results with empty state."""
        state = ProcessorState()
        assert not state.has_schema_alignment_results()

    def test_has_schema_alignment_results_with_none_combined_results(self):
        """Test has_schema_alignment_results with None combined_results."""
        state = ProcessorState(combined_results=None)
        assert not state.has_schema_alignment_results()

    def test_has_schema_alignment_results_with_valid_results(self):
        """Test has_schema_alignment_results with valid results."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
            ),
        )
        combined_results = CombinedResults(schema_alignment_results=schema_alignment_results)
        state = ProcessorState(combined_results=combined_results)
        assert state.has_schema_alignment_results()

    def test_get_combined_results_with_empty_state(self):
        """Test get_combined_results with empty state."""
        state = ProcessorState()
        combined_results = state.get_combined_results()
        assert combined_results is None

    def test_get_combined_results_with_validation_only(self):
        """Test get_combined_results with validation results only."""
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=0, total_errors=0, error_types={}, columns_validated=0),
        )
        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(combined_results=combined_results)

        result = state.get_combined_results()
        assert result == combined_results
        assert result.has_validation_results()
        assert not result.has_schema_alignment_results()

    def test_get_combined_results_with_schema_alignment_only(self):
        """Test get_combined_results with schema alignment results only."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
            ),
        )
        combined_results = CombinedResults(schema_alignment_results=schema_alignment_results)
        state = ProcessorState(combined_results=combined_results)

        result = state.get_combined_results()
        assert result == combined_results
        assert not result.has_validation_results()
        assert result.has_schema_alignment_results()

    def test_get_combined_results_with_both_results(self):
        """Test get_combined_results with both result types."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
        )

        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=0, total_errors=0, error_types={}, columns_validated=0),
        )
        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
            ),
        )
        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )
        state = ProcessorState(combined_results=combined_results)

        result = state.get_combined_results()
        assert result == combined_results
        assert result.has_validation_results()
        assert result.has_schema_alignment_results()

    def test_get_processing_duration_with_no_start_time(self):
        """Test get_processing_duration with no start time."""
        state = ProcessorState()
        assert state.get_processing_duration() is None

    def test_get_processing_duration_with_start_time(self):
        """Test get_processing_duration with start time."""
        start_time = datetime.now() - timedelta(seconds=5)
        state = ProcessorState(processing_start_time=start_time)

        duration = state.get_processing_duration()
        assert duration is not None
        assert duration >= 4.0  # Should be at least 4 seconds
        assert duration <= 10.0  # Should be less than 10 seconds (allowing for test execution time)


class TestProcessorStateSerialization:
    """Test ProcessorState serialization and validation behavior."""

    def test_model_dump_basic_fields(self):
        """Test model_dump with basic fields."""
        state = ProcessorState(
            job_id="test-job",
            program_id="test-program",
            core_id="test-core",
            current_stage="validation",
        )

        data = state.model_dump()

        assert data["job_id"] == "test-job"
        assert data["program_id"] == "test-program"
        assert data["core_id"] == "test-core"
        assert data["current_stage"] == "validation"
        assert data["metadata_df"] is None
        assert data["processing_start_time"] is None

    def test_model_dump_with_datetime(self):
        """Test model_dump with datetime field."""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        state = ProcessorState(processing_start_time=start_time)

        data = state.model_dump()

        assert data["processing_start_time"] == start_time

    def test_model_dump_excludes_dataframes_by_default(self):
        """Test that DataFrames are included in model_dump (arbitrary types allowed)."""
        df = pd.DataFrame({"column1": ["value1"]})
        state = ProcessorState(metadata_df=df)

        data = state.model_dump()

        # DataFrames should be included since arbitrary_types_allowed=True
        assert "metadata_df" in data
        assert isinstance(data["metadata_df"], pd.DataFrame)

    def test_model_validation_with_invalid_types(self):
        """Test model validation with invalid field types."""
        # Test with invalid job_id type
        with pytest.raises(ValidationError):
            ProcessorState(job_id=123)  # Should be string

        # Test with invalid processing_start_time type
        with pytest.raises(ValidationError):
            ProcessorState(processing_start_time="not-a-datetime")


class TestProcessorStateComplexScenarios:
    """Test ProcessorState in complex processing scenarios."""

    def test_complete_processing_state(self):
        """Test ProcessorState with all fields populated."""
        # Create test data
        metadata_df = pd.DataFrame({"column1": ["value1", "value2"], "column2": [1, 2]})

        aligned_df = pd.DataFrame({"aligned_column1": ["value1", "value2"], "aligned_column2": [1, 2]})

        schema_definition = {
            "columns": {
                "aligned_column1": {"type": "string", "required": True},
                "aligned_column2": {"type": "integer", "required": False},
            }
        }

        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="aligned_column1",
                    current_value="invalid",
                    error_type=ValidationErrorType.INVALID_OPTION,
                    valid_options=["valid1", "valid2"],
                    recommended_value="valid1",
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=2,
                total_errors=1,
                error_types={ValidationErrorType.INVALID_OPTION: 1},
                columns_validated=1,
            ),
        )

        combined_results = CombinedResults(validation_results=validation_results)
        start_time = datetime.now()

        # Create complete state
        state = ProcessorState(
            metadata_df=metadata_df,
            program_id="test-program",
            core_id="test-core",
            aligned_df=aligned_df,
            schema_definition=schema_definition,
            combined_results=combined_results,
            job_id="complete-job-123",
            current_stage="prediction",
            processing_start_time=start_time,
        )

        # Verify all fields
        assert state.has_metadata()
        assert state.has_schema_ids()
        assert state.has_aligned_data()
        assert state.has_validation_results()
        assert state.job_id == "complete-job-123"
        assert state.current_stage == "prediction"
        assert state.processing_start_time == start_time

        # Verify DataFrames
        pd.testing.assert_frame_equal(state.metadata_df, metadata_df)
        pd.testing.assert_frame_equal(state.aligned_df, aligned_df)

        # Verify complex objects
        assert state.schema_definition == schema_definition
        assert state.combined_results == combined_results

    def test_state_progression_simulation(self):
        """Test simulating state progression through processing stages."""
        # Initial state
        state = ProcessorState(job_id="progression-test", processing_start_time=datetime.now())

        # Stage 1: Add input data
        state.metadata_df = pd.DataFrame({"raw_column": ["data1", "data2"]})
        state.program_id = "test-program"
        state.core_id = "test-core"
        state.set_current_stage("schema_alignment")

        assert state.has_metadata()
        assert state.has_schema_ids()
        assert state.current_stage == "schema_alignment"

        # Stage 2: Add aligned data
        state.aligned_df = pd.DataFrame({"aligned_column": ["data1", "data2"]})
        state.schema_definition = {"columns": {"aligned_column": {"type": "string"}}}
        state.set_current_stage("validation")

        assert state.has_aligned_data()
        assert state.current_stage == "validation"

        # Stage 3: Add validation results
        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=2, total_errors=0, error_types={}, columns_validated=0),
        )
        state.combined_results = CombinedResults(validation_results=validation_results)
        state.set_current_stage("complete")

        assert state.has_validation_results()
        assert state.current_stage == "complete"

        # Verify processing duration
        duration = state.get_processing_duration()
        assert duration is not None
        assert duration >= 0


class TestProcessorStateResultInstances:
    """Test ProcessorState result instance management with CombinedResults."""

    def test_initialization_with_schema_alignment_results(self):
        """Test creating ProcessorState with SchemaAlignmentResults in CombinedResults."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
            ),
        )

        combined_results = CombinedResults(schema_alignment_results=schema_alignment_results)
        state = ProcessorState(combined_results=combined_results)

        assert state.combined_results.schema_alignment_results == schema_alignment_results
        assert state.has_schema_alignment_results()
        assert not state.has_validation_results()

    def test_initialization_with_both_result_instances(self):
        """Test creating ProcessorState with both ValidationResults and SchemaAlignmentResults in CombinedResults."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
        )

        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=2, total_errors=0, error_types={}, columns_validated=0),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
            ),
        )

        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )
        state = ProcessorState(combined_results=combined_results)

        assert state.combined_results.validation_results == validation_results
        assert state.combined_results.schema_alignment_results == schema_alignment_results
        assert state.has_validation_results()
        assert state.has_schema_alignment_results()

    def test_model_dump_includes_combined_results(self):
        """Test that model_dump includes combined_results."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
        )

        validation_results = ValidationResults(
            validation_results=[],
            summary=ValidationResultsSummary(total_rows=2, total_errors=0, error_types={}, columns_validated=0),
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test-job",
                version=1,
                original_data_csv="col1,col2\nval1,val2",
                aligned_data_csv="aligned_col1,aligned_col2\nval1,val2",
            ),
        )

        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )

        state = ProcessorState(
            combined_results=combined_results,
            column_mappings={"col1": "aligned_col1"},
            transformation_summary={"columns_renamed": 1},
        )

        data = state.model_dump()

        # model_dump() serializes Pydantic models to dictionaries
        assert "combined_results" in data
        assert data["column_mappings"] == {"col1": "aligned_col1"}
        assert data["transformation_summary"] == {"columns_renamed": 1}

        # Verify the actual objects are preserved in the state
        assert state.combined_results == combined_results

    def test_complete_combined_results_scenario(self):
        """Test complete scenario with CombinedResults and processing metadata."""
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResultsSummary,
        )

        # Original DataFrame
        original_df = pd.DataFrame({"raw_column1": ["value1", "value2"], "raw_column2": [1, 2]})

        # Aligned DataFrame
        aligned_df = pd.DataFrame({"aligned_column1": ["value1", "value2"], "aligned_column2": [1, 2]})

        # Validation results
        validation_results = ValidationResults(
            validation_results=[
                ValidationErrorDetail(
                    row=1,
                    column="aligned_column1",
                    current_value="invalid",
                    error_type=ValidationErrorType.INVALID_OPTION,
                    valid_options=["valid1", "valid2"],
                )
            ],
            summary=ValidationResultsSummary(
                total_rows=2,
                total_errors=1,
                error_types={ValidationErrorType.INVALID_OPTION: 1},
                columns_validated=1,
            ),
        )

        # Schema alignment results
        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="dual-instance-test",
                version=1,
                original_data_csv="raw_column1,raw_column2\nvalue1,1\nvalue2,2",
                aligned_data_csv="aligned_column1,aligned_column2\nvalue1,1\nvalue2,2",
                columns_renamed=2,
                rows_original=2,
                rows_aligned=2,
            ),
        )

        # Combined results
        combined_results = CombinedResults(
            validation_results=validation_results,
            schema_alignment_results=schema_alignment_results,
        )

        # Processing metadata
        column_mappings = {
            "raw_column1": "aligned_column1",
            "raw_column2": "aligned_column2",
        }
        transformation_summary = {
            "columns_renamed": 2,
            "columns_added": 0,
            "columns_removed": 0,
            "rows_original": 2,
            "rows_aligned": 2,
        }

        state = ProcessorState(
            metadata_df=original_df,
            aligned_df=aligned_df,
            combined_results=combined_results,
            column_mappings=column_mappings,
            transformation_summary=transformation_summary,
            job_id="dual-instance-test",
        )

        # Verify DataFrame methods still work
        assert state.has_metadata()
        assert state.has_aligned_data()

        # Verify result instance methods work
        assert state.has_validation_results()
        assert state.has_schema_alignment_results()

        # Verify get_combined_results works
        result = state.get_combined_results()
        assert result == combined_results
        assert result.validation_results == validation_results
        assert result.schema_alignment_results == schema_alignment_results

        # Verify data integrity
        pd.testing.assert_frame_equal(state.metadata_df, original_df)
        pd.testing.assert_frame_equal(state.aligned_df, aligned_df)
        assert state.combined_results == combined_results
        assert state.column_mappings == column_mappings
        assert state.transformation_summary == transformation_summary
