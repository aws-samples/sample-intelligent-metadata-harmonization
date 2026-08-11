# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for pattern-based prediction node.

This module tests the pattern matching algorithms and heuristics used
for generating recommendations for INVALID_PATTERN and REQUIRED_VALUE errors,
and MultiAgentBase compatibility.
"""

from unittest.mock import patch

import pytest

# Import MultiAgentBase components for testing
from strands.multiagent.base import Status

from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.nodes.pattern_prediction import (
    PatternBasedPredictionNode,
)


class TestPatternBasedPredictionNode:
    """Test cases for PatternBasedPredictionNode class."""

    @pytest.fixture
    def prediction_node(self):
        """Create a PatternBasedPredictionNode instance for testing."""
        return PatternBasedPredictionNode()

    @pytest.fixture
    def sample_validation_results(self):
        """Create sample validation results for testing."""
        errors = [
            ValidationErrorDetail(
                row=1,
                column="birth_date",
                current_value="12/25/1990",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.INVALID_PATTERN,
            ),
            ValidationErrorDetail(
                row=2,
                column="phone_number",
                current_value="555-123-4567",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.INVALID_PATTERN,
            ),
            ValidationErrorDetail(
                row=3,
                column="status",
                current_value="",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.REQUIRED_VALUE,
            ),
            ValidationErrorDetail(
                row=4,
                column="category",
                current_value="invalid_option",
                valid_options=["option1", "option2", "option3"],
                recommended_value=None,
                error_type=ValidationErrorType.INVALID_OPTION,
            ),
        ]

        summary = ValidationResultsSummary(
            total_rows=4,
            total_errors=4,
            error_types={
                ValidationErrorType.INVALID_PATTERN: 2,
                ValidationErrorType.REQUIRED_VALUE: 1,
                ValidationErrorType.INVALID_OPTION: 1,
            },
            columns_validated=3,
        )

        return ValidationResults(validation_results=errors, summary=summary)

    @pytest.mark.asyncio
    async def test_invoke_async_processes_pattern_errors_only(self, prediction_node, sample_validation_results):
        """Test that invoke_async processes only INVALID_PATTERN and REQUIRED_VALUE errors."""
        # Create ProcessorState with validation results
        combined_results = CombinedResults(validation_results=sample_validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        # Execute prediction using MultiAgentBase interface
        result = await prediction_node.invoke_async(
            task="pattern_prediction_task", invocation_state={"processor_state": state}
        )

        # Verify MultiAgentResult structure
        assert result.status == Status.COMPLETED
        assert "pattern_prediction" in result.results
        assert result.results["pattern_prediction"].status == Status.COMPLETED

        # Verify state updates (state is modified in place)
        assert state.current_stage == "pattern_prediction"

        # Should process 3 errors (2 INVALID_PATTERN + 1 REQUIRED_VALUE)
        pattern_errors = [
            error
            for error in state.combined_results.validation_results.validation_results
            if error.error_type in [ValidationErrorType.INVALID_PATTERN, ValidationErrorType.REQUIRED_VALUE]
        ]

        assert len(pattern_errors) == 3

        # INVALID_OPTION error should remain unchanged
        invalid_option_error = next(
            error
            for error in state.combined_results.validation_results.validation_results
            if error.error_type == ValidationErrorType.INVALID_OPTION
        )
        assert invalid_option_error.recommended_value is None

    @pytest.mark.asyncio
    async def test_invoke_async_with_no_pattern_errors(self, prediction_node):
        """Test invoke_async with validation results containing no pattern-based errors."""
        errors = [
            ValidationErrorDetail(
                row=1,
                column="category",
                current_value="invalid_option",
                valid_options=["option1", "option2", "option3"],
                recommended_value=None,
                error_type=ValidationErrorType.INVALID_OPTION,
            )
        ]

        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
            columns_validated=1,
        )

        validation_results = ValidationResults(validation_results=errors, summary=summary)

        # Create ProcessorState with validation results
        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        # Execute prediction using MultiAgentBase interface
        result = await prediction_node.invoke_async(
            task="pattern_prediction_task", invocation_state={"processor_state": state}
        )

        # Verify MultiAgentResult structure
        assert result.status == Status.COMPLETED
        assert "pattern_prediction" in result.results
        assert result.results["pattern_prediction"].status == Status.COMPLETED

        # Verify state updates (state is modified in place)
        # Should return unchanged results
        assert state.combined_results.validation_results.validation_results[0].recommended_value is None

    @pytest.mark.asyncio
    async def test_invoke_async_handles_processing_errors_gracefully(self, prediction_node):
        """Test that invoke_async handles individual error processing failures gracefully."""
        errors = [
            ValidationErrorDetail(
                row=1,
                column="test_column",
                current_value="test_value",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.INVALID_PATTERN,
            )
        ]

        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            error_types={ValidationErrorType.INVALID_PATTERN: 1},
            columns_validated=1,
        )

        validation_results = ValidationResults(validation_results=errors, summary=summary)

        # Create ProcessorState with validation results
        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        # Mock _generate_recommendation to raise an exception
        with patch.object(
            prediction_node,
            "_generate_recommendation",
            side_effect=Exception("Test error"),
        ):
            result = await prediction_node.invoke_async(
                task="pattern_prediction_task",
                invocation_state={"processor_state": state},
            )

            # Should continue processing and return successful result without crashing
            assert result.status == Status.COMPLETED
            # Verify state updates (state is modified in place)
            assert state.combined_results.validation_results.validation_results[0].recommended_value is None

    def test_filter_pattern_errors(self, prediction_node, sample_validation_results):
        """Test filtering of pattern-based errors."""
        pattern_errors = prediction_node._filter_pattern_errors(sample_validation_results.validation_results)

        assert len(pattern_errors) == 3

        error_types = [error.error_type for error in pattern_errors]
        assert ValidationErrorType.INVALID_PATTERN in error_types
        assert ValidationErrorType.REQUIRED_VALUE in error_types
        assert ValidationErrorType.INVALID_OPTION not in error_types

    @pytest.mark.asyncio
    async def test_generate_recommendation_invalid_pattern(self, prediction_node):
        """Test recommendation generation for INVALID_PATTERN errors."""
        error = ValidationErrorDetail(
            row=1,
            column="birth_date",
            current_value="12/25/1990",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.INVALID_PATTERN,
        )

        recommendation = await prediction_node._generate_recommendation(error)

        # Should convert MM/DD/YYYY to YYYY-MM-DD format
        assert recommendation == "1990-12-25"

    @pytest.mark.asyncio
    async def test_generate_recommendation_required_value(self, prediction_node):
        """Test recommendation generation for REQUIRED_VALUE errors."""
        error = ValidationErrorDetail(
            row=1,
            column="status",
            current_value="",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.REQUIRED_VALUE,
        )

        recommendation = await prediction_node._generate_recommendation(error)

        # Should suggest 'active' for status fields
        assert recommendation == "active"

    @pytest.mark.asyncio
    async def test_generate_recommendation_unsupported_type(self, prediction_node):
        """Test recommendation generation for unsupported error types."""
        error = ValidationErrorDetail(
            row=1,
            column="category",
            current_value="invalid_option",
            valid_options=["option1", "option2", "option3"],
            recommended_value=None,
            error_type=ValidationErrorType.INVALID_OPTION,
        )

        recommendation = await prediction_node._generate_recommendation(error)

        # Should return None for unsupported types
        assert recommendation is None

    @pytest.mark.asyncio
    async def test_invoke_async_missing_validation_results(self, prediction_node):
        """Test invoke_async with ProcessorState missing validation results."""
        # Create state without validation results
        state = ProcessorState(job_id="test-job")

        # Execute prediction using MultiAgentBase interface
        result = await prediction_node.invoke_async(
            task="pattern_prediction_task", invocation_state={"processor_state": state}
        )

        # Should return failed result
        assert result.status == Status.FAILED
        assert "pattern_prediction" in result.results
        assert result.results["pattern_prediction"].status == Status.FAILED
        assert isinstance(result.results["pattern_prediction"].result, Exception)

    @pytest.mark.asyncio
    async def test_invoke_async_general_processing_error(self, prediction_node, sample_validation_results):
        """Test invoke_async handles general processing errors."""
        # Create state with validation results
        combined_results = CombinedResults(validation_results=sample_validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        # Mock _filter_pattern_errors to raise an exception
        with patch.object(
            prediction_node,
            "_filter_pattern_errors",
            side_effect=Exception("General processing error"),
        ):
            result = await prediction_node.invoke_async(
                task="pattern_prediction_task",
                invocation_state={"processor_state": state},
            )

            # Should return failed result
            assert result.status == Status.FAILED
            assert "pattern_prediction" in result.results
            assert result.results["pattern_prediction"].status == Status.FAILED
            assert isinstance(result.results["pattern_prediction"].result, Exception)


class TestInvalidPatternHandling:
    """Test cases for INVALID_PATTERN error handling."""

    @pytest.fixture
    def prediction_node(self):
        """Create a PatternBasedPredictionNode instance for testing."""
        return PatternBasedPredictionNode()

    def test_handle_invalid_pattern_date_correction(self, prediction_node):
        """Test date pattern correction."""
        error = ValidationErrorDetail(
            row=1,
            column="birth_date",
            current_value="12/25/1990",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.INVALID_PATTERN,
        )

        result = prediction_node._handle_invalid_pattern(error)
        assert result == "1990-12-25"

    def test_handle_invalid_pattern_numeric_correction(self, prediction_node):
        """Test numeric pattern correction."""
        error = ValidationErrorDetail(
            row=1,
            column="amount",
            current_value="$1,234.56",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.INVALID_PATTERN,
        )

        result = prediction_node._handle_invalid_pattern(error)
        assert result == "1234.56"

    def test_handle_invalid_pattern_case_correction(self, prediction_node):
        """Test case correction."""
        error = ValidationErrorDetail(
            row=1,
            column="name",
            current_value="john doe",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.INVALID_PATTERN,
        )

        result = prediction_node._handle_invalid_pattern(error)
        assert result == "John Doe"

    def test_handle_invalid_pattern_empty_value(self, prediction_node):
        """Test handling of empty values."""
        error = ValidationErrorDetail(
            row=1,
            column="test_field",
            current_value="",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.INVALID_PATTERN,
        )

        result = prediction_node._handle_invalid_pattern(error)
        assert result is None

    def test_handle_invalid_pattern_no_correction_possible(self, prediction_node):
        """Test handling when no correction is possible."""
        error = ValidationErrorDetail(
            row=1,
            column="complex_field",
            current_value="completely_invalid_data_123!@#",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.INVALID_PATTERN,
        )

        result = prediction_node._handle_invalid_pattern(error)
        assert result is None


class TestRequiredValueHandling:
    """Test cases for REQUIRED_VALUE error handling."""

    @pytest.fixture
    def prediction_node(self):
        """Create a PatternBasedPredictionNode instance for testing."""
        return PatternBasedPredictionNode()

    def test_handle_required_value_date_fields(self, prediction_node):
        """Test required value suggestions for date fields."""
        test_cases = [
            ("created_date", "date"),
            ("updated_time", "date"),
            ("modified_timestamp", "date"),
        ]

        for column_name, expected_type in test_cases:
            error = ValidationErrorDetail(
                row=1,
                column=column_name,
                current_value="",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )

            result = prediction_node._handle_required_value(error)

            # Should suggest current date in YYYY-MM-DD format
            assert result is not None
            assert len(result) == 10  # YYYY-MM-DD format
            assert result.count("-") == 2

    def test_handle_required_value_status_fields(self, prediction_node):
        """Test required value suggestions for status fields."""
        error = ValidationErrorDetail(
            row=1,
            column="status",
            current_value="",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.REQUIRED_VALUE,
        )

        result = prediction_node._handle_required_value(error)
        assert result == "active"

    def test_handle_required_value_boolean_fields(self, prediction_node):
        """Test required value suggestions for boolean-like fields."""
        test_cases = ["active", "enabled", "valid", "confirmed"]

        for column_name in test_cases:
            error = ValidationErrorDetail(
                row=1,
                column=column_name,
                current_value="",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )

            result = prediction_node._handle_required_value(error)
            assert result == "true"

    def test_handle_required_value_id_fields(self, prediction_node):
        """Test required value suggestions for ID fields."""
        test_cases = ["user_id", "record_id", "id"]

        for column_name in test_cases:
            error = ValidationErrorDetail(
                row=1,
                column=column_name,
                current_value="",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )

            result = prediction_node._handle_required_value(error)
            assert result is None

    def test_handle_required_value_name_fields(self, prediction_node):
        """Test required value suggestions for name fields."""
        error = ValidationErrorDetail(
            row=1,
            column="full_name",
            current_value="",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.REQUIRED_VALUE,
        )

        result = prediction_node._handle_required_value(error)
        assert result is None

    def test_handle_required_value_numeric_fields(self, prediction_node):
        """Test required value suggestions for numeric fields."""
        test_cases = ["count", "number", "quantity", "amount"]

        for column_name in test_cases:
            error = ValidationErrorDetail(
                row=1,
                column=column_name,
                current_value="",
                valid_options=None,
                recommended_value=None,
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )

            result = prediction_node._handle_required_value(error)
            assert result == "0"

    def test_handle_required_value_default_fallback(self, prediction_node):
        """Test default fallback for unknown field types."""
        error = ValidationErrorDetail(
            row=1,
            column="unknown_field_type",
            current_value="",
            valid_options=None,
            recommended_value=None,
            error_type=ValidationErrorType.REQUIRED_VALUE,
        )

        result = prediction_node._handle_required_value(error)
        assert result is None


class TestDateCorrection:
    """Test cases for date correction algorithms."""

    @pytest.fixture
    def prediction_node(self):
        """Create a PatternBasedPredictionNode instance for testing."""
        return PatternBasedPredictionNode()

    def test_try_date_correction_mm_dd_yyyy(self, prediction_node):
        """Test MM/DD/YYYY date format correction."""
        test_cases = [
            ("12/25/1990", "1990-12-25"),
            ("1/5/2000", "2000-01-05"),
            ("12-25-1990", "1990-12-25"),
        ]

        for input_date, expected_output in test_cases:
            result = prediction_node._try_date_correction(input_date)
            assert result == expected_output

    def test_try_date_correction_yyyy_mm_dd(self, prediction_node):
        """Test YYYY/MM/DD date format correction."""
        test_cases = [
            ("1990/12/25", "1990-12-25"),
            ("2000/1/5", "2000-01-05"),
            ("1990-12-25", "1990-12-25"),
        ]

        for input_date, expected_output in test_cases:
            result = prediction_node._try_date_correction(input_date)
            assert result == expected_output

    def test_try_date_correction_mm_dd_yy(self, prediction_node):
        """Test MM/DD/YY date format correction (assumes 20XX)."""
        test_cases = [("12/25/90", "2090-12-25"), ("1/5/00", "2000-01-05")]

        for input_date, expected_output in test_cases:
            result = prediction_node._try_date_correction(input_date)
            assert result == expected_output

    def test_try_date_correction_invalid_dates(self, prediction_node):
        """Test handling of invalid date formats."""
        invalid_dates = [
            "not_a_date",
            "13/45/1990",  # Invalid month/day
            "12/25",  # Missing year
            "1990",  # Only year
            "",  # Empty string
        ]

        for invalid_date in invalid_dates:
            result = prediction_node._try_date_correction(invalid_date)
            assert result is None


class TestNumericCorrection:
    """Test cases for numeric correction algorithms."""

    @pytest.fixture
    def prediction_node(self):
        """Create a PatternBasedPredictionNode instance for testing."""
        return PatternBasedPredictionNode()

    def test_try_numeric_correction_currency(self, prediction_node):
        """Test currency format correction."""
        test_cases = [
            ("$1,234.56", "1234.56"),
            ("$1234", "1234"),
            ("1,234.56", "1234.56"),
        ]

        for input_value, expected_output in test_cases:
            result = prediction_node._try_numeric_correction(input_value)
            assert result == expected_output

    def test_try_numeric_correction_negative_numbers(self, prediction_node):
        """Test negative number correction."""
        test_cases = [
            ("-$1,234.56", "-1234.56"),
            ("-1,234", "-1234"),
            ("($1,234.56)", "1234.56"),  # Parentheses removed
        ]

        for input_value, expected_output in test_cases:
            result = prediction_node._try_numeric_correction(input_value)
            assert result == expected_output

    def test_try_numeric_correction_multiple_decimals(self, prediction_node):
        """Test handling of multiple decimal points."""
        result = prediction_node._try_numeric_correction("1.234.56")
        assert result == "1.23456"

    def test_try_numeric_correction_invalid_numbers(self, prediction_node):
        """Test handling of invalid numeric formats."""
        invalid_numbers = ["not_a_number", "abc123", "", "..."]

        for invalid_number in invalid_numbers:
            result = prediction_node._try_numeric_correction(invalid_number)
            assert result is None


class TestFormatCorrection:
    """Test cases for format correction algorithms."""

    @pytest.fixture
    def prediction_node(self):
        """Create a PatternBasedPredictionNode instance for testing."""
        return PatternBasedPredictionNode()

    def test_try_format_correction_email(self, prediction_node):
        """Test email format correction."""
        test_cases = [
            ("John.Doe@Example.COM", "john.doe@example.com"),
            ("  user@domain.com  ", "user@domain.com"),
        ]

        for input_email, expected_output in test_cases:
            result = prediction_node._try_format_correction(input_email)
            assert result == expected_output

    def test_try_format_correction_phone(self, prediction_node):
        """Test phone number format correction."""
        test_cases = [
            ("5551234567", "(555) 123-4567"),
            ("15551234567", "1-(555) 123-4567"),
            ("555.123.4567", "(555) 123-4567"),
        ]

        for input_phone, expected_output in test_cases:
            result = prediction_node._try_format_correction(input_phone)
            assert result == expected_output

    def test_try_format_correction_url(self, prediction_node):
        """Test URL format correction."""
        test_cases = [
            ("www.example.com", "https://www.example.com"),
            ("example.com", "https://www.example.com"),
            ("HTTP://EXAMPLE.COM", "http://example.com"),
        ]

        for input_url, expected_output in test_cases:
            result = prediction_node._try_format_correction(input_url)
            assert result == expected_output

    def test_try_format_correction_no_match(self, prediction_node):
        """Test format correction when no pattern matches."""
        result = prediction_node._try_format_correction("random_text_123")
        assert result is None


class TestCaseCorrection:
    """Test cases for case correction algorithms."""

    @pytest.fixture
    def prediction_node(self):
        """Create a PatternBasedPredictionNode instance for testing."""
        return PatternBasedPredictionNode()

    def test_try_case_correction_names(self, prediction_node):
        """Test case correction for names."""
        test_cases = [
            ("john doe", "John Doe"),
            ("JANE SMITH", "Jane Smith"),
            ("mary-jane watson", "Mary-Jane Watson"),
            ("o'connor", "O'Connor"),
        ]

        for input_name, expected_output in test_cases:
            result = prediction_node._try_case_correction(input_name)
            assert result == expected_output

    def test_try_case_correction_mixed_case(self, prediction_node):
        """Test that mixed case names are not changed."""
        mixed_case_names = ["John Doe", "Mary-Jane Watson", "O'Connor"]

        for name in mixed_case_names:
            result = prediction_node._try_case_correction(name)
            assert result is None

    def test_try_case_correction_non_names(self, prediction_node):
        """Test that non-name strings are not changed."""
        non_names = ["abc123", "test@example.com", "123-456-7890"]

        for non_name in non_names:
            result = prediction_node._try_case_correction(non_name)
            assert result is None
