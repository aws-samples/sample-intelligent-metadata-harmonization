# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for ValidationNode.

This module contains comprehensive unit tests for the validation
functionality, including different error types, validation rules,
and error scenarios for MultiAgentBase compatibility.
"""

from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest

from metadata_harmonization_processor.interfaces.schema_collector import SchemaCollector
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
)
from metadata_harmonization_processor.nodes.validation import ValidationNode


class TestValidationNode:
    """Test cases for ValidationNode."""

    @pytest.fixture
    def mock_schema_collector(self):
        """Create a mock SchemaCollector for testing."""
        collector = Mock(spec=SchemaCollector)
        collector.get_validation_rules = AsyncMock()
        return collector

    @pytest.fixture
    def validation_node(self, mock_schema_collector):
        """Create a ValidationNode instance for testing."""
        return ValidationNode(mock_schema_collector)

    @pytest.fixture
    def sample_aligned_dataframe(self):
        """Create a sample aligned DataFrame for testing."""
        return pd.DataFrame(
            {
                "name": ["John Doe", "", "Jane Smith"],
                "age": [25, 30, None],
                "status": ["active", "invalid_status", "inactive"],
                "email": ["john@test.com", "invalid-email", "jane@test.com"],
                "phone": ["123-456-7890", "123", ""],
            }
        )

    @pytest.fixture
    def sample_validation_rules(self):
        """Sample validation rules for testing."""
        return {
            "name": {"required": True, "pattern": r"^[A-Za-z\s]+$"},
            "age": {"required": False, "pattern": r"^\d+$"},
            "status": {"required": True, "options": ["active", "inactive", "pending"]},
            "email": {
                "required": True,
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
            "phone": {"required": False, "pattern": r"^\d{3}-\d{3}-\d{4}$"},
        }

    @pytest.fixture
    def validation_rules_with_custom_messages(self):
        """Sample validation rules with custom error messages for testing."""
        return {
            "library_strategy": {
                "required": True,
                "options": ["Amplicon"],
                "error_message": {"enum": 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'},
            },
            "sequence_id": {
                "required": True,
                "pattern": r"^[A-Za-z]{2}[0-9]{2}-[A-Za-z]{2}[A-Za-z0-9]{2}[0-9]{2}-Cx[0-9]-[A-Za-z]$",
                "error_message": {"regex": "sequence_id is a required field that must follow the proper formatting"},
            },
            "CSID": {
                "required": True,
                "pattern": r"^[0-9]{10}$",
                "error_message": {
                    "regex": "CSID is a required field and must be a ten-digit numerical string with no special characters"
                },
            },
            "submitter_state": {
                "required": True,
                "options": ["AK", "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA"],
                "error_message": {
                    "enum": "submitter_state is a required field and must be formatted as the two-letter State abbreviation"
                },
            },
        }

    @pytest.fixture
    def sample_dataframe_with_custom_errors(self):
        """Create a sample DataFrame that will trigger custom error messages."""
        return pd.DataFrame(
            {
                "library_strategy": ["Invalid", "", "Amplicon"],
                "sequence_id": ["invalid-format", "AB12-CD34-Cx1-A", ""],
                "CSID": ["123", "1234567890", "invalid"],
                "submitter_state": ["XX", "CA", ""],
            }
        )

    @pytest.fixture
    def valid_state(self, sample_aligned_dataframe):
        """Create a valid ProcessorState for testing."""
        return ProcessorState(
            aligned_df=sample_aligned_dataframe,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

    @pytest.mark.asyncio
    async def test_successful_validation(
        self,
        validation_node,
        mock_schema_collector,
        valid_state,
        sample_validation_rules,
    ):
        """Test successful validation with various error types."""
        # Setup mock
        mock_schema_collector.get_validation_rules.return_value = sample_validation_rules

        # Execute validation using MultiAgentBase interface
        result = await validation_node.invoke_async(
            task="validation_task", invocation_state={"processor_state": valid_state}
        )

        # Verify schema collector call
        mock_schema_collector.get_validation_rules.assert_called_once_with("test_program", "test_core")

        # Verify MultiAgentResult structure
        assert hasattr(result, "status")
        assert hasattr(result, "results")
        assert result.status.name == "COMPLETED"
        assert "validation" in result.results

        # Verify state updates
        assert valid_state.current_stage == "validation"
        assert valid_state.has_validation_results()

        # Verify combined_results structure
        assert valid_state.combined_results is not None
        assert valid_state.combined_results.has_validation_results()

        # Verify validation results structure
        validation_results = valid_state.combined_results.validation_results
        assert isinstance(validation_results, ValidationResults)
        assert validation_results.summary.total_rows == 3

        # Verify specific errors found
        errors = validation_results.validation_results

        # Should find REQUIRED_VALUE error for empty name in row 2 (1-based indexing)
        required_errors = [e for e in errors if e.error_type == ValidationErrorType.REQUIRED_VALUE]
        assert len(required_errors) >= 1
        name_required_error = next((e for e in required_errors if e.column == "name" and e.row == 2), None)
        assert name_required_error is not None

        # Should find INVALID_OPTION error for invalid status in row 2 (1-based indexing)
        option_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_OPTION]
        assert len(option_errors) >= 1
        status_option_error = next((e for e in option_errors if e.column == "status" and e.row == 2), None)
        assert status_option_error is not None
        assert status_option_error.valid_options == ["active", "inactive", "pending"]

        # Should find INVALID_PATTERN errors
        pattern_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_PATTERN]
        assert len(pattern_errors) >= 1

    @pytest.mark.asyncio
    async def test_missing_aligned_df(self, validation_node):
        """Test error when aligned_df is missing."""
        state = ProcessorState(program_id="test_program", core_id="test_core")

        # Execute validation using MultiAgentBase interface
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "validation" in result.results
        assert isinstance(result.results["validation"].result, Exception)
        assert "Input state must contain aligned_df" in str(result.results["validation"].result)

    @pytest.mark.asyncio
    async def test_missing_schema_ids(self, validation_node, sample_aligned_dataframe):
        """Test error when schema IDs are missing."""
        state = ProcessorState(aligned_df=sample_aligned_dataframe)

        # Execute validation using MultiAgentBase interface
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "validation" in result.results
        assert isinstance(result.results["validation"].result, Exception)
        assert "Input state must contain program_id and core_id" in str(result.results["validation"].result)

    @pytest.mark.asyncio
    async def test_empty_aligned_dataframe(self, validation_node, mock_schema_collector, sample_validation_rules):
        """Test validation with empty aligned DataFrame."""
        empty_df = pd.DataFrame()
        state = ProcessorState(aligned_df=empty_df, program_id="test_program", core_id="test_core")

        # Execute validation using MultiAgentBase interface
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "validation" in result.results
        assert isinstance(result.results["validation"].result, Exception)
        assert "Input state must contain aligned_df" in str(result.results["validation"].result)

    @pytest.mark.asyncio
    async def test_schema_collector_error(self, validation_node, mock_schema_collector, valid_state):
        """Test error handling when schema collector fails."""
        mock_schema_collector.get_validation_rules.side_effect = Exception("Rules not found")

        # Execute validation using MultiAgentBase interface
        result = await validation_node.invoke_async(
            task="validation_task", invocation_state={"processor_state": valid_state}
        )

        # Verify failed result
        assert result.status.name == "FAILED"
        assert "validation" in result.results
        assert isinstance(result.results["validation"].result, Exception)
        assert "Validation failed" in str(result.results["validation"].result)

    def test_validate_pattern_valid(self, validation_node):
        """Test pattern validation with valid values."""
        # Test valid email pattern
        assert validation_node._validate_pattern(
            "test@example.com", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )

        # Test valid phone pattern
        assert validation_node._validate_pattern("123-456-7890", r"^\d{3}-\d{3}-\d{4}$")

        # Test valid name pattern
        assert validation_node._validate_pattern("John Doe", r"^[A-Za-z\s]+$")

    def test_validate_pattern_invalid(self, validation_node):
        """Test pattern validation with invalid values."""
        # Test invalid email pattern
        assert not validation_node._validate_pattern(
            "invalid-email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )

        # Test invalid phone pattern
        assert not validation_node._validate_pattern("123", r"^\d{3}-\d{3}-\d{4}$")

        # Test invalid name pattern (contains numbers)
        assert not validation_node._validate_pattern("John123", r"^[A-Za-z\s]+$")

    def test_validate_pattern_invalid_regex(self, validation_node):
        """Test pattern validation with invalid regex."""
        # Should return True for invalid regex patterns (graceful handling)
        assert validation_node._validate_pattern("test", "[invalid regex")

    @pytest.mark.asyncio
    async def test_required_field_validation(self, validation_node, mock_schema_collector):
        """Test required field validation specifically."""
        df = pd.DataFrame(
            {
                "required_field": ["value", "", None, "another_value"],
                "optional_field": ["value", "", None, "another_value"],
            }
        )

        rules = {
            "required_field": {"required": True},
            "optional_field": {"required": False},
        }

        state = ProcessorState(aligned_df=df, program_id="test_program", core_id="test_core")

        mock_schema_collector.get_validation_rules.return_value = rules

        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})
        errors = state.combined_results.validation_results.validation_results

        # Should find REQUIRED_VALUE errors for rows 2 and 3 in required_field (1-based indexing)
        required_errors = [e for e in errors if e.error_type == ValidationErrorType.REQUIRED_VALUE]
        assert len(required_errors) == 2

        # Verify error details
        for error in required_errors:
            assert error.column == "required_field"
            assert error.row in [
                2,
                3,
            ]  # Empty string and None values (1-based indexing)

    @pytest.mark.asyncio
    async def test_options_validation(self, validation_node, mock_schema_collector):
        """Test options validation specifically."""
        df = pd.DataFrame({"status": ["active", "invalid", "inactive", "pending", "unknown"]})

        rules = {"status": {"required": True, "options": ["active", "inactive", "pending"]}}

        state = ProcessorState(aligned_df=df, program_id="test_program", core_id="test_core")

        mock_schema_collector.get_validation_rules.return_value = rules

        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})
        errors = state.combined_results.validation_results.validation_results

        # Should find INVALID_OPTION errors for 'invalid' and 'unknown'
        option_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_OPTION]
        assert len(option_errors) == 2

        # Verify error details
        for error in option_errors:
            assert error.column == "status"
            assert error.current_value in ["invalid", "unknown"]
            assert error.valid_options == ["active", "inactive", "pending"]

    @pytest.mark.asyncio
    async def test_pattern_validation(self, validation_node, mock_schema_collector):
        """Test pattern validation specifically."""
        df = pd.DataFrame({"email": ["valid@test.com", "invalid-email", "another@valid.com", "bad@"]})

        rules = {
            "email": {
                "required": True,
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            }
        }

        state = ProcessorState(aligned_df=df, program_id="test_program", core_id="test_core")

        mock_schema_collector.get_validation_rules.return_value = rules

        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})
        errors = state.combined_results.validation_results.validation_results

        # Should find INVALID_PATTERN errors for invalid emails
        pattern_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_PATTERN]
        assert len(pattern_errors) == 2

        # Verify error details
        invalid_emails = [error.current_value for error in pattern_errors]
        assert "invalid-email" in invalid_emails
        assert "bad@" in invalid_emails

    @pytest.mark.asyncio
    async def test_no_validation_errors(self, validation_node, mock_schema_collector):
        """Test validation with no errors found."""
        df = pd.DataFrame(
            {
                "name": ["John Doe", "Jane Smith"],
                "status": ["active", "inactive"],
                "email": ["john@test.com", "jane@test.com"],
            }
        )

        rules = {
            "name": {"required": True, "pattern": r"^[A-Za-z\s]+$"},
            "status": {"required": True, "options": ["active", "inactive", "pending"]},
            "email": {
                "required": True,
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
        }

        state = ProcessorState(aligned_df=df, program_id="test_program", core_id="test_core")

        mock_schema_collector.get_validation_rules.return_value = rules

        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})
        validation_results = state.combined_results.validation_results

        # Should find no errors
        assert len(validation_results.validation_results) == 0
        assert validation_results.summary.total_errors == 0
        assert validation_results.summary.total_rows == 2

        # All error type counts should be zero
        for count in validation_results.summary.error_types.values():
            assert count == 0

    def test_create_validation_results(self, validation_node):
        """Test creation of ValidationResults object."""
        errors = [
            ValidationErrorDetail(
                row=1,
                column="test_col",
                current_value="test",
                error_type=ValidationErrorType.REQUIRED_VALUE,
            ),
            ValidationErrorDetail(
                row=2,
                column="test_col2",
                current_value="test2",
                error_type=ValidationErrorType.INVALID_OPTION,
                valid_options=["option1", "option2"],
            ),
            ValidationErrorDetail(
                row=3,
                column="test_col3",
                current_value="test3",
                error_type=ValidationErrorType.INVALID_PATTERN,
            ),
        ]

        results = validation_node._create_validation_results(errors, 10, 3)

        assert results.summary.total_rows == 10
        assert results.summary.total_errors == 3
        assert results.summary.error_types[ValidationErrorType.REQUIRED_VALUE] == 1
        assert results.summary.error_types[ValidationErrorType.INVALID_OPTION] == 1
        assert results.summary.error_types[ValidationErrorType.INVALID_PATTERN] == 1
        assert results.summary.columns_validated == 3
        assert len(results.validation_results) == 3

    @pytest.mark.asyncio
    async def test_session_manager_integration(
        self,
        validation_node,
        mock_schema_collector,
        valid_state,
        sample_validation_rules,
    ):
        """Test session manager integration for state persistence."""
        # Create mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.save_data = AsyncMock()
        mock_session_manager.get_data = AsyncMock(return_value=None)  # No cached data

        # Attach session manager to node
        validation_node.session_manager = mock_session_manager

        # Setup mocks
        mock_schema_collector.get_validation_rules.return_value = sample_validation_rules

        # Execute validation
        result = await validation_node.invoke_async(
            task="validation_task", invocation_state={"processor_state": valid_state}
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify session manager was called for state persistence
        assert mock_session_manager.save_data.call_count >= 2  # At least start and complete checkpoints

        # Verify specific checkpoint calls
        call_args_list = [call[0] for call in mock_session_manager.save_data.call_args_list]
        checkpoint_keys = [args[0] for args in call_args_list]

        assert any("validation_start" in key for key in checkpoint_keys)
        assert any("validation_complete" in key for key in checkpoint_keys)

    @pytest.mark.asyncio
    async def test_validation_rules_caching_with_session_manager(
        self,
        validation_node,
        mock_schema_collector,
        valid_state,
        sample_validation_rules,
    ):
        """Test validation rules caching functionality with session manager."""
        # Create mock session manager with cached validation rules
        mock_session_manager = AsyncMock()
        mock_session_manager.get_data = AsyncMock()
        mock_session_manager.save_data = AsyncMock()

        # Setup cache responses
        cache_key = "test_program_test_core"
        mock_session_manager.get_data.side_effect = lambda key: {
            f"validation_rules_{cache_key}": sample_validation_rules
        }.get(key, None)

        # Attach session manager to node
        validation_node.session_manager = mock_session_manager

        # Execute validation
        result = await validation_node.invoke_async(
            task="validation_task", invocation_state={"processor_state": valid_state}
        )

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify schema collector was NOT called (cache hit)
        mock_schema_collector.get_validation_rules.assert_not_called()

        # Verify session manager was called for cache lookup
        expected_cache_call = f"validation_rules_{cache_key}"
        get_data_calls = [call[0][0] for call in mock_session_manager.get_data.call_args_list]
        assert expected_cache_call in get_data_calls

    @pytest.mark.asyncio
    async def test_session_cleanup(self, validation_node):
        """Test session data cleanup functionality."""
        # Create mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.delete_data = AsyncMock()

        # Attach session manager to node
        validation_node.session_manager = mock_session_manager

        # Execute cleanup
        await validation_node.cleanup_session_data()

        # Verify cleanup calls
        assert mock_session_manager.delete_data.call_count >= 2

        # Verify specific cleanup keys
        call_args_list = [call[0][0] for call in mock_session_manager.delete_data.call_args_list]
        expected_keys = ["validation_start", "validation_complete"]

        for expected_key in expected_keys:
            assert expected_key in call_args_list

    @pytest.mark.asyncio
    async def test_session_manager_error_handling(
        self,
        validation_node,
        mock_schema_collector,
        valid_state,
        sample_validation_rules,
    ):
        """Test graceful handling of session manager errors."""
        # Create mock session manager that raises errors
        mock_session_manager = AsyncMock()
        mock_session_manager.save_data = AsyncMock(side_effect=Exception("Session error"))
        mock_session_manager.get_data = AsyncMock(side_effect=Exception("Session error"))

        # Attach session manager to node
        validation_node.session_manager = mock_session_manager

        # Setup mocks
        mock_schema_collector.get_validation_rules.return_value = sample_validation_rules

        # Execute validation - should still succeed despite session errors
        result = await validation_node.invoke_async(
            task="validation_task", invocation_state={"processor_state": valid_state}
        )

        # Verify successful result (session errors should not fail processing)
        assert result.status.name == "COMPLETED"

        # Verify schema collector was called (no cache due to errors)
        mock_schema_collector.get_validation_rules.assert_called_once()

    @pytest.mark.asyncio
    async def test_combined_results_population(self, validation_node, mock_schema_collector, sample_validation_rules):
        """Test that ValidationNode properly populates CombinedResults.validation_results."""
        # Create test data
        df = pd.DataFrame(
            {
                "name": ["John Doe", "", "Jane Smith"],
                "status": ["active", "invalid", "inactive"],
            }
        )

        state = ProcessorState(
            aligned_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Pre-populate combined_results with schema alignment results to simulate schema alignment node
        from metadata_harmonization_processor.models.combined_results import (
            CombinedResults,
        )
        from metadata_harmonization_processor.models.schema_alignment_results import (
            SchemaAlignmentResults,
            SchemaAlignmentResultsSummary,
        )

        schema_alignment_results = SchemaAlignmentResults(
            schema_alignment_results=[],
            summary=SchemaAlignmentResultsSummary(
                job_id="test_job",
                version=1,
                original_data_csv="test,data",
                aligned_data_csv="test,data",
                total_changes=0,
                rows_original=3,
                rows_aligned=3,
            ),
        )

        state.combined_results = CombinedResults(schema_alignment_results=schema_alignment_results)

        # Setup mock
        mock_schema_collector.get_validation_rules.return_value = sample_validation_rules

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify combined_results structure
        assert state.combined_results is not None
        assert state.combined_results.has_validation_results()
        assert state.combined_results.has_schema_alignment_results()

        # Verify validation results were populated correctly
        validation_results = state.combined_results.validation_results
        assert validation_results is not None
        assert validation_results.summary.total_rows == 3
        assert len(validation_results.validation_results) > 0  # Should have some errors

        # Verify schema alignment results were preserved
        assert state.combined_results.schema_alignment_results is not None
        assert state.combined_results.schema_alignment_results.summary.job_id == "test_job"

    @pytest.mark.asyncio
    async def test_combined_results_initialization_when_missing(
        self, validation_node, mock_schema_collector, sample_validation_rules
    ):
        """Test that ValidationNode initializes CombinedResults when it doesn't exist."""
        # Create test data without combined_results
        df = pd.DataFrame({"name": ["John Doe", "Jane Smith"], "status": ["active", "inactive"]})

        state = ProcessorState(
            aligned_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Ensure combined_results is None
        assert state.combined_results is None

        # Setup mock
        mock_schema_collector.get_validation_rules.return_value = sample_validation_rules

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Verify combined_results was initialized
        assert state.combined_results is not None
        assert state.combined_results.has_validation_results()
        assert (
            not state.combined_results.has_schema_alignment_results()
        )  # Should be None since not set by schema alignment

        # Verify validation results were populated correctly
        validation_results = state.combined_results.validation_results
        assert validation_results is not None
        assert validation_results.summary.total_rows == 2

    @pytest.mark.asyncio
    async def test_custom_error_messages_extraction(
        self,
        validation_node,
        mock_schema_collector,
        validation_rules_with_custom_messages,
        sample_dataframe_with_custom_errors,
    ):
        """Test extraction and usage of custom error messages from schema."""
        # Setup mock
        mock_schema_collector.get_validation_rules.return_value = validation_rules_with_custom_messages

        state = ProcessorState(
            aligned_df=sample_dataframe_with_custom_errors,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Get validation errors
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have multiple errors with custom messages
        assert len(errors) > 0

        # Check for custom error messages in enum validation errors
        enum_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_OPTION]
        assert len(enum_errors) > 0

        # Find library_strategy enum error
        library_strategy_error = next(
            (e for e in enum_errors if e.column == "library_strategy" and e.current_value == "Invalid"),
            None,
        )
        assert library_strategy_error is not None
        assert (
            library_strategy_error.error_message
            == 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
        )
        assert library_strategy_error.schema_field_name == "library_strategy"

        # Find submitter_state enum error
        submitter_state_error = next(
            (e for e in enum_errors if e.column == "submitter_state" and e.current_value == "XX"),
            None,
        )
        assert submitter_state_error is not None
        assert (
            submitter_state_error.error_message
            == "submitter_state is a required field and must be formatted as the two-letter State abbreviation"
        )
        assert submitter_state_error.schema_field_name == "submitter_state"

        # Check for custom error messages in pattern validation errors
        pattern_errors = [e for e in errors if e.error_type == ValidationErrorType.INVALID_PATTERN]
        assert len(pattern_errors) > 0

        # Find sequence_id pattern error
        sequence_id_error = next(
            (e for e in pattern_errors if e.column == "sequence_id" and e.current_value == "invalid-format"),
            None,
        )
        assert sequence_id_error is not None
        assert (
            sequence_id_error.error_message == "sequence_id is a required field that must follow the proper formatting"
        )
        assert sequence_id_error.schema_field_name == "sequence_id"

        # Find CSID pattern error
        csid_error = next(
            (e for e in pattern_errors if e.column == "CSID" and e.current_value == "123"),
            None,
        )
        assert csid_error is not None
        assert (
            csid_error.error_message
            == "CSID is a required field and must be a ten-digit numerical string with no special characters"
        )
        assert csid_error.schema_field_name == "CSID"

    @pytest.mark.asyncio
    async def test_custom_error_messages_required_fields(self, validation_node, mock_schema_collector):
        """Test custom error messages for required field validation."""
        # Create DataFrame with empty required fields
        df = pd.DataFrame(
            {
                "library_strategy": ["", "Amplicon"],
                "sequence_id": ["AB12-CD34-Cx1-A", ""],
            }
        )

        rules = {
            "library_strategy": {
                "required": True,
                "options": ["Amplicon"],
                "error_message": {"enum": 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'},
            },
            "sequence_id": {
                "required": True,
                "pattern": r"^[A-Za-z]{2}[0-9]{2}-[A-Za-z]{2}[A-Za-z0-9]{2}[0-9]{2}-Cx[0-9]-[A-Za-z]$",
                "error_message": {"regex": "sequence_id is a required field that must follow the proper formatting"},
            },
        }

        mock_schema_collector.get_validation_rules.return_value = rules

        state = ProcessorState(
            aligned_df=df,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Execute validation
        await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Get validation errors
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have required field errors with custom messages
        required_errors = [e for e in errors if e.error_type == ValidationErrorType.REQUIRED_VALUE]
        assert len(required_errors) == 2

        # Check library_strategy required error
        library_strategy_error = next((e for e in required_errors if e.column == "library_strategy"), None)
        assert library_strategy_error is not None
        assert (
            library_strategy_error.error_message
            == 'library_strategy is a required field. Valid input(s) are: ["Amplicon"]'
        )
        assert library_strategy_error.schema_field_name == "library_strategy"

        # Check sequence_id required error - should use enum message since it has options
        sequence_id_error = next((e for e in required_errors if e.column == "sequence_id"), None)
        assert sequence_id_error is not None
        # For required fields, we try enum message first, then regex message
        assert (
            sequence_id_error.error_message == "sequence_id is a required field that must follow the proper formatting"
        )
        assert sequence_id_error.schema_field_name == "sequence_id"

    def test_extract_error_messages_dict_format(self, validation_node):
        """Test extraction of error messages in dictionary format."""
        rules = {
            "error_message": {
                "enum": "Custom enum error message",
                "pattern": "Custom pattern error message",
                "regex": "Custom regex error message",
            }
        }

        error_messages = validation_node._extract_error_messages(rules)

        assert len(error_messages) == 3
        assert error_messages["enum"] == "Custom enum error message"
        assert error_messages["pattern"] == "Custom pattern error message"
        assert error_messages["regex"] == "Custom regex error message"

    def test_extract_error_messages_string_format(self, validation_node):
        """Test extraction of error messages in string format."""
        rules = {"error_message": "General custom error message"}

        error_messages = validation_node._extract_error_messages(rules)

        assert len(error_messages) == 1
        assert error_messages["general"] == "General custom error message"

    def test_extract_error_messages_no_messages(self, validation_node):
        """Test extraction when no error messages are present."""
        rules = {"required": True, "options": ["option1", "option2"]}

        error_messages = validation_node._extract_error_messages(rules)

        assert len(error_messages) == 0

    def test_extract_error_messages_invalid_format(self, validation_node):
        """Test extraction with invalid error message format."""
        rules = {
            "error_message": {
                "enum": 123,  # Invalid: should be string
                "pattern": "Valid pattern message",
            }
        }

        error_messages = validation_node._extract_error_messages(rules)

        # Should only extract valid string messages
        assert len(error_messages) == 1
        assert error_messages["pattern"] == "Valid pattern message"
        assert "enum" not in error_messages

    @pytest.mark.asyncio
    async def test_backward_compatibility_without_custom_messages(
        self,
        validation_node,
        mock_schema_collector,
        sample_validation_rules,
        sample_aligned_dataframe,
    ):
        """Test that validation works correctly without custom error messages (backward compatibility)."""
        # Use original validation rules without custom error messages
        mock_schema_collector.get_validation_rules.return_value = sample_validation_rules

        state = ProcessorState(
            aligned_df=sample_aligned_dataframe,
            program_id="test_program",
            core_id="test_core",
            job_id="test_job",
        )

        # Execute validation
        result = await validation_node.invoke_async(task="validation_task", invocation_state={"processor_state": state})

        # Verify successful result
        assert result.status.name == "COMPLETED"

        # Get validation errors
        validation_results = state.combined_results.validation_results
        errors = validation_results.validation_results

        # Should have errors but without custom messages
        assert len(errors) > 0

        # All errors should have None for error_message and schema_field_name
        for error in errors:
            assert error.error_message is None
            assert error.schema_field_name == error.column  # Should still have the column name
