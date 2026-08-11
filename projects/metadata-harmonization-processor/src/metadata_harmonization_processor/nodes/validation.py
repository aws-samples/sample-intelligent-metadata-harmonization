# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Validation node for metadata harmonization processing.

This module implements the ValidationNode class that handles schema validation
of aligned metadata, generating detailed validation results with error
categorization. It inherits from MultiAgentBase for AWS Strands integration
with proper session management.
"""

import re
from typing import Any, Dict, List

import pandas as pd
from loguru import logger
from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import ContentBlock, Message

from ..interfaces.schema_collector import SchemaCollector
from ..logging.error_context_builder import ErrorContextBuilder, safe_isoformat
from ..models.state import ProcessorState
from ..models.validation import (
    CorrectionNodeType,
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)


class ValidationError(Exception):
    """Exception raised when validation processing fails."""

    pass


class ValidationNode(MultiAgentBase):
    """
    MultiAgentBase node for validating aligned metadata against schema rules.

    This node performs comprehensive validation of the aligned DataFrame
    against schema validation rules, generating detailed error reports
    with categorized validation issues. It inherits from MultiAgentBase
    for AWS Strands session management and standardized result handling.
    """

    def __init__(self, schema_collector: SchemaCollector):
        """
        Initialize the validation node.

        Args:
            schema_collector: Implementation for retrieving schema information
        """
        super().__init__()
        self.schema_collector = schema_collector
        self._validation_rules_cache: Dict[str, Dict[str, Any]] = {}

    async def invoke_async(
        self,
        task: str | list[ContentBlock],
        invocation_state: dict[str, Any] | None = None,
        **kwargs,
    ) -> MultiAgentResult:
        """
        Process validation using MultiAgentBase framework.

        Args:
            task: Task content (string or ContentBlock list)
            invocation_state: Optional invocation state dictionary containing ProcessorState
            **kwargs: Additional keyword arguments (unused)

        Returns:
            MultiAgentResult with validation_results in ProcessorState
        """
        # Get ProcessorState from invocation_state
        if not invocation_state or "processor_state" not in invocation_state:
            error_msg = "ProcessorState must be provided in invocation_state"
            logger.error(f"{error_msg} - validation_error: missing_processor_state")
            return MultiAgentResult(
                status=Status.FAILED,
                results={"validation": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        state = invocation_state["processor_state"]

        # Validate input state
        try:
            self._validate_input_state(state)
        except ValidationError as e:
            logger.error(f"Input validation failed: {str(e)}")
            return MultiAgentResult(
                status=Status.FAILED,
                results={"validation": NodeResult(result=e, status=Status.FAILED)},
            )

        try:
            # Update processing stage
            state.set_current_stage("validation")

            # Save initial state to session
            await self._save_state_to_session("validation_start", state)

            # Get validation rules from schema with caching
            logger.debug(
                f"Retrieving validation rules for program_id={state.program_id}, core_id={state.core_id} - operation: validation_rules_retrieval"
            )

            validation_rules = await self._get_cached_validation_rules(state.program_id, state.core_id)

            # Perform validation with enhanced logging
            columns_with_rules = list(validation_rules.keys()) if validation_rules else []
            logger.info(
                f"Starting validation of {len(state.aligned_df)} rows against {len(validation_rules)} column rules - columns_with_rules={len(columns_with_rules)}, total_columns={len(state.aligned_df.columns)}"
            )

            validation_errors, columns_validated = await self._validate_dataframe_with_logging(
                state.aligned_df, validation_rules, state
            )

            # Create validation results
            validation_results = self._create_validation_results(
                validation_errors, len(state.aligned_df), columns_validated
            )

            # Ensure combined_results exists (should be initialized by schema alignment node)
            if state.combined_results is None:
                from ..models.combined_results import CombinedResults

                state.combined_results = CombinedResults()
                logger.info(
                    "Initialized CombinedResults in validation node (schema alignment node should have done this) - operation: combined_results_initialization"
                )

            # Store validation results in combined_results instead of state.validation_results
            state.combined_results.validation_results = validation_results
            logger.info(
                f"Stored validation results in combined_results: {len(validation_errors)} errors found - total_errors: {len(validation_errors)}, total_rows: {len(state.aligned_df)}, has_schema_alignment_results: {state.combined_results.has_schema_alignment_results()}"
            )

            # Save intermediate state to session
            await self._save_state_to_session("validation_complete", state)

            # Log completion with appropriate level based on errors found
            if len(validation_errors) > 0:
                logger.warning(
                    f"Validation completed. Found {len(validation_errors)} errors in {len(state.aligned_df)} rows"
                )
            else:
                logger.info(f"Validation completed successfully. No errors found in {len(state.aligned_df)} rows")

            # Create success AgentResult with validation summary
            success_message: Message = {
                "content": [
                    {
                        "text": f"Validation completed. Found {len(validation_errors)} errors in {len(state.aligned_df)} rows"
                    }
                ]
            }
            agent_result = AgentResult(
                stop_reason="end_turn",
                message=success_message,
                metrics=EventLoopMetrics(),
                state={
                    "total_errors": len(validation_errors),
                    "total_rows": len(state.aligned_df),
                },
            )

            return MultiAgentResult(
                status=Status.COMPLETED,
                results={"validation": NodeResult(result=agent_result, status=Status.COMPLETED)},
            )

        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            logger.error(error_msg)

            # Enhanced error logging
            error_context = ErrorContextBuilder.build_validation_context(state, e, {"node": "validation"})
            logger.error(f"Validation node error: {str(e)} - error_context={error_context}")

            # Return failed result with enhanced error information
            enhanced_error = ValidationError(f"{error_msg}. Check logs for detailed error context.")
            return MultiAgentResult(
                status=Status.FAILED,
                results={"validation": NodeResult(result=enhanced_error, status=Status.FAILED)},
            )

    def _validate_input_state(self, state: ProcessorState) -> None:
        """
        Validate that the input state contains required data.

        Args:
            state: ProcessorState to validate

        Raises:
            ValidationError: If required data is missing
        """
        if not state.has_aligned_data():
            raise ValidationError("Input state must contain aligned_df")

        if not state.has_schema_ids():
            raise ValidationError("Input state must contain program_id and core_id")

    async def _validate_dataframe_with_logging(
        self, df: pd.DataFrame, validation_rules: Dict[str, Any], state: ProcessorState
    ) -> tuple[List[ValidationErrorDetail], int]:
        """
        Validate DataFrame with enhanced logging and progress tracking.

        Args:
            df: Aligned DataFrame to validate
            validation_rules: Dictionary of validation rules by column
            state: Current processor state for logging context

        Returns:
            Tuple of (List of ValidationErrorDetail objects, number of columns validated)
        """
        logger.debug(
            f"Starting DataFrame validation: {len(df)} rows, {len(df.columns)} columns - dataframe_shape: {df.shape}, columns_with_rules: {list(validation_rules.keys()) if validation_rules else []}, total_validation_rules: {len(validation_rules) if validation_rules else 0}"
        )

        errors = []
        columns_processed = 0

        for column in df.columns:
            if column in validation_rules:
                column_rules = validation_rules[column]

                logger.debug(
                    f"Validating column: {column} - rules: {column_rules}, column_dtype: {str(df[column].dtype)}, null_count: {df[column].isnull().sum()}"
                )

                column_errors = self._validate_column(df, column, column_rules)
                errors.extend(column_errors)

                columns_processed += 1

                if column_errors:
                    # Format sample errors for better readability
                    sample_lines = []
                    for err in column_errors[:3]:
                        value_preview = str(err.current_value)[:50]  # Truncate long values
                        sample_lines.append(f"    • Row {err.row}: {err.error_type.value} - '{value_preview}'")

                    sample_text = "\n".join(sample_lines)
                    logger.warning(
                        f"Column '{column}' validation: {len(column_errors)} errors found\n"
                        f"  Sample errors (first {min(3, len(column_errors))}):\n{sample_text}"
                    )

                # Progress tracking removed (previously used NodeExecutionTracker)

        # Log final validation summary
        error_summary = self._create_error_summary(errors)
        # Calculate error rate as percentage of total validation points (rows × columns)
        total_validation_points = len(df) * columns_processed
        error_rate = (len(errors) / total_validation_points * 100) if total_validation_points > 0 else 0

        if len(errors) == 0:
            logger.info(f"Validation completed: No errors found in {len(df)} rows across {columns_processed} columns")
        else:
            # Format a readable multi-line summary
            summary_lines = [
                "═" * 60,
                "VALIDATION SUMMARY",
                "═" * 60,
                f"Total Errors: {len(errors)} ({error_rate:.1f}% error rate)",
                f"Columns Validated: {columns_processed}",
                "",
            ]

            # Error breakdown by type
            if error_summary.get("by_type"):
                summary_lines.append("Error Breakdown by Type:")
                for error_type, count in error_summary["by_type"].items():
                    percentage = (count / len(errors)) * 100 if len(errors) > 0 else 0
                    summary_lines.append(f"  • {error_type}: {count} errors ({percentage:.1f}%)")
                summary_lines.append("")

            # Most problematic columns (only show columns with >10 errors)
            if error_summary.get("by_column"):
                problematic_columns = [(col, count) for col, count in error_summary["by_column"].items() if count > 10]
                problematic_columns.sort(key=lambda x: x[1], reverse=True)

                if problematic_columns:
                    summary_lines.append("Most Problematic Columns (>10 errors):")

                    # Group columns with same error count
                    from itertools import groupby

                    for count, group in groupby(problematic_columns, key=lambda x: x[1]):
                        cols = [col for col, _ in group]
                        if len(cols) > 5:
                            summary_lines.append(
                                f"  • {len(cols)} columns with {count} errors each: {', '.join(cols[:3])}, ..."
                            )
                        else:
                            for col in cols:
                                summary_lines.append(f"  • {col}: {count} errors")
                    summary_lines.append("")

            summary_lines.append("═" * 60)

            # Log each line separately for better formatting
            for line in summary_lines:
                logger.warning(line)

        return errors, columns_processed

    def _validate_column(self, df: pd.DataFrame, column: str, rules: Dict[str, Any]) -> List[ValidationErrorDetail]:
        """
        Validate a single column against its rules.

        Args:
            df: DataFrame containing the column
            column: Column name to validate
            rules: Validation rules for this column

        Returns:
            List of ValidationErrorDetail objects for this column
        """
        errors = []

        # Extract custom error messages from schema
        error_messages = self._extract_error_messages(rules)

        for row_idx, value in enumerate(df[column]):
            # Convert value to string for consistent processing
            str_value = str(value) if pd.notna(value) else ""

            # Add 1 to row_idx so first data row is row 1, not 0
            display_row = row_idx + 1

            # Check required field validation
            if rules.get("required", False):
                if pd.isna(value) or str_value.strip() == "":
                    # Include valid options for required fields that have enum constraints
                    field_valid_options = rules.get("options")

                    # Get custom error message for required field validation
                    # Try different message types based on what validation rules exist
                    custom_error_message = None
                    if field_valid_options:
                        # Field has options, use enum message
                        custom_error_message = error_messages.get("enum")
                    else:
                        # Field doesn't have options, try pattern/regex message
                        custom_error_message = error_messages.get("regex") or error_messages.get("pattern")

                    # Fallback to general or required message
                    if not custom_error_message:
                        custom_error_message = error_messages.get("required") or error_messages.get("general")

                    errors.append(
                        ValidationErrorDetail(
                            row=display_row,
                            column=column,
                            current_value=str_value,
                            valid_options=field_valid_options,
                            recommended_value=None,
                            error_type=ValidationErrorType.REQUIRED_VALUE,
                            error_message=custom_error_message,
                            schema_field_name=column,
                        )
                    )
                    continue  # Skip other validations for empty required fields

            # Skip validation for empty optional fields
            if pd.isna(value) or str_value.strip() == "":
                continue

            # Check valid options validation
            valid_options = rules.get("options")
            if valid_options and str_value not in valid_options:
                # Get custom error message for enum validation
                custom_error_message = error_messages.get("enum")

                # Auto-correct if only one valid option (trivial case)
                recommended_value = None
                if len(valid_options) == 1:
                    recommended_value = valid_options[0]

                errors.append(
                    ValidationErrorDetail(
                        row=display_row,
                        column=column,
                        current_value=str_value,
                        valid_options=valid_options,
                        recommended_value=recommended_value,
                        error_type=ValidationErrorType.INVALID_OPTION,
                        error_message=custom_error_message,
                        schema_field_name=column,
                        confidence_score=1.0 if recommended_value else None,
                        confidence_level="high" if recommended_value else None,
                        correction_node=(CorrectionNodeType.VALIDATION if recommended_value else None),
                    )
                )
                continue  # Skip pattern validation if option validation fails

            # Check pattern validation
            pattern = rules.get("pattern")
            if pattern and not self._validate_pattern(str_value, pattern):
                # Get custom error message for pattern validation
                custom_error_message = error_messages.get("pattern") or error_messages.get("regex")

                errors.append(
                    ValidationErrorDetail(
                        row=display_row,
                        column=column,
                        current_value=str_value,
                        valid_options=None,
                        recommended_value=None,
                        error_type=ValidationErrorType.INVALID_PATTERN,
                        error_message=custom_error_message,
                        schema_field_name=column,
                    )
                )

        return errors

    def _extract_error_messages(self, rules: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract custom error messages from schema validation rules.

        Args:
            rules: Validation rules dictionary for a field

        Returns:
            Dictionary mapping validation types to custom error messages
        """
        error_messages = {}

        # Extract error messages from the rules
        if "error_message" in rules:
            error_message_obj = rules["error_message"]

            # Handle different error message formats
            if isinstance(error_message_obj, dict):
                # Schema format: {"enum": "Custom message", "pattern": "Another message"}
                for validation_type, message in error_message_obj.items():
                    if isinstance(message, str):
                        error_messages[validation_type] = message
                        logger.debug(f"Extracted custom error message for {validation_type}: {message}")
            elif isinstance(error_message_obj, str):
                # Simple string format - use for all validation types
                error_messages["general"] = error_message_obj
                logger.debug(f"Extracted general custom error message: {error_message_obj}")

        if error_messages:
            logger.debug(f"Found {len(error_messages)} custom error messages in schema")

        return error_messages

    def _validate_pattern(self, value: str, pattern: str) -> bool:
        """
        Validate a value against a regex pattern.

        Args:
            value: Value to validate
            pattern: Regex pattern to match against

        Returns:
            True if value matches pattern, False otherwise
        """
        try:
            return bool(re.match(pattern, value))
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            return True  # Don't fail validation for invalid patterns

    def _create_validation_results(
        self,
        errors: List[ValidationErrorDetail],
        total_rows: int,
        columns_validated: int,
    ) -> ValidationResults:
        """
        Create ValidationResults object from error list.

        Args:
            errors: List of validation errors
            total_rows: Total number of rows processed
            columns_validated: Number of columns that were validated

        Returns:
            ValidationResults object with errors and summary
        """
        # Count errors by type
        error_type_counts = {
            ValidationErrorType.REQUIRED_VALUE: 0,
            ValidationErrorType.INVALID_OPTION: 0,
            ValidationErrorType.INVALID_PATTERN: 0,
        }

        for error in errors:
            error_type_counts[error.error_type] += 1

        # Create summary
        summary = ValidationResultsSummary(
            total_rows=total_rows,
            total_errors=len(errors),
            error_types=error_type_counts,
            columns_validated=columns_validated,
        )

        # Create complete results
        return ValidationResults(validation_results=errors, summary=summary)

    def _create_error_summary(self, errors: List[ValidationErrorDetail]) -> Dict[str, Any]:
        """
        Create a summary of validation errors for logging.

        Args:
            errors: List of validation errors

        Returns:
            Error summary dictionary
        """
        if not errors:
            return {"total": 0}

        # Group errors by type
        error_by_type = {}
        error_by_column = {}

        for error in errors:
            # By type
            error_type = error.error_type.value
            error_by_type[error_type] = error_by_type.get(error_type, 0) + 1

            # By column
            column = error.column
            error_by_column[column] = error_by_column.get(column, 0) + 1

        return {
            "total": len(errors),
            "by_type": error_by_type,
            "by_column": error_by_column,
            "most_common_type": (max(error_by_type.items(), key=lambda x: x[1])[0] if error_by_type else None),
            "most_problematic_column": (
                max(error_by_column.items(), key=lambda x: x[1])[0] if error_by_column else None
            ),
        }

    async def _save_state_to_session(self, checkpoint: str, state: ProcessorState) -> None:
        """
        Save processing state to session manager.

        Args:
            checkpoint: Checkpoint name for this state save
            state: ProcessorState to save
        """
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Create serializable state data
                state_data = {
                    "job_id": state.job_id,
                    "current_stage": state.current_stage,
                    "program_id": state.program_id,
                    "core_id": state.core_id,
                    "processing_start_time": safe_isoformat(state.processing_start_time),
                    "aligned_shape": (state.aligned_df.shape if state.has_aligned_data() else None),
                    "validation_error_count": (
                        len(state.combined_results.validation_results.validation_results)
                        if state.has_validation_results()
                        else None
                    ),
                    "validation_summary": (
                        state.combined_results.validation_results.summary.model_dump()
                        if state.has_validation_results()
                        else None
                    ),
                    "has_combined_results": state.combined_results is not None,
                    "has_schema_alignment_results": state.has_schema_alignment_results(),
                }

                # Use session manager's actual method (may vary by implementation)
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data(f"validation_{checkpoint}", state_data)
                elif hasattr(self.session_manager, "save"):
                    await self.session_manager.save(f"validation_{checkpoint}", state_data)
                else:
                    logger.debug(f"Session manager {type(self.session_manager)} does not support data saving")
                logger.debug(f"Saved state to session at checkpoint: {checkpoint}")
        except Exception as e:
            logger.warning(f"Failed to save state to session at {checkpoint}: {e}")

    async def _get_cached_validation_rules(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """
        Get validation rules with session-based caching.

        Args:
            program_id: Schema program identifier
            core_id: Schema core identifier

        Returns:
            Validation rules dictionary
        """
        cache_key = f"{program_id}_{core_id}"

        # Check local cache first
        if cache_key in self._validation_rules_cache:
            logger.debug(f"Validation rules cache hit (local) for {cache_key}")
            return self._validation_rules_cache[cache_key]

        # Check session cache
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Use session manager's actual method (may vary by implementation)
                if hasattr(self.session_manager, "get_data"):
                    cached_rules = await self.session_manager.get_data(f"validation_rules_{cache_key}")
                elif hasattr(self.session_manager, "get"):
                    cached_rules = await self.session_manager.get(f"validation_rules_{cache_key}")
                else:
                    cached_rules = None
                if cached_rules:
                    logger.debug(f"Validation rules cache hit (session) for {cache_key}")
                    self._validation_rules_cache[cache_key] = cached_rules
                    return cached_rules
        except Exception as e:
            logger.debug(f"Session cache lookup failed for validation rules {cache_key}: {e}")

        # Fetch from schema collector
        logger.debug(f"Fetching validation rules from collector for {cache_key}")
        validation_rules = await self.schema_collector.get_validation_rules(program_id, core_id)

        # Cache in both local and session
        self._validation_rules_cache[cache_key] = validation_rules
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Use session manager's actual method (may vary by implementation)
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data(f"validation_rules_{cache_key}", validation_rules)
                elif hasattr(self.session_manager, "save"):
                    await self.session_manager.save(f"validation_rules_{cache_key}", validation_rules)
                logger.debug(f"Cached validation rules in session for {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache validation rules in session for {cache_key}: {e}")

        return validation_rules

    async def cleanup_session_data(self) -> None:
        """
        Clean up session data for this node.
        """
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Clean up validation specific session data
                keys_to_clean = ["validation_start", "validation_complete"]

                for key in keys_to_clean:
                    try:
                        await self.session_manager.delete_data(key)
                    except Exception as e:
                        logger.debug(f"Failed to clean session key {key}: {e}")

                logger.debug("Validation session data cleaned up")
        except Exception as e:
            logger.warning(f"Error during validation session cleanup: {e}")
