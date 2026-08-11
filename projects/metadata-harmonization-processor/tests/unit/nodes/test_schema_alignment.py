# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for SchemaAlignmentNode.

This module contains comprehensive unit tests for the schema alignment
functionality, including column mapping, missing column handling,
error scenarios, and Strands Agent compatibility.
"""

from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest

from metadata_harmonization_processor.interfaces.schema_collector import SchemaCollector
from metadata_harmonization_processor.models.schema_alignment_results import (
    SchemaAlignmentResults,
)
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.nodes.schema_alignment import (
    SchemaAlignmentError,
    SchemaAlignmentNode,
)


class TestSchemaAlignmentNode:
    """Test cases for SchemaAlignmentNode."""

    @pytest.fixture
    def mock_schema_collector(self):
        """Create a mock SchemaCollector for testing."""
        collector = Mock(spec=SchemaCollector)
        collector.get_schema = AsyncMock()
        collector.get_schema_columns = AsyncMock()
        return collector

    @pytest.fixture
    def schema_alignment_node(self, mock_schema_collector):
        """Create a SchemaAlignmentNode instance for testing."""
        return SchemaAlignmentNode(mock_schema_collector)

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame(
            {
                "Name": ["John", "Jane", "Bob"],
                "age": [25, 30, 35],
                "Email Address": ["john@test.com", "jane@test.com", "bob@test.com"],
                "extra_column": ["extra1", "extra2", "extra3"],
            }
        )

    @pytest.fixture
    def expected_columns(self):
        """Expected columns from schema."""
        return ["name", "age", "email_address", "phone_number"]

    @pytest.fixture
    def sample_schema_definition(self):
        """Sample schema definition."""
        return {
            "properties": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "required": False},
                "email_address": {"type": "string", "required": True},
                "phone_number": {"type": "string", "required": False},
            }
        }

    @pytest.fixture
    def valid_state(self, sample_dataframe):
        """Create a valid ProcessorState for testing."""
        return ProcessorState(
            metadata_df=sample_dataframe,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

    @pytest.mark.asyncio
    async def test_successful_alignment(
        self,
        schema_alignment_node,
        mock_schema_collector,
        valid_state,
        expected_columns,
        sample_schema_definition,
    ):
        """Test successful schema alignment with column mapping."""
        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment using MultiAgentBase interface
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify schema collector calls
        mock_schema_collector.get_schema.assert_called_once_with("test_program", "test_core")
        mock_schema_collector.get_schema_columns.assert_called_once_with("test_program", "test_core")

        # Verify MultiAgentResult structure
        assert hasattr(result, "status")
        assert hasattr(result, "results")
        assert result.status.name == "COMPLETED"  # Status enum
        assert "schema_alignment" in result.results

        # Verify state updates (state is modified in place)
        assert valid_state.current_stage == "schema_alignment"
        assert valid_state.schema_definition == sample_schema_definition
        assert valid_state.aligned_df is not None

        # Verify DataFrame alignment
        aligned_df = valid_state.aligned_df
        assert list(aligned_df.columns) == expected_columns
        assert len(aligned_df) == 3  # Same number of rows

        # Verify column mappings worked
        assert aligned_df["name"].tolist() == ["John", "Jane", "Bob"]
        assert aligned_df["age"].tolist() == [25, 30, 35]
        assert aligned_df["email_address"].tolist() == [
            "john@test.com",
            "jane@test.com",
            "bob@test.com",
        ]

        # Verify phone_number column exists (LLM may map extra_column to it or leave it null)
        assert "phone_number" in aligned_df.columns

        # Verify SchemaAlignmentResults instance was created and stored in CombinedResults
        assert valid_state.has_schema_alignment_results()
        assert valid_state.combined_results is not None
        assert valid_state.combined_results.has_schema_alignment_results()
        schema_results = valid_state.combined_results.schema_alignment_results
        assert isinstance(schema_results, SchemaAlignmentResults)
        assert schema_results.summary.job_id == "test_job"
        assert schema_results.summary.version == 1
        assert schema_results.summary.original_data_csv is not None
        assert schema_results.summary.aligned_data_csv is not None
        assert len(schema_results.schema_alignment_results) > 0  # Should have change details
        assert schema_results.summary.total_changes > 0

    @pytest.mark.asyncio
    async def test_schema_alignment_results_instance_creation(
        self,
        schema_alignment_node,
        mock_schema_collector,
        valid_state,
        expected_columns,
        sample_schema_definition,
    ):
        """Test that SchemaAlignmentResults instance is created and stored correctly."""
        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify successful completion
        assert result.status.name == "COMPLETED"

        # Verify SchemaAlignmentResults instance was created in CombinedResults
        assert valid_state.has_schema_alignment_results()
        assert valid_state.combined_results is not None
        assert valid_state.combined_results.has_schema_alignment_results()
        schema_results = valid_state.combined_results.schema_alignment_results

        # Verify instance properties
        assert isinstance(schema_results, SchemaAlignmentResults)
        assert schema_results.summary.job_id == "test_job"
        assert schema_results.summary.version == 1

        # Verify CSV data is present in the summary
        assert schema_results.summary.original_data_csv is not None
        assert len(schema_results.summary.original_data_csv) > 0
        assert "Name,age,Email Address,extra_column" in schema_results.summary.original_data_csv

        assert schema_results.summary.aligned_data_csv is not None
        assert len(schema_results.summary.aligned_data_csv) > 0
        assert "name,age,email_address,phone_number" in schema_results.summary.aligned_data_csv

        # Verify change details are populated
        assert isinstance(schema_results.schema_alignment_results, list)
        assert len(schema_results.schema_alignment_results) > 0

        # Verify change types are present
        change_types = [change.change_type for change in schema_results.schema_alignment_results]
        assert "rename" in change_types
        # LLM may identify different types of changes (split, add, remove, combine)
        assert len(change_types) > 0

        # Verify aggregate statistics
        # LLM may map extra_column to phone_number, so we check for total changes instead
        assert schema_results.summary.columns_renamed >= 2  # At least Name and Email Address
        assert schema_results.summary.total_changes > 0  # Should have some changes

        # Verify serialization methods work
        result_dict = schema_results.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["summary"]["job_id"] == "test_job"

        # Verify deserialization works
        recreated_results = SchemaAlignmentResults.from_dict(result_dict)
        assert recreated_results.summary.job_id == schema_results.summary.job_id

    @pytest.mark.asyncio
    async def test_combined_results_population(
        self,
        schema_alignment_node,
        mock_schema_collector,
        valid_state,
        expected_columns,
        sample_schema_definition,
    ):
        """Test that CombinedResults is initialized and schema_alignment_results is populated correctly."""
        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Verify state starts without combined_results
        assert valid_state.combined_results is None

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify successful completion
        assert result.status.name == "COMPLETED"

        # Verify CombinedResults was initialized
        assert valid_state.combined_results is not None
        assert valid_state.combined_results.__class__.__name__ == "CombinedResults"

        # Verify schema_alignment_results is populated in CombinedResults
        assert valid_state.combined_results.has_schema_alignment_results()
        schema_results = valid_state.combined_results.schema_alignment_results

        # Verify instance properties
        assert isinstance(schema_results, SchemaAlignmentResults)
        assert schema_results.summary.job_id == "test_job"
        assert schema_results.summary.version == 1

        # Verify CSV data is present in the summary
        assert schema_results.summary.original_data_csv is not None
        assert len(schema_results.summary.original_data_csv) > 0
        assert "Name,age,Email Address,extra_column" in schema_results.summary.original_data_csv

        assert schema_results.summary.aligned_data_csv is not None
        assert len(schema_results.summary.aligned_data_csv) > 0
        assert "name,age,email_address,phone_number" in schema_results.summary.aligned_data_csv

        # Verify change details are populated
        assert isinstance(schema_results.schema_alignment_results, list)
        assert len(schema_results.schema_alignment_results) > 0

        # Verify change types are tracked
        change_types = [change.change_type for change in schema_results.schema_alignment_results]
        assert "rename" in change_types  # Should have column renames
        # LLM may map extra_column to phone_number instead of adding/removing
        # So we don't enforce specific add/remove counts

        # Verify aggregate statistics match change details
        rename_count = sum(1 for change in schema_results.schema_alignment_results if change.change_type == "rename")
        add_count = sum(1 for change in schema_results.schema_alignment_results if change.change_type == "add")
        remove_count = sum(1 for change in schema_results.schema_alignment_results if change.change_type == "remove")

        assert schema_results.summary.columns_renamed == rename_count
        assert schema_results.summary.columns_added == add_count
        assert schema_results.summary.columns_removed == remove_count
        assert schema_results.summary.total_changes == len(schema_results.schema_alignment_results)

        # Verify row counts
        assert schema_results.summary.rows_original == 3
        assert schema_results.summary.rows_aligned == 3

        # Verify CombinedResults serialization works
        combined_dict = valid_state.combined_results.to_dict()
        assert isinstance(combined_dict, dict)
        assert "schema_alignment_results" in combined_dict
        assert combined_dict["schema_alignment_results"]["summary"]["job_id"] == "test_job"

        # Verify validation_results is None (not populated by schema alignment node)
        assert not valid_state.combined_results.has_validation_results()
        assert valid_state.combined_results.validation_results is None

    @pytest.mark.asyncio
    async def test_combined_results_preserves_existing_validation_results(
        self,
        schema_alignment_node,
        mock_schema_collector,
        valid_state,
        expected_columns,
        sample_schema_definition,
    ):
        """Test that CombinedResults preserves existing validation_results when adding schema_alignment_results."""
        from metadata_harmonization_processor.models.combined_results import (
            CombinedResults,
        )
        from metadata_harmonization_processor.models.validation import ValidationResults

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Pre-populate state with existing validation results
        from metadata_harmonization_processor.models.validation import (
            ValidationErrorType,
            ValidationResultsSummary,
        )

        summary = ValidationResultsSummary(
            total_rows=3,
            total_errors=0,
            error_types={
                ValidationErrorType.REQUIRED_VALUE: 0,
                ValidationErrorType.INVALID_OPTION: 0,
                ValidationErrorType.INVALID_PATTERN: 0,
            },
            columns_validated=4,
        )
        existing_validation_results = ValidationResults(validation_results=[], summary=summary)
        valid_state.combined_results = CombinedResults(validation_results=existing_validation_results)

        # Verify initial state
        assert valid_state.combined_results.has_validation_results()
        assert not valid_state.combined_results.has_schema_alignment_results()

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify successful completion
        assert result.status.name == "COMPLETED"

        # Verify both results are now present
        assert valid_state.combined_results.has_validation_results()
        assert valid_state.combined_results.has_schema_alignment_results()

        # Verify existing validation results were preserved
        assert valid_state.combined_results.validation_results is existing_validation_results
        assert valid_state.combined_results.validation_results.summary.total_rows == 3

        # Verify schema alignment results were added
        schema_results = valid_state.combined_results.schema_alignment_results
        assert isinstance(schema_results, SchemaAlignmentResults)
        assert schema_results.summary.job_id == "test_job"

    @pytest.mark.asyncio
    async def test_missing_metadata_df(self, schema_alignment_node):
        """Test error when metadata_df is missing."""
        state = ProcessorState(program_id="test_program", core_id="test_core")

        # Execute alignment using MultiAgentBase interface
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "schema_alignment" in result.results
        assert "Input state must contain metadata_df" in str(result.results["schema_alignment"].result)

    @pytest.mark.asyncio
    async def test_missing_schema_ids(self, schema_alignment_node, sample_dataframe):
        """Test error when schema IDs are missing."""
        state = ProcessorState(metadata_df=sample_dataframe)

        # Execute alignment using MultiAgentBase interface
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "schema_alignment" in result.results
        assert "Input state must contain program_id and core_id" in str(result.results["schema_alignment"].result)

    @pytest.mark.asyncio
    async def test_empty_dataframe(
        self,
        schema_alignment_node,
        mock_schema_collector,
        expected_columns,
        sample_schema_definition,
    ):
        """Test alignment with empty DataFrame."""
        empty_df = pd.DataFrame()
        state = ProcessorState(metadata_df=empty_df, program_id="test_program", core_id="test_core")

        # Execute alignment using MultiAgentBase interface
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "schema_alignment" in result.results
        assert "Input state must contain metadata_df" in str(result.results["schema_alignment"].result)

    @pytest.mark.asyncio
    async def test_schema_collector_error(self, schema_alignment_node, mock_schema_collector, valid_state):
        """Test error handling when schema collector fails."""
        mock_schema_collector.get_schema.side_effect = Exception("Schema not found")

        # Execute alignment using MultiAgentBase interface
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "schema_alignment" in result.results
        assert "Schema alignment failed" in str(result.results["schema_alignment"].result)

    def test_column_name_normalization(self, schema_alignment_node):
        """Test column name normalization logic."""
        # Test various column name formats
        test_cases = [
            ("User Name", "user_name"),
            ("user-name", "user_name"),
            ("user.name", "user_name"),
            ("UserName", "username"),
            ("  user_name  ", "user_name"),
            ("USER_NAME", "user_name"),
        ]

        for input_name, expected in test_cases:
            result = schema_alignment_node._normalize_column_name(input_name)
            assert result == expected, f"Expected {expected}, got {result} for input {input_name}"

    def test_find_column_mappings(self, schema_alignment_node, valid_state):
        """Test column mapping logic."""
        current_columns = {"User Name", "Email-Address", "phone.number", "AGE"}
        expected_columns = {"user_name", "email_address", "phone_number", "age"}

        mappings = schema_alignment_node._find_column_mappings(current_columns, expected_columns, valid_state)

        expected_mappings = {
            "User Name": "user_name",
            "Email-Address": "email_address",
            "phone.number": "phone_number",
            "AGE": "age",
        }

        assert mappings == expected_mappings

    def test_add_missing_columns(self, schema_alignment_node):
        """Test adding missing columns to DataFrame."""
        df = pd.DataFrame({"existing_col": [1, 2, 3]})
        missing_columns = {"new_col1", "new_col2"}

        schema_alignment_node._add_missing_columns(df, missing_columns)

        assert "new_col1" in df.columns
        assert "new_col2" in df.columns
        assert df["new_col1"].isna().all()
        assert df["new_col2"].isna().all()

    def test_handle_extra_columns(self, schema_alignment_node):
        """Test handling of extra columns."""
        df = pd.DataFrame({"keep_col": [1, 2, 3], "extra_col1": [4, 5, 6], "extra_col2": [7, 8, 9]})
        extra_columns = {"extra_col1", "extra_col2"}

        schema_alignment_node._handle_extra_columns(df, extra_columns)

        assert "keep_col" in df.columns
        assert "extra_col1" not in df.columns
        assert "extra_col2" not in df.columns

    @pytest.mark.asyncio
    async def test_exact_column_match(self, schema_alignment_node, mock_schema_collector, sample_schema_definition):
        """Test alignment when columns already match exactly."""
        # DataFrame with columns that already match expected
        df = pd.DataFrame(
            {
                "name": ["John", "Jane"],
                "age": [25, 30],
                "email_address": ["john@test.com", "jane@test.com"],
                "phone_number": ["123-456-7890", "098-765-4321"],
            }
        )

        expected_columns = ["name", "age", "email_address", "phone_number"]

        state = ProcessorState(metadata_df=df, program_id="test_program", core_id="test_core")

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment using MultiAgentBase interface
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify no changes needed (state is modified in place)
        aligned_df = state.aligned_df
        assert list(aligned_df.columns) == expected_columns
        assert aligned_df.equals(df)  # Should be identical

    @pytest.mark.asyncio
    async def test_partial_column_match(self, schema_alignment_node, mock_schema_collector, sample_schema_definition):
        """Test alignment with partial column matches."""
        # DataFrame with some matching and some non-matching columns
        df = pd.DataFrame(
            {
                "name": ["John", "Jane"],  # Exact match
                "Age": [25, 30],  # Case difference
                "email": ["john@test.com", "jane@test.com"],  # Partial match
                "unknown_col": ["data1", "data2"],  # No match
            }
        )

        expected_columns = ["name", "age", "email_address", "phone_number"]

        state = ProcessorState(metadata_df=df, program_id="test_program", core_id="test_core")

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment using MultiAgentBase interface
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify alignment results (state is modified in place)
        aligned_df = state.aligned_df
        assert list(aligned_df.columns) == expected_columns

        # Verify data preservation for matched columns
        assert aligned_df["name"].tolist() == ["John", "Jane"]
        assert aligned_df["age"].tolist() == [25, 30]  # Should be renamed from 'Age'

        # Verify email was matched (substring matching should work)
        assert aligned_df["email_address"].tolist() == [
            "john@test.com",
            "jane@test.com",
        ]  # 'email' matched 'email_address'
        # Verify phone_number column exists (LLM may map unknown_col to it or leave it null)
        assert "phone_number" in aligned_df.columns

    @pytest.mark.asyncio
    async def test_session_manager_integration(
        self,
        schema_alignment_node,
        mock_schema_collector,
        valid_state,
        expected_columns,
        sample_schema_definition,
    ):
        """Test session manager integration for state persistence."""
        # Create mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.save_data = AsyncMock()
        mock_session_manager.get_data = AsyncMock(return_value=None)  # No cached data

        # Attach session manager to node
        schema_alignment_node.session_manager = mock_session_manager

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify session manager was called for state persistence
        assert mock_session_manager.save_data.call_count >= 2  # At least start and complete checkpoints

        # Verify specific checkpoint calls
        call_args_list = [call[0] for call in mock_session_manager.save_data.call_args_list]
        checkpoint_keys = [args[0] for args in call_args_list]

        assert any("schema_alignment_start" in key for key in checkpoint_keys)
        assert any("schema_alignment_complete" in key for key in checkpoint_keys)

    @pytest.mark.asyncio
    async def test_schema_caching_with_session_manager(
        self,
        schema_alignment_node,
        mock_schema_collector,
        valid_state,
        expected_columns,
        sample_schema_definition,
    ):
        """Test schema caching functionality with session manager."""
        # Create mock session manager with cached schema
        mock_session_manager = AsyncMock()
        mock_session_manager.get_data = AsyncMock()
        mock_session_manager.save_data = AsyncMock()

        # Setup cache responses
        cache_key = "test_program_test_core"
        mock_session_manager.get_data.side_effect = lambda key: {
            f"schema_def_{cache_key}": sample_schema_definition,
            f"schema_cols_{cache_key}": expected_columns,
        }.get(key, None)

        # Attach session manager to node
        schema_alignment_node.session_manager = mock_session_manager

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify schema collector was NOT called (cache hit)
        mock_schema_collector.get_schema.assert_not_called()
        mock_schema_collector.get_schema_columns.assert_not_called()

        # Verify session manager was called for cache lookup
        expected_cache_calls = [f"schema_def_{cache_key}", f"schema_cols_{cache_key}"]

        get_data_calls = [call[0][0] for call in mock_session_manager.get_data.call_args_list]
        for expected_call in expected_cache_calls:
            assert expected_call in get_data_calls

    @pytest.mark.asyncio
    async def test_session_cleanup(self, schema_alignment_node):
        """Test session data cleanup functionality."""
        # Create mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.delete_data = AsyncMock()

        # Attach session manager to node
        schema_alignment_node.session_manager = mock_session_manager

        # Execute cleanup
        await schema_alignment_node.cleanup_session_data()

        # Verify cleanup calls
        assert mock_session_manager.delete_data.call_count >= 2

        # Verify specific cleanup keys
        call_args_list = [call[0][0] for call in mock_session_manager.delete_data.call_args_list]
        expected_keys = ["schema_alignment_start", "schema_alignment_complete"]

        for expected_key in expected_keys:
            assert expected_key in call_args_list

    @pytest.mark.asyncio
    async def test_session_manager_error_handling(
        self,
        schema_alignment_node,
        mock_schema_collector,
        valid_state,
        expected_columns,
        sample_schema_definition,
    ):
        """Test graceful handling of session manager errors."""
        # Create mock session manager that raises errors
        mock_session_manager = AsyncMock()
        mock_session_manager.save_data = AsyncMock(side_effect=Exception("Session error"))
        mock_session_manager.get_data = AsyncMock(side_effect=Exception("Session error"))

        # Attach session manager to node
        schema_alignment_node.session_manager = mock_session_manager

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment - should still succeed despite session errors
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task",
            invocation_state={"processor_state": valid_state},
        )

        # Verify successful result (session errors should not fail processing)
        assert result.status.name == "COMPLETED"

        # Verify schema collector was called (no cache due to errors)
        mock_schema_collector.get_schema.assert_called_once()
        mock_schema_collector.get_schema_columns.assert_called_once()

    def test_dataframe_to_csv_string_success(self, schema_alignment_node):
        """Test successful DataFrame to CSV string conversion."""
        # Create test DataFrame
        df = pd.DataFrame(
            {
                "name": ["John", "Jane", "Bob"],
                "age": [25, 30, 35],
                "email": ["john@test.com", "jane@test.com", "bob@test.com"],
            }
        )

        # Convert to CSV string
        csv_string = schema_alignment_node._dataframe_to_csv_string(df)

        # Verify result
        assert isinstance(csv_string, str)
        assert len(csv_string) > 0
        assert "name,age,email" in csv_string  # Header row
        assert "John,25,john@test.com" in csv_string  # Data row
        assert "Jane,30,jane@test.com" in csv_string
        assert "Bob,35,bob@test.com" in csv_string

        # Verify CSV format consistency
        lines = csv_string.strip().split("\n")
        assert len(lines) == 4  # Header + 3 data rows
        assert lines[0] == "name,age,email"

    def test_dataframe_to_csv_string_with_nulls(self, schema_alignment_node):
        """Test DataFrame to CSV string conversion with null values."""
        # Create DataFrame with null values
        df = pd.DataFrame(
            {
                "name": ["John", None, "Bob"],
                "age": [25, 30, None],
                "email": ["john@test.com", "jane@test.com", None],
            }
        )

        # Convert to CSV string
        csv_string = schema_alignment_node._dataframe_to_csv_string(df)

        # Verify null values are handled as empty strings
        assert isinstance(csv_string, str)
        assert len(csv_string) > 0

        # Check that null values become empty fields
        assert ",30.0," in csv_string  # Middle null (pandas converts to float when nulls present)
        assert "Bob,," in csv_string  # Trailing nulls

    def test_dataframe_to_csv_string_empty_dataframe(self, schema_alignment_node):
        """Test DataFrame to CSV string conversion with empty DataFrame."""
        # Create empty DataFrame
        df = pd.DataFrame()

        # Should raise SchemaAlignmentError for empty DataFrame
        with pytest.raises(SchemaAlignmentError) as exc_info:
            schema_alignment_node._dataframe_to_csv_string(df)

        assert "Failed to convert DataFrame to CSV string" in str(exc_info.value)

    def test_dataframe_to_csv_string_special_characters(self, schema_alignment_node):
        """Test DataFrame to CSV string conversion with special characters."""
        # Create DataFrame with special characters
        df = pd.DataFrame(
            {
                "name": ['John "Johnny" Doe', "Jane, Smith", "Bob\nNewline"],
                "description": ['Has "quotes"', "Has, comma", "Has\nnewline"],
            }
        )

        # Convert to CSV string
        csv_string = schema_alignment_node._dataframe_to_csv_string(df)

        # Verify result handles special characters properly
        assert isinstance(csv_string, str)
        assert len(csv_string) > 0

        # CSV should properly quote fields with special characters
        assert '"John ""Johnny"" Doe"' in csv_string or 'John "Johnny" Doe' in csv_string
        assert '"Jane, Smith"' in csv_string or "Jane, Smith" in csv_string

    def test_create_transformation_summary_basic(self, schema_alignment_node):
        """Test basic transformation summary creation."""
        # Import the change detail model
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentChangeDetail,
        )

        # Create original DataFrame
        original_df = pd.DataFrame(
            {
                "Name": ["John", "Jane"],
                "Age": [25, 30],
                "Email": ["john@test.com", "jane@test.com"],
            }
        )

        # Create aligned DataFrame (renamed columns, added column)
        aligned_df = pd.DataFrame(
            {
                "name": ["John", "Jane"],
                "age": [25, 30],
                "email_address": ["john@test.com", "jane@test.com"],
                "phone_number": [None, None],
            }
        )

        # Column mapping used during alignment
        column_mapping = {"Name": "name", "Age": "age", "Email": "email_address"}

        # Create change details with LLM and rule-based matching
        change_details = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="Name",
                new_column="name",
                reason="LLM-determined semantic match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="Age",
                new_column="age",
                reason="Rule-based pattern match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="Email",
                new_column="email_address",
                reason="LLM-determined semantic match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="phone_number",
                reason="Required by schema",
                row_count_affected=2,
            ),
        ]

        # Create transformation summary
        summary = schema_alignment_node._create_transformation_summary(
            original_df, aligned_df, column_mapping, change_details
        )

        # Verify summary structure
        assert isinstance(summary, dict)
        assert "columns_renamed" in summary
        assert "columns_added" in summary
        assert "columns_removed" in summary
        assert "rows_original" in summary
        assert "rows_aligned" in summary
        assert "column_mappings" in summary
        assert "added_columns" in summary
        assert "removed_columns" in summary

        # Verify counts
        assert summary["columns_renamed"] == 3  # Name, Age, Email renamed
        assert summary["columns_added"] == 1  # phone_number added
        assert summary["columns_removed"] == 0  # No columns removed
        assert summary["rows_original"] == 2
        assert summary["rows_aligned"] == 2

        # Verify mappings
        assert summary["column_mappings"] == column_mapping
        assert "phone_number" in summary["added_columns"]
        assert len(summary["removed_columns"]) == 0

        # Verify enhanced metadata from change details
        assert "change_breakdown" in summary
        assert "llm_processing" in summary
        assert "change_history" in summary
        assert "processing_metadata" in summary
        assert "impact_analysis" in summary

        # Verify change breakdown with LLM matching confidence
        change_breakdown = summary["change_breakdown"]
        assert "llm_matching_confidence" in change_breakdown
        assert "llm_matches" in change_breakdown
        assert "rule_based_matches" in change_breakdown
        assert change_breakdown["llm_matches"] == 2  # Name and Email
        assert change_breakdown["rule_based_matches"] == 2  # Age and phone_number add

        # Verify detailed column information
        assert "renamed_columns" in change_breakdown
        assert "added_column_details" in change_breakdown
        assert "removed_column_details" in change_breakdown

        # Verify LLM processing statistics
        llm_processing = summary["llm_processing"]
        assert "llm_success_rate" in llm_processing
        assert "total_llm_calls" in llm_processing
        assert "matching_method" in llm_processing

        # Verify change history with detailed changes
        change_history = summary["change_history"]
        assert "detailed_changes" in change_history
        assert len(change_history["detailed_changes"]) == 4  # All change details

        # Verify impact analysis
        impact_analysis = summary["impact_analysis"]
        assert "total_changes_detected" in impact_analysis
        assert impact_analysis["total_changes_detected"] == 4
        assert "schema_complexity_change" in impact_analysis

    def test_create_transformation_summary_with_removed_columns(self, schema_alignment_node):
        """Test transformation summary with removed columns."""
        # Import the change detail model
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentChangeDetail,
        )

        # Create original DataFrame with extra column
        original_df = pd.DataFrame(
            {
                "name": ["John", "Jane"],
                "age": [25, 30],
                "extra_col": ["extra1", "extra2"],
                "another_extra": ["extra3", "extra4"],
            }
        )

        # Create aligned DataFrame (removed extra columns)
        aligned_df = pd.DataFrame({"name": ["John", "Jane"], "age": [25, 30]})

        # No column mapping (exact matches)
        column_mapping = {}

        # Create change details for removed columns
        change_details = [
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="extra_col",
                new_column=None,
                reason="Not in target schema",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="another_extra",
                new_column=None,
                reason="Not in target schema",
                row_count_affected=2,
            ),
        ]

        # Create transformation summary
        summary = schema_alignment_node._create_transformation_summary(
            original_df, aligned_df, column_mapping, change_details
        )

        # Verify removed columns are tracked
        assert summary["columns_removed"] == 2
        assert "extra_col" in summary["removed_columns"]
        assert "another_extra" in summary["removed_columns"]

        # Verify enhanced metadata for removed columns
        assert "change_breakdown" in summary
        change_breakdown = summary["change_breakdown"]
        assert "removed_column_details" in change_breakdown
        assert "extra_col" in change_breakdown["removed_column_details"]
        assert "another_extra" in change_breakdown["removed_column_details"]

        # Verify removal reasons are captured
        assert change_breakdown["removed_column_details"]["extra_col"]["reason"] == "Not in target schema"
        assert change_breakdown["removed_column_details"]["another_extra"]["reason"] == "Not in target schema"
        assert summary["columns_renamed"] == 0
        assert summary["columns_added"] == 0

    def test_create_transformation_summary_complex_scenario(self, schema_alignment_node):
        """Test transformation summary with complex transformations."""
        # Import the change detail model
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentChangeDetail,
        )

        # Create original DataFrame
        original_df = pd.DataFrame(
            {
                "User Name": ["John", "Jane"],
                "user_age": [25, 30],
                "Email-Address": ["john@test.com", "jane@test.com"],
                "extra_field": ["extra1", "extra2"],
                "temp_col": ["temp1", "temp2"],
            }
        )

        # Create aligned DataFrame
        aligned_df = pd.DataFrame(
            {
                "name": ["John", "Jane"],
                "age": [25, 30],
                "email_address": ["john@test.com", "jane@test.com"],
                "phone_number": [None, None],
                "address": [None, None],
            }
        )

        # Column mapping
        column_mapping = {
            "User Name": "name",
            "user_age": "age",
            "Email-Address": "email_address",
        }

        # Create complex change details with mixed LLM and rule-based matching
        change_details = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="User Name",
                new_column="name",
                reason="LLM-determined semantic match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="user_age",
                new_column="age",
                reason="Rule-based pattern match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="Email-Address",
                new_column="email_address",
                reason="LLM-determined semantic match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="phone_number",
                reason="Required by schema",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="address",
                reason="Required by schema",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="extra_field",
                new_column=None,
                reason="Not in target schema",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="temp_col",
                new_column=None,
                reason="Not in target schema",
                row_count_affected=2,
            ),
        ]

        # Create transformation summary
        summary = schema_alignment_node._create_transformation_summary(
            original_df, aligned_df, column_mapping, change_details
        )

        # Verify complex transformation tracking
        assert summary["columns_renamed"] == 3
        assert summary["columns_added"] == 2  # phone_number, address
        assert summary["columns_removed"] == 2  # extra_field, temp_col

        # Verify detailed analysis
        assert "column_analysis" in summary
        assert summary["column_analysis"]["total_transformations"] == 7  # 3 + 2 + 2
        assert summary["original_column_count"] == 5
        assert summary["aligned_column_count"] == 5

        # Verify timestamp is included
        assert "transformation_timestamp" in summary
        assert isinstance(summary["transformation_timestamp"], str)

        # Verify enhanced metadata for complex scenario
        assert "change_breakdown" in summary
        change_breakdown = summary["change_breakdown"]
        assert change_breakdown["llm_matches"] == 2  # User Name and Email-Address
        assert change_breakdown["rule_based_matches"] == 5  # user_age, phone_number, address, extra_field, temp_col

        # Verify LLM confidence calculation
        assert "llm_matching_confidence" in change_breakdown
        expected_confidence = (2 / 7) * 100  # 2 LLM matches out of 7 total changes
        assert f"{expected_confidence:.1f}%" == change_breakdown["llm_matching_confidence"]

        # Verify impact analysis
        assert "impact_analysis" in summary
        impact_analysis = summary["impact_analysis"]
        assert impact_analysis["total_changes_detected"] == 7
        assert impact_analysis["columns_with_structural_changes"] == 4  # 2 adds + 2 removes

    def test_create_transformation_summary_no_changes(self, schema_alignment_node):
        """Test transformation summary when no changes are made."""
        # Create identical DataFrames
        df = pd.DataFrame(
            {
                "name": ["John", "Jane"],
                "age": [25, 30],
                "email": ["john@test.com", "jane@test.com"],
            }
        )

        # No column mapping
        column_mapping = {}

        # Empty change details (no changes)
        change_details = []

        # Create transformation summary
        summary = schema_alignment_node._create_transformation_summary(df, df, column_mapping, change_details)

        # Verify no transformations
        assert summary["columns_renamed"] == 0
        assert summary["columns_added"] == 0
        assert summary["columns_removed"] == 0
        assert summary["rows_original"] == summary["rows_aligned"]
        assert len(summary["added_columns"]) == 0
        assert len(summary["removed_columns"]) == 0
        assert summary["data_shape_changed"] is False

        # Verify enhanced metadata for no changes scenario
        assert "change_breakdown" in summary
        change_breakdown = summary["change_breakdown"]
        assert change_breakdown["llm_matches"] == 0
        assert change_breakdown["rule_based_matches"] == 0
        assert change_breakdown["llm_matching_confidence"] == "0.0%"

        # Verify impact analysis shows no changes
        assert "impact_analysis" in summary
        impact_analysis = summary["impact_analysis"]
        assert impact_analysis["total_changes_detected"] == 0

    def test_create_transformation_summary_error_handling(self, schema_alignment_node):
        """Test transformation summary error handling."""
        # Test with invalid input (None DataFrame)
        with pytest.raises(SchemaAlignmentError) as exc_info:
            schema_alignment_node._create_transformation_summary(None, None, {}, [])

        assert "Failed to create transformation summary" in str(exc_info.value)

    def test_create_transformation_summary_llm_integration(self, schema_alignment_node):
        """Test enhanced transformation summary with comprehensive LLM integration metadata."""
        # Import the change detail model
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentChangeDetail,
        )

        # Create test DataFrames
        original_df = pd.DataFrame(
            {
                "customer_name": ["Alice", "Bob"],
                "user_email": ["alice@test.com", "bob@test.com"],
                "phone": ["123-456-7890", "098-765-4321"],
            }
        )

        aligned_df = pd.DataFrame(
            {
                "name": ["Alice", "Bob"],
                "email_address": ["alice@test.com", "bob@test.com"],
                "phone_number": ["123-456-7890", "098-765-4321"],
                "address": [None, None],
            }
        )

        column_mapping = {
            "customer_name": "name",
            "user_email": "email_address",
            "phone": "phone_number",
        }

        # Create change details with mixed LLM and rule-based matching
        change_details = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="customer_name",
                new_column="name",
                reason="LLM-determined semantic match with high confidence",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="user_email",
                new_column="email_address",
                reason="LLM-determined semantic match with medium confidence",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="phone",
                new_column="phone_number",
                reason="Rule-based pattern match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="address",
                reason="Required by schema",
                row_count_affected=2,
            ),
        ]

        # Create transformation summary
        summary = schema_alignment_node._create_transformation_summary(
            original_df, aligned_df, column_mapping, change_details
        )

        # Verify LLM processing statistics
        llm_processing = summary["llm_processing"]
        assert "llm_success_rate" in llm_processing
        assert "total_llm_calls" in llm_processing
        assert "matching_method" in llm_processing
        assert "model_id" in llm_processing
        assert "aws_region" in llm_processing
        assert "llm_temperature" in llm_processing
        assert "llm_max_tokens" in llm_processing
        assert "llm_timeout_seconds" in llm_processing
        assert "similarity_threshold" in llm_processing

        # Verify change breakdown with LLM matching confidence
        change_breakdown = summary["change_breakdown"]
        assert change_breakdown["llm_matches"] == 2  # customer_name and user_email
        assert change_breakdown["rule_based_matches"] == 2  # phone and address
        assert change_breakdown["llm_matching_confidence"] == "50.0%"  # 2/4 * 100

        # Verify detailed change history with semantic matching details
        change_history = summary["change_history"]
        assert "detailed_changes" in change_history
        detailed_changes = change_history["detailed_changes"]
        assert len(detailed_changes) == 4

        # Verify semantic matching flags
        llm_changes = [change for change in detailed_changes if change["semantic_matching"]]
        rule_changes = [change for change in detailed_changes if not change["semantic_matching"]]
        assert len(llm_changes) == 2
        assert len(rule_changes) == 2

        # Verify impact analysis
        impact_analysis = summary["impact_analysis"]
        assert impact_analysis["total_changes_detected"] == 4
        assert impact_analysis["columns_with_semantic_changes"] == 2  # LLM matches
        assert impact_analysis["columns_with_structural_changes"] == 1  # address add

        # Verify processing metadata includes change validation
        processing_metadata = summary["processing_metadata"]
        assert processing_metadata["change_validation_passed"] is True
        assert processing_metadata["llm_processing_enabled"] is not None
        assert processing_metadata["change_tracking_enabled"] is not None

    def test_create_transformation_summary_validation_accuracy(self, schema_alignment_node):
        """Test that transformation summary accurately reflects all detected changes from LLM and rule-based matching."""
        # Import the change detail model
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentChangeDetail,
        )

        # Create test scenario with mismatched column mappings vs change details
        original_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        aligned_df = pd.DataFrame({"new_col1": [1, 2], "new_col2": [3, 4]})

        # Column mapping has different count than change details (to test validation)
        column_mapping = {"col1": "new_col1"}  # Only 1 mapping

        # Change details has more comprehensive information
        change_details = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="col1",
                new_column="new_col1",
                reason="LLM-determined semantic match",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="col2",
                new_column="new_col2",
                reason="Rule-based pattern match",
                row_count_affected=2,
            ),
        ]

        # Create transformation summary
        summary = schema_alignment_node._create_transformation_summary(
            original_df, aligned_df, column_mapping, change_details
        )

        # Verify that change_details is used as authoritative source
        assert summary["columns_renamed"] == 2  # From change_details, not column_mapping
        assert summary["total_transformations"] == 2

        # Verify validation warning is captured in processing metadata
        processing_metadata = summary["processing_metadata"]
        assert "change_validation_passed" in processing_metadata
        # The validation should pass because we're using change_details as authoritative

        # Verify change breakdown uses change_details data
        change_breakdown = summary["change_breakdown"]
        assert len(change_breakdown["renamed_columns"]) == 2  # Both renames from change_details
        assert "col1" in change_breakdown["renamed_columns"]
        assert "col2" in change_breakdown["renamed_columns"]

    def test_create_transformation_summary_comprehensive_change_metadata(self, schema_alignment_node):
        """Test comprehensive change metadata storage with before/after column states and transformation reasons."""
        # Import the change detail model
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentChangeDetail,
        )

        # Create comprehensive test scenario
        original_df = pd.DataFrame(
            {
                "first_name": ["John", "Jane"],
                "last_name": ["Doe", "Smith"],
                "email_addr": ["john@test.com", "jane@test.com"],
                "temp_field": ["temp1", "temp2"],
                "legacy_col": ["legacy1", "legacy2"],
            }
        )

        aligned_df = pd.DataFrame(
            {
                "name": ["John Doe", "Jane Smith"],  # Combined first_name + last_name
                "email_address": ["john@test.com", "jane@test.com"],
                "phone_number": [None, None],
                "created_date": [None, None],
            }
        )

        column_mapping = {"email_addr": "email_address"}

        # Comprehensive change details with various transformation reasons
        change_details = [
            SchemaAlignmentChangeDetail(
                change_type="rename",
                original_column="email_addr",
                new_column="email_address",
                reason="LLM-determined semantic match with standardization",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="name",
                reason="Schema requirement - combined field",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="phone_number",
                reason="Required by schema",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="add",
                original_column=None,
                new_column="created_date",
                reason="Audit field requirement",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="first_name",
                new_column=None,
                reason="Consolidated into name field",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="last_name",
                new_column=None,
                reason="Consolidated into name field",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="temp_field",
                new_column=None,
                reason="Not in target schema",
                row_count_affected=2,
            ),
            SchemaAlignmentChangeDetail(
                change_type="remove",
                original_column="legacy_col",
                new_column=None,
                reason="Deprecated field",
                row_count_affected=2,
            ),
        ]

        # Create transformation summary
        summary = schema_alignment_node._create_transformation_summary(
            original_df, aligned_df, column_mapping, change_details
        )

        # Verify complete change history with before/after column states
        change_history = summary["change_history"]
        assert "before_state" in change_history
        assert "after_state" in change_history
        assert "detailed_changes" in change_history

        before_state = change_history["before_state"]
        after_state = change_history["after_state"]

        assert before_state["column_count"] == 5
        assert after_state["column_count"] == 4
        assert set(before_state["columns"]) == {
            "first_name",
            "last_name",
            "email_addr",
            "temp_field",
            "legacy_col",
        }
        assert set(after_state["columns"]) == {
            "name",
            "email_address",
            "phone_number",
            "created_date",
        }

        # Verify detailed changes include transformation reasons
        detailed_changes = change_history["detailed_changes"]
        assert len(detailed_changes) == 8

        # Check specific transformation reasons are preserved
        email_change = next(change for change in detailed_changes if change["original_column"] == "email_addr")
        assert email_change["reason"] == "LLM-determined semantic match with standardization"

        consolidation_changes = [
            change for change in detailed_changes if change["reason"] == "Consolidated into name field"
        ]
        assert len(consolidation_changes) == 2  # first_name and last_name

        # Verify impact analysis with schema complexity change
        impact_analysis = summary["impact_analysis"]
        schema_complexity = impact_analysis["schema_complexity_change"]
        assert schema_complexity["before"] == 5
        assert schema_complexity["after"] == 4
        assert schema_complexity["net_change"] == -1  # Reduced complexity

        # Verify processing timestamp and impact analysis
        processing_metadata = summary["processing_metadata"]
        assert "processing_timestamp" in processing_metadata
        assert processing_metadata["total_rows_affected"] == 2
        assert processing_metadata["column_count_change"] == -1
        assert processing_metadata["data_integrity_maintained"] is True

    @pytest.mark.asyncio
    async def test_data_preservation_workflow_integration(
        self, schema_alignment_node, mock_schema_collector, sample_schema_definition
    ):
        """Test complete data preservation workflow integration."""
        # Create test DataFrame with transformations needed
        original_df = pd.DataFrame(
            {
                "User Name": ["John", "Jane", "Bob"],
                "user_age": [25, 30, 35],
                "Email-Address": ["john@test.com", "jane@test.com", "bob@test.com"],
                "extra_column": ["extra1", "extra2", "extra3"],
            }
        )

        expected_columns = ["name", "age", "email_address", "phone_number"]

        state = ProcessorState(
            metadata_df=original_df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify SchemaAlignmentResults instance was created with data preservation
        assert state.has_schema_alignment_results()
        assert state.combined_results is not None
        assert state.combined_results.has_schema_alignment_results()
        schema_results = state.combined_results.schema_alignment_results
        assert schema_results is not None
        assert schema_results.summary.original_data_csv is not None
        assert "User Name,user_age,Email-Address,extra_column" in schema_results.summary.original_data_csv
        assert "John,25,john@test.com,extra1" in schema_results.summary.original_data_csv

        # Verify aligned data preservation
        assert schema_results.summary.aligned_data_csv is not None
        assert "name,age,email_address,phone_number" in schema_results.summary.aligned_data_csv
        # All columns should map properly with our improved matching
        assert (
            "John,25,john@test.com," in schema_results.summary.aligned_data_csv
        )  # All data preserved, phone_number is null

        # Verify column mappings (LLM may map extra_column to phone_number)
        assert state.column_mappings is not None
        # Check that at least the main columns are mapped
        assert "User Name" in state.column_mappings or "Name" in state.column_mappings
        assert "Email-Address" in state.column_mappings

        # Verify transformation summary
        assert state.transformation_summary is not None
        summary = state.transformation_summary
        # LLM may rename extra_column to phone_number, so totals may vary
        assert summary["columns_renamed"] >= 2  # At least User Name and Email-Address
        assert summary["rows_original"] == 3
        assert summary["rows_aligned"] == 3

        # Verify all expected columns are present in the aligned DataFrame
        assert set(state.aligned_df.columns) == {
            "name",
            "age",
            "email_address",
            "phone_number",
        }

    @pytest.mark.asyncio
    async def test_data_preservation_with_csv_conversion_failure(
        self, schema_alignment_node, mock_schema_collector, sample_schema_definition
    ):
        """Test data preservation workflow when CSV conversion fails."""
        # Create test DataFrame
        df = pd.DataFrame({"name": ["John", "Jane"], "age": [25, 30]})

        expected_columns = ["name", "age"]

        state = ProcessorState(
            metadata_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Mock the CSV conversion to fail only for original data
        original_method = schema_alignment_node._dataframe_to_csv_string
        call_count = 0

        def failing_csv_conversion(df):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call (original DataFrame)
                raise Exception("CSV conversion failed")
            return original_method(df)  # Second call (aligned DataFrame) succeeds

        schema_alignment_node._dataframe_to_csv_string = failing_csv_conversion

        # Execute alignment - should still succeed despite CSV failure
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful result (CSV failure should not fail processing)
        assert result.status.name == "COMPLETED"

        # Verify SchemaAlignmentResults instance was not created due to CSV failure
        assert not state.has_schema_alignment_results()
        assert state.combined_results is None or not state.combined_results.has_schema_alignment_results()

        # Verify aligned data is still available (different DataFrame)
        # Note: SchemaAlignmentResults instance should not be created due to original CSV failure
        # But aligned data should still be processed and available in the aligned_df
        assert state.aligned_df is not None

        # Restore original method
        schema_alignment_node._dataframe_to_csv_string = original_method

    @pytest.mark.asyncio
    async def test_data_preservation_with_transformation_summary_failure(
        self, schema_alignment_node, mock_schema_collector, sample_schema_definition
    ):
        """Test data preservation workflow when transformation summary creation fails."""
        # Create test DataFrame
        df = pd.DataFrame({"name": ["John", "Jane"], "age": [25, 30]})

        expected_columns = ["name", "age"]

        state = ProcessorState(
            metadata_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Mock the transformation summary creation to fail
        original_method = schema_alignment_node._create_transformation_summary

        def failing_summary_creation(*args):
            raise Exception("Summary creation failed")

        schema_alignment_node._create_transformation_summary = failing_summary_creation

        # Execute alignment - should still succeed despite summary failure
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful result (summary failure should not fail processing)
        assert result.status.name == "COMPLETED"

        # Verify SchemaAlignmentResults instance was created despite summary failure
        assert state.has_schema_alignment_results()
        assert state.combined_results is not None
        assert state.combined_results.has_schema_alignment_results()
        schema_results = state.combined_results.schema_alignment_results
        assert schema_results is not None
        assert schema_results.summary.original_data_csv is not None
        assert schema_results.summary.aligned_data_csv is not None

        # Verify transformation summary has error information
        assert state.transformation_summary is not None
        assert "error" in state.transformation_summary
        assert state.transformation_summary["columns_renamed"] == 0
        assert state.transformation_summary["columns_added"] == 0
        assert state.transformation_summary["columns_removed"] == 0

        # Restore original method
        schema_alignment_node._create_transformation_summary = original_method

    @pytest.mark.asyncio
    async def test_data_preservation_no_transformations_needed(
        self, schema_alignment_node, mock_schema_collector, sample_schema_definition
    ):
        """Test data preservation when no transformations are needed."""
        # Create DataFrame that already matches expected schema
        df = pd.DataFrame(
            {
                "name": ["John", "Jane"],
                "age": [25, 30],
                "email_address": ["john@test.com", "jane@test.com"],
                "phone_number": ["123-456-7890", "098-765-4321"],
            }
        )

        expected_columns = ["name", "age", "email_address", "phone_number"]

        state = ProcessorState(
            metadata_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify SchemaAlignmentResults instance was created with data preservation
        assert state.has_schema_alignment_results()
        assert state.combined_results is not None
        assert state.combined_results.has_schema_alignment_results()
        schema_results = state.combined_results.schema_alignment_results
        assert schema_results is not None
        assert schema_results.summary.original_data_csv is not None
        assert schema_results.summary.aligned_data_csv is not None

        # Verify no transformations in summary
        assert state.transformation_summary is not None
        summary = state.transformation_summary
        assert summary["columns_renamed"] == 0
        assert summary["columns_added"] == 0
        assert summary["columns_removed"] == 0
        assert summary["data_shape_changed"] is False

        # Verify column mappings is empty
        assert state.column_mappings == {}

        # Verify original and aligned CSV should be very similar (same data, same columns)
        original_lines = schema_results.summary.original_data_csv.strip().split("\n")
        aligned_lines = schema_results.summary.aligned_data_csv.strip().split("\n")
        assert len(original_lines) == len(aligned_lines)
        assert original_lines[0] == aligned_lines[0]  # Same headers

    @pytest.mark.asyncio
    async def test_llm_enhanced_change_details_creation(
        self, schema_alignment_node, mock_schema_collector, sample_schema_definition
    ):
        """Test end-to-end SchemaAlignmentResults creation with LLM-based schema alignment scenarios and change tracking."""
        # Create DataFrame with various transformation scenarios
        df = pd.DataFrame(
            {
                "sample_id": ["S001", "S002", "S003"],  # Will be renamed to sampleId
                "patient_name": [
                    "John Doe",
                    "Jane Smith",
                    "Bob Johnson",
                ],  # Will be renamed to patientName
                "test_date": [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                ],  # Will be renamed to testDate
                "extra_column": ["extra1", "extra2", "extra3"],  # Will be removed
                "legacy_field": ["legacy1", "legacy2", "legacy3"],  # Will be removed
            }
        )

        # Expected columns from schema (different naming convention)
        expected_columns = ["sampleId", "patientName", "testDate", "labResult", "notes"]

        state = ProcessorState(
            metadata_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job_llm_enhanced",
        )

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment with LLM-enhanced processing
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful completion
        assert result.status.name == "COMPLETED"

        # Verify SchemaAlignmentResults instance was created with change details
        assert state.has_schema_alignment_results()
        assert state.combined_results is not None
        assert state.combined_results.has_schema_alignment_results()
        schema_results = state.combined_results.schema_alignment_results

        # Verify instance structure
        assert isinstance(schema_results, SchemaAlignmentResults)
        assert hasattr(schema_results, "schema_alignment_results")  # List of change details
        assert hasattr(schema_results, "summary")  # Summary object

        # Verify change details list is populated
        change_details = schema_results.schema_alignment_results
        assert isinstance(change_details, list)
        assert len(change_details) > 0  # Should have detected changes

        # Verify change detail structure and types
        change_types_found = set()
        for change in change_details:
            assert hasattr(change, "change_type")
            assert hasattr(change, "original_column")
            assert hasattr(change, "new_column")
            assert hasattr(change, "reason")
            assert hasattr(change, "row_count_affected")

            assert change.change_type in ["rename", "add", "remove", "split", "combine"]
            assert change.row_count_affected == len(df)  # All rows affected by column changes
            change_types_found.add(change.change_type)

        # Verify we have some types of changes (LLM may choose different transformation strategies)
        assert "rename" in change_types_found  # Should have column renames
        assert len(change_types_found) > 0  # Should have at least some changes

        # Verify specific rename changes
        rename_changes = [c for c in change_details if c.change_type == "rename"]
        assert len(rename_changes) >= 3  # At least sample_id, patient_name, test_date

        # Check for expected renames (case-insensitive matching should work)
        rename_mappings = {c.original_column: c.new_column for c in rename_changes}
        expected_renames = {
            "sample_id": "sampleId",
            "patient_name": "patientName",
            "test_date": "testDate",
        }

        for original, expected_new in expected_renames.items():
            assert original in rename_mappings
            assert rename_mappings[original] == expected_new

        # LLM may make different matching decisions, so we check that some changes were tracked
        # but don't enforce specific add/remove expectations
        assert len(change_details) > 0  # Should have tracked some changes

        # Verify change reasons include structured confidence/reasoning indicators
        for change in change_details:
            assert change.reason is not None
            assert len(change.reason) > 0
            # Reasons should follow the structured format with confidence/reasoning
            assert any(
                keyword in change.reason.lower()
                for keyword in [
                    "confidence",
                    "rule-based",
                    "required by schema",
                    "not in target schema",
                    "reasoning",
                ]
            )

        # Verify summary statistics match change details
        summary = schema_results.summary
        assert summary.total_changes == len(change_details)
        assert summary.columns_renamed == len(rename_changes)
        assert summary.rows_original == len(df)
        assert summary.rows_aligned == len(df)  # Row count should be preserved

        # Verify CSV data is present and valid
        assert summary.original_data_csv is not None
        assert len(summary.original_data_csv) > 0
        assert "sample_id,patient_name,test_date,extra_column,legacy_field" in summary.original_data_csv

        assert summary.aligned_data_csv is not None
        assert len(summary.aligned_data_csv) > 0
        assert "sampleId,patientName,testDate,labResult,notes" in summary.aligned_data_csv

        # Verify job metadata
        assert summary.job_id == "test_job_llm_enhanced"
        assert summary.version == 1
        assert summary.timestamp is not None

        # Verify serialization and deserialization work with change details
        result_dict = schema_results.to_dict()
        assert "schema_alignment_results" in result_dict
        assert "summary" in result_dict
        assert isinstance(result_dict["schema_alignment_results"], list)
        assert len(result_dict["schema_alignment_results"]) == len(change_details)

        # Verify each change detail is properly serialized
        for i, change_dict in enumerate(result_dict["schema_alignment_results"]):
            assert "change_type" in change_dict
            assert "reason" in change_dict
            assert "row_count_affected" in change_dict
            assert change_dict["change_type"] == change_details[i].change_type
            assert change_dict["reason"] == change_details[i].reason

        # Verify deserialization recreates the same structure
        recreated_results = SchemaAlignmentResults.from_dict(result_dict)
        assert len(recreated_results.schema_alignment_results) == len(change_details)
        assert recreated_results.summary.total_changes == summary.total_changes
        assert recreated_results.summary.job_id == summary.job_id

    @pytest.mark.asyncio
    async def test_llm_matching_success_rate_logging(
        self, schema_alignment_node, mock_schema_collector, sample_schema_definition
    ):
        """Test that SchemaAlignmentResults tracks LLM matching for success rate calculation."""
        # Create DataFrame that will trigger matching
        df = pd.DataFrame(
            {
                "user_id": ["U001", "U002"],  # Should match to userId
                "full_name": ["John Doe", "Jane Smith"],  # Should match to fullName
                "contact_email": [
                    "john@test.com",
                    "jane@test.com",
                ],  # Should match to email
            }
        )

        expected_columns = ["userId", "fullName", "email", "phoneNumber"]

        state = ProcessorState(
            metadata_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job_logging",
        )

        # Setup mocks
        mock_schema_collector.get_schema.return_value = sample_schema_definition
        mock_schema_collector.get_schema_columns.return_value = expected_columns

        # Execute alignment
        result = await schema_alignment_node.invoke_async(
            task="schema_alignment_task", invocation_state={"processor_state": state}
        )

        # Verify successful completion
        assert result.status.name == "COMPLETED"

        # Verify SchemaAlignmentResults was created with change details
        assert state.has_schema_alignment_results()
        schema_results = state.combined_results.schema_alignment_results

        # Verify change details contain matching information
        change_details = schema_results.schema_alignment_results
        assert len(change_details) > 0

        # Verify that reasons are set (indicating matching method used)
        for change in change_details:
            assert change.reason is not None
            assert len(change.reason) > 0

        # Verify LLM success rate can be calculated from change details
        # Some matching method should have been used (reasons should be populated)
        total_with_reasons = sum(1 for change in change_details if change.reason)
        assert total_with_reasons > 0

        # Verify summary statistics are consistent
        assert schema_results.summary.total_changes == len(change_details)
        assert schema_results.summary.job_id == "test_job_logging"
        assert schema_results.summary.version == 1
