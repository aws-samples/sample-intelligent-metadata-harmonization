# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Schema alignment node for metadata harmonization processing.

This module implements the SchemaAlignmentNode class that handles DataFrame
column mapping and alignment to target schema structure. It inherits from
MultiAgentBase for AWS Strands integration with proper session management.
"""

import re
from datetime import datetime
from difflib import SequenceMatcher
from io import StringIO
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from loguru import logger
from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import ContentBlock, Message

from ..config import SchemaAlignmentConfig
from ..interfaces.schema_collector import SchemaCollector

# ProcessorLogger removed - using standard logging
from ..logging.error_context_builder import ErrorContextBuilder, safe_isoformat
from ..models.schema_alignment_results import (
    SchemaAlignmentChangeDetail,
    SchemaAlignmentResults,
)
from ..models.state import NodeTokenUsage, ProcessorState
from ..utils.prompt_utils import FENCING_INSTRUCTION, fence_list, sanitize


class SchemaAlignmentError(Exception):
    """Exception raised when schema alignment fails."""

    pass


class SchemaAlignmentNode(MultiAgentBase):
    """
    MultiAgentBase node for aligning DataFrame to schema structure.

    This node handles the mapping of input DataFrame columns to the expected
    schema columns, including handling missing columns, extra columns, and
    column renaming based on schema definitions. It inherits from MultiAgentBase
    for AWS Strands session management and standardized result handling.
    """

    def __init__(
        self,
        schema_collector: SchemaCollector,
        schema_alignment_config: Optional["SchemaAlignmentConfig"] = None,
    ):
        """
        Initialize the schema alignment node.

        Args:
            schema_collector: Implementation for retrieving schema information
            schema_alignment_config: Configuration for schema alignment processing
        """
        super().__init__()
        self.schema_collector = schema_collector

        # Import here to avoid circular imports
        from ..config import SchemaAlignmentConfig

        self.config = schema_alignment_config or SchemaAlignmentConfig()

        # Initialize Bedrock client if LLM is enabled
        self.bedrock_runtime = None
        if self.config.use_llm:
            try:
                import boto3

                self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=self.config.aws_region)
            except Exception as e:
                logger.warning(f"Failed to initialize Bedrock client: {e}. LLM matching will be disabled.")
                self.config.use_llm = False

        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._columns_cache: Dict[str, List[str]] = {}
        self._llm_confidence_data: Dict[str, Dict[str, Any]] = {}

    async def invoke_async(
        self,
        task: str | list[ContentBlock],
        invocation_state: dict[str, Any] | None = None,
        **kwargs,
    ) -> MultiAgentResult:
        """
        Process schema alignment using MultiAgentBase framework.

        Args:
            task: Task content (string or ContentBlock list)
            invocation_state: Optional invocation state dictionary containing ProcessorState
            **kwargs: Additional keyword arguments (unused)

        Returns:
            MultiAgentResult with aligned_df and schema_definition in ProcessorState
        """
        # Get ProcessorState from invocation_state
        if not invocation_state or "processor_state" not in invocation_state:
            error_msg = "ProcessorState must be provided in invocation_state"
            logger.error(error_msg)
            return MultiAgentResult(
                status=Status.FAILED,
                results={"schema_alignment": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        state = invocation_state["processor_state"]

        # Validate input state
        try:
            self._validate_input_state(state)
        except SchemaAlignmentError as e:
            logger.error(f"Input validation failed: {str(e)}")
            return MultiAgentResult(
                status=Status.FAILED,
                results={"schema_alignment": NodeResult(result=e, status=Status.FAILED)},
            )

        try:
            # Update processing stage
            state.set_current_stage("schema_alignment")

            # Convert original DataFrame to CSV string for result instance
            original_data_csv = None
            if state.has_metadata():
                try:
                    original_data_csv = self._dataframe_to_csv_string(state.metadata_df)
                    logger.debug(
                        f"Converted original data to CSV string ({len(original_data_csv)} characters) - original_shape={state.metadata_df.shape}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to convert original data to CSV: {e}")
                    # Continue processing even if CSV conversion fails

            # Save initial state to session
            await self._save_state_to_session("schema_alignment_start", state)

            # Retrieve schema definition with caching
            logger.debug(f"Retrieving schema definition for program_id={state.program_id}, core_id={state.core_id}")

            schema_definition = await self._get_cached_schema(state.program_id, state.core_id)
            state.schema_definition = schema_definition

            # Get expected columns from schema with caching
            expected_columns = await self._get_cached_columns(state.program_id, state.core_id)

            logger.debug(
                f"Expected columns retrieved: {len(expected_columns)} columns - expected_columns={expected_columns}, input_columns={list(state.metadata_df.columns)}"
            )

            # Perform column alignment
            aligned_df, column_mapping, change_details = await self._align_dataframe_columns(
                state.metadata_df, expected_columns, schema_definition, state
            )
            state.aligned_df = aligned_df

            # Convert aligned DataFrame to CSV string for result instance
            aligned_data_csv = None
            try:
                aligned_data_csv = self._dataframe_to_csv_string(aligned_df)
                logger.debug(
                    f"Converted aligned data to CSV string ({len(aligned_data_csv)} characters) - aligned_shape={aligned_df.shape}"
                )
            except Exception as e:
                logger.warning(f"Failed to convert aligned data to CSV: {e}")
                # Continue processing even if CSV conversion fails

            # Generate transformation summary with counts and details
            transformation_summary = {}
            try:
                transformation_summary = self._create_transformation_summary(
                    state.metadata_df, aligned_df, column_mapping, change_details
                )
                # Store temporary processing metadata in state
                state.transformation_summary = transformation_summary
                state.column_mappings = column_mapping

                logger.info(
                    f"Generated transformation summary - columns_renamed={transformation_summary.get('columns_renamed', 0)}, columns_added={transformation_summary.get('columns_added', 0)}, columns_removed={transformation_summary.get('columns_removed', 0)}"
                )
            except Exception as e:
                logger.warning(f"Failed to create transformation summary: {e}")
                # Set empty summary if creation fails
                transformation_summary = {
                    "columns_renamed": 0,
                    "columns_added": 0,
                    "columns_removed": 0,
                    "error": str(e),
                }
                state.transformation_summary = transformation_summary
                state.column_mappings = {}

            # Initialize CombinedResults if not already present
            if state.combined_results is None:
                from ..models.combined_results import CombinedResults

                state.combined_results = CombinedResults()
                logger.debug(f"Initialized CombinedResults in ProcessorState - job_id={state.job_id}")

            # Create SchemaAlignmentResults instance with LLM-enhanced change details
            try:
                if original_data_csv and aligned_data_csv:
                    # Import the summary model
                    from ..models.schema_alignment_results import (
                        SchemaAlignmentResultsSummary,
                    )

                    # Calculate aggregate statistics from LLM-enhanced change details
                    total_changes = len(change_details)
                    columns_renamed = sum(1 for change in change_details if change.change_type == "rename")
                    columns_added = sum(1 for change in change_details if change.change_type == "add")
                    columns_removed = sum(1 for change in change_details if change.change_type == "remove")

                    # Create summary with job metadata, CSV data, and calculated aggregate statistics
                    summary = SchemaAlignmentResultsSummary(
                        job_id=state.job_id,
                        version=getattr(state, "current_version", 1),
                        original_data_csv=original_data_csv,
                        aligned_data_csv=aligned_data_csv,
                        total_changes=total_changes,
                        columns_renamed=columns_renamed,
                        columns_added=columns_added,
                        columns_removed=columns_removed,
                        rows_original=len(state.metadata_df),
                        rows_aligned=len(aligned_df),
                    )

                    # Construct complete SchemaAlignmentResults instance with populated change details list
                    schema_alignment_results = SchemaAlignmentResults(
                        schema_alignment_results=change_details,  # Use LLM-enhanced change details from alignment
                        summary=summary,
                    )

                    # Store SchemaAlignmentResults instance in CombinedResults.schema_alignment_results
                    state.combined_results.schema_alignment_results = schema_alignment_results

                    # Calculate LLM matching success rate for logging
                    llm_matches = sum(
                        1 for change in change_details if change.reason and "LLM-determined" in change.reason
                    )
                    llm_success_rate = (llm_matches / total_changes * 100) if total_changes > 0 else 0

                    # Comprehensive logging for result instance creation
                    logger.info(
                        f"Created SchemaAlignmentResults instance with LLM-enhanced change details - job_id={schema_alignment_results.summary.job_id}, version={schema_alignment_results.summary.version}, change_details_count={total_changes}, llm_success_rate={llm_success_rate:.1f}%"
                    )

                    logger.info(
                        f"Successfully created SchemaAlignmentResults instance for job {state.job_id} and stored in CombinedResults: "
                        f"{total_changes} changes tracked ({columns_renamed} renames, {columns_added} adds, "
                        f"{columns_removed} removes), LLM success rate: {llm_success_rate:.1f}%"
                    )
                else:
                    logger.warning("Could not create SchemaAlignmentResults instance due to missing CSV data")

            except Exception as e:
                logger.error(f"Failed to create SchemaAlignmentResults instance: {e}")
                # Continue processing even if result instance creation fails

            # Save intermediate state to session
            await self._save_state_to_session("schema_alignment_complete", state)

            logger.info(
                f"Schema alignment completed successfully. "
                f"Aligned {len(aligned_df.columns)} columns for {len(aligned_df)} rows"
            )

            # Create success AgentResult with alignment summary
            success_message: Message = {
                "content": [
                    {
                        "text": f"Schema alignment completed successfully. Aligned {len(aligned_df.columns)} columns for {len(aligned_df)} rows"
                    }
                ]
            }
            agent_result = AgentResult(
                stop_reason="end_turn",
                message=success_message,
                metrics=EventLoopMetrics(),
                state={
                    "aligned_columns": len(aligned_df.columns),
                    "total_rows": len(aligned_df),
                },
            )

            return MultiAgentResult(
                status=Status.COMPLETED,
                results={"schema_alignment": NodeResult(result=agent_result, status=Status.COMPLETED)},
            )

        except Exception as e:
            error_msg = f"Schema alignment failed: {str(e)}"
            logger.error(error_msg)

            # Enhanced error logging
            error_context = ErrorContextBuilder.build_schema_alignment_context(state, e, {"node": "schema_alignment"})
            logger.error(f"Schema alignment error: {str(e)} - error_context={error_context}")

            # Return failed result with enhanced error information
            enhanced_error = SchemaAlignmentError(f"{error_msg}. Check logs for detailed error context.")
            return MultiAgentResult(
                status=Status.FAILED,
                results={"schema_alignment": NodeResult(result=enhanced_error, status=Status.FAILED)},
            )

    def _validate_input_state(self, state: ProcessorState) -> None:
        """
        Validate that the input state contains required data.

        Args:
            state: ProcessorState to validate

        Raises:
            SchemaAlignmentError: If required data is missing
        """
        if not state.has_metadata():
            raise SchemaAlignmentError("Input state must contain metadata_df")

        if not state.has_schema_ids():
            raise SchemaAlignmentError("Input state must contain program_id and core_id")

    async def _align_dataframe_columns(
        self,
        df: pd.DataFrame,
        expected_columns: List[str],
        schema_definition: Dict,
        state: ProcessorState,
    ) -> Tuple[pd.DataFrame, Dict[str, str], List["SchemaAlignmentChangeDetail"]]:
        """
        Align DataFrame columns to match expected schema columns with change tracking.

        Args:
            df: Input DataFrame to align
            expected_columns: List of expected column names from schema
            schema_definition: Full schema definition for reference
            state: ProcessorState for token usage tracking

        Returns:
            Tuple of (aligned DataFrame, column mappings, change details list)

        Raises:
            SchemaAlignmentError: If critical alignment issues occur
        """

        logger.debug(f"Aligning DataFrame with {len(df.columns)} columns to {len(expected_columns)} expected columns")

        # Create a copy to avoid modifying the original
        aligned_df = df.copy()
        change_details = []
        total_rows = len(df)

        # Get current columns
        current_columns = set(aligned_df.columns)
        expected_columns_set = set(expected_columns)

        # Find column mappings (case-insensitive and with common variations)
        column_mapping = self._find_column_mappings(current_columns, expected_columns_set, state)

        # Track column rename changes with confidence information
        if column_mapping and self.config.enable_change_tracking:
            for original_col, new_col in column_mapping.items():
                change_detail = self._create_change_detail_with_confidence(
                    change_type="rename",
                    original_column=original_col,
                    new_column=new_col,
                    row_count_affected=total_rows,
                )
                change_details.append(change_detail)

        # Apply column renaming
        if column_mapping:
            aligned_df = aligned_df.rename(columns=column_mapping)
            logger.info(f"Renamed columns: {column_mapping}")

        # Handle column splitting and combining (only with LLM)
        if self.config.use_llm and self.bedrock_runtime:
            aligned_df, split_combine_changes = await self._handle_column_transformations_llm(
                aligned_df, expected_columns_set, total_rows
            )
            change_details.extend(split_combine_changes)

        # Handle missing columns
        missing_columns = expected_columns_set - set(aligned_df.columns)
        if missing_columns:
            if self.config.enable_change_tracking:
                for col in missing_columns:
                    change_detail = self._create_change_detail_with_confidence(
                        change_type="add",
                        original_column=None,
                        new_column=col,
                        row_count_affected=total_rows,
                    )
                    change_details.append(change_detail)

            self._add_missing_columns(aligned_df, missing_columns)
            logger.warning(f"Added missing columns with null values: {missing_columns}")

        # Handle extra columns
        extra_columns = set(aligned_df.columns) - expected_columns_set
        if extra_columns:
            if self.config.enable_change_tracking:
                for col in extra_columns:
                    change_detail = self._create_change_detail_with_confidence(
                        change_type="remove",
                        original_column=col,
                        new_column=None,
                        row_count_affected=total_rows,
                    )
                    change_details.append(change_detail)

            self._handle_extra_columns(aligned_df, extra_columns)
            logger.warning(f"Removed extra columns: {extra_columns}")

        # Reorder columns to match expected order
        aligned_df = aligned_df.reindex(columns=expected_columns, fill_value=None)

        return aligned_df, column_mapping, change_details

    def _find_column_mappings(
        self,
        current_columns: Set[str],
        expected_columns: Set[str],
        state: ProcessorState,
    ) -> Dict[str, str]:
        """
        Find mappings between current and expected column names using LLM with rule-based fallback.

        Args:
            current_columns: Set of current column names
            expected_columns: Set of expected column names

        Returns:
            Dictionary mapping current column names to expected names
        """
        current_list = list(current_columns)
        expected_list = list(expected_columns)

        # Use batched matching for large column sets (if enabled)
        if (
            self.config.use_llm
            and self.config.enable_column_batching
            and len(expected_list) > self.config.column_batch_size
        ):
            return self._find_column_mappings_batched(current_list, expected_list, state)

        try:
            if self.config.use_llm and self.bedrock_runtime:
                matches = self._llm_column_match(current_list, expected_list, state)
                logger.info(f"LLM matching found {len(matches)} column mappings")
            else:
                matches = self._rule_based_match(current_list, expected_list)
                logger.info(f"Rule-based matching found {len(matches)} column mappings")
        except Exception as e:
            logger.warning(f"LLM matching failed: {e}, falling back to rule-based")
            if self.config.fallback_on_llm_failure:
                matches = self._rule_based_match(current_list, expected_list)
                logger.info(f"Fallback rule-based matching found {len(matches)} column mappings")
            else:
                raise

        # Convert matches to mappings (reverse the direction)
        mappings = {}
        for expected_col, current_col in matches.items():
            if current_col != expected_col:
                mappings[current_col] = expected_col

        return mappings

    def _normalize_column_name(self, column_name: str) -> str:
        """
        Normalize column name for comparison.

        Args:
            column_name: Original column name

        Returns:
            Normalized column name (lowercase, underscores, no spaces)
        """
        return column_name.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")

    def _add_missing_columns(self, df: pd.DataFrame, missing_columns: Set[str]) -> None:
        """
        Add missing columns to DataFrame with null values.

        Args:
            df: DataFrame to modify (modified in place)
            missing_columns: Set of column names to add
        """
        for col in missing_columns:
            df[col] = None

    def _handle_extra_columns(self, df: pd.DataFrame, extra_columns: Set[str]) -> None:
        """
        Handle extra columns that are not in the expected schema.

        Currently removes extra columns, but could be extended to log them
        or handle them differently based on configuration.

        Args:
            df: DataFrame to modify (modified in place)
            extra_columns: Set of extra column names to handle
        """
        # For now, we drop extra columns
        # In the future, this could be configurable (keep, log, etc.)
        df.drop(columns=list(extra_columns), inplace=True)

    def _dataframe_to_csv_string(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to CSV string for frontend consumption.

        This method handles the conversion of pandas DataFrame to CSV string format
        that can be safely transmitted through the API and parsed by the frontend.
        It includes proper error handling for CSV conversion failures.

        Args:
            df: DataFrame to convert to CSV string

        Returns:
            CSV string representation of the DataFrame

        Raises:
            SchemaAlignmentError: If CSV conversion fails
        """
        try:
            # Use StringIO to capture CSV output
            csv_buffer = StringIO()

            # Convert DataFrame to CSV with specific formatting for consistency
            df.to_csv(
                csv_buffer,
                index=False,  # Don't include row indices
                na_rep="",  # Replace NaN values with empty strings
                encoding="utf-8",
                lineterminator="\n",  # Use consistent line endings
            )

            # Get the CSV string
            csv_string = csv_buffer.getvalue()
            csv_buffer.close()

            # Validate that we got a non-empty result
            if not csv_string or csv_string.strip() == "":
                raise ValueError("DataFrame conversion resulted in empty CSV string")

            logger.debug(
                f"Successfully converted DataFrame with shape {df.shape} to CSV string ({len(csv_string)} characters)"
            )
            return csv_string

        except Exception as e:
            error_msg = f"Failed to convert DataFrame to CSV string: {str(e)}"
            logger.error(error_msg)
            raise SchemaAlignmentError(error_msg) from e

    def _create_transformation_summary(
        self,
        original_df: pd.DataFrame,
        aligned_df: pd.DataFrame,
        column_mapping: Dict[str, str],
        change_details: List["SchemaAlignmentChangeDetail"],
    ) -> Dict[str, Any]:
        """
        Create enhanced summary of transformations with detailed change metadata.

        This method analyzes the differences between the original and aligned
        DataFrames to create a comprehensive summary of all transformations
        that were applied during the schema alignment process, including
        detailed change metadata from SchemaAlignmentChangeDetail objects.

        Args:
            original_df: Original DataFrame before alignment
            aligned_df: DataFrame after schema alignment
            column_mapping: Dictionary mapping original to aligned column names
            change_details: List of SchemaAlignmentChangeDetail objects with detailed change metadata

        Returns:
            Dictionary containing transformation summary with counts and details

        Raises:
            SchemaAlignmentError: If transformation analysis fails
        """
        try:
            # Get column sets for analysis
            original_cols = set(original_df.columns)
            aligned_cols = set(aligned_df.columns)

            # Calculate column changes from change_details for accuracy
            rename_changes = [change for change in change_details if change.change_type == "rename"]
            add_changes = [change for change in change_details if change.change_type == "add"]
            remove_changes = [change for change in change_details if change.change_type == "remove"]

            # Extract column mappings from rename changes for validation
            change_detail_mappings = {change.original_column: change.new_column for change in rename_changes}

            # Validate that transformation summary accurately reflects all detected changes
            if len(change_detail_mappings) != len(column_mapping):
                logger.warning(
                    f"Mismatch between change details mappings ({len(change_detail_mappings)}) "
                    f"and column mappings ({len(column_mapping)}). Using change details as authoritative."
                )

            # Use change_details as the authoritative source for transformation counts
            columns_renamed = len(rename_changes)
            columns_added = len(add_changes)
            columns_removed = len(remove_changes)

            # Extract specific column names affected from change details
            renamed_column_details = {
                change.original_column: {
                    "new_name": change.new_column,
                    "reason": change.reason,
                    "rows_affected": change.row_count_affected,
                }
                for change in rename_changes
            }

            added_column_details = {
                change.new_column: {
                    "reason": change.reason,
                    "rows_affected": change.row_count_affected,
                }
                for change in add_changes
            }

            removed_column_details = {
                change.original_column: {
                    "reason": change.reason,
                    "rows_affected": change.row_count_affected,
                }
                for change in remove_changes
            }

            # Calculate LLM matching confidence from change details
            llm_matches = sum(1 for change in change_details if change.reason and "LLM-determined" in change.reason)
            rule_based_matches = len(change_details) - llm_matches
            llm_confidence = (llm_matches / len(change_details) * 100) if change_details else 0

            # Create comprehensive transformation summary with enhanced metadata
            transformation_summary = {
                "columns_renamed": columns_renamed,
                "columns_added": columns_added,
                "columns_removed": columns_removed,
                "rows_original": len(original_df),
                "rows_aligned": len(aligned_df),
                "column_mappings": column_mapping,  # Keep for backward compatibility
                "added_columns": sorted([change.new_column for change in add_changes]),
                "removed_columns": sorted([change.original_column for change in remove_changes]),
                "original_column_count": len(original_cols),
                "aligned_column_count": len(aligned_cols),
                "data_shape_changed": original_df.shape != aligned_df.shape,
                "transformation_timestamp": datetime.now().isoformat(),
                "total_transformations": len(change_details),
            }

            # Add detailed column analysis with change metadata
            transformation_summary["column_analysis"] = {
                "original_columns": sorted(list(original_cols)),
                "aligned_columns": sorted(list(aligned_cols)),
                "unchanged_columns": sorted(list(original_cols & aligned_cols - set(column_mapping.keys()))),
                "total_transformations": len(change_details),
            }

            # Add change type breakdown with specific column names affected and LLM matching confidence
            transformation_summary["change_breakdown"] = {
                "rename_count": columns_renamed,
                "add_count": columns_added,
                "remove_count": columns_removed,
                "renamed_columns": renamed_column_details,
                "added_column_details": added_column_details,
                "removed_column_details": removed_column_details,
                "llm_matching_confidence": f"{llm_confidence:.1f}%",
                "llm_matches": llm_matches,
                "rule_based_matches": rule_based_matches,
            }

            # Add LLM usage statistics and matching details
            llm_enabled = self.config.use_llm and self.bedrock_runtime is not None
            transformation_summary["llm_processing"] = {
                "llm_enabled": llm_enabled,
                "model_id": self.config.model_id if llm_enabled else None,
                "aws_region": self.config.aws_region,
                "llm_temperature": self.config.llm_temperature,
                "llm_max_tokens": self.config.llm_max_tokens,
                "llm_timeout_seconds": self.config.llm_timeout_seconds,
                "fallback_used": not llm_enabled and self.config.fallback_on_llm_failure,
                "similarity_threshold": self.config.similarity_threshold,
                "matching_method": "LLM-enhanced" if llm_enabled else "rule-based",
                "total_llm_calls": 1 if llm_enabled and change_details else 0,
                "llm_success_rate": f"{llm_confidence:.1f}%",
                "column_batch_size": (self.config.column_batch_size if llm_enabled else None),
            }

            # Store complete change history with before/after column states, transformation reasons, and semantic matching details
            transformation_summary["change_history"] = {
                "before_state": {
                    "columns": sorted(list(original_cols)),
                    "column_count": len(original_cols),
                    "row_count": len(original_df),
                },
                "after_state": {
                    "columns": sorted(list(aligned_cols)),
                    "column_count": len(aligned_cols),
                    "row_count": len(aligned_df),
                },
                "transformations_applied": {
                    "column_renames": column_mapping,  # Keep for backward compatibility
                    "columns_added": sorted([change.new_column for change in add_changes]),
                    "columns_removed": sorted([change.original_column for change in remove_changes]),
                },
                "detailed_changes": [
                    {
                        "change_type": change.change_type,
                        "original_column": change.original_column,
                        "new_column": change.new_column,
                        "reason": change.reason,
                        "rows_affected": change.row_count_affected,
                        "semantic_matching": "LLM-determined" in (change.reason or ""),
                    }
                    for change in change_details
                ],
            }

            # Include processing timestamp, LLM usage statistics, and impact analysis
            transformation_summary["processing_metadata"] = {
                "processing_timestamp": datetime.now().isoformat(),
                "total_rows_affected": len(original_df),  # All rows are affected by column changes
                "column_count_change": len(aligned_cols) - len(original_cols),
                "data_integrity_maintained": len(original_df) == len(aligned_df),
                "change_validation_passed": len(change_details) == (columns_renamed + columns_added + columns_removed),
                "llm_processing_enabled": llm_enabled,
                "change_tracking_enabled": self.config.enable_change_tracking,
            }

            # Add impact analysis with total rows affected and column count changes
            transformation_summary["impact_analysis"] = {
                "total_changes_detected": len(change_details),
                "columns_with_semantic_changes": sum(
                    1 for change in change_details if change.reason and "semantic" in change.reason.lower()
                ),
                "columns_with_structural_changes": sum(
                    1 for change in change_details if change.change_type in ["add", "remove"]
                ),
                "total_rows_impacted": len(original_df),
                "data_completeness_maintained": len(original_df) == len(aligned_df),
                "schema_complexity_change": {
                    "before": len(original_cols),
                    "after": len(aligned_cols),
                    "net_change": len(aligned_cols) - len(original_cols),
                },
            }

            logger.debug(
                f"Created enhanced transformation summary with detailed change metadata: "
                f"{columns_renamed} renamed, {columns_added} added, {columns_removed} removed columns, "
                f"LLM enabled: {llm_enabled}, LLM confidence: {llm_confidence:.1f}%"
            )

            return transformation_summary

        except Exception as e:
            error_msg = f"Failed to create transformation summary: {str(e)}"
            logger.error(error_msg)
            raise SchemaAlignmentError(error_msg) from e

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
                    "metadata_shape": (state.metadata_df.shape if state.has_metadata() else None),
                    "aligned_shape": (state.aligned_df.shape if state.has_aligned_data() else None),
                    "schema_definition_keys": (
                        list(state.schema_definition.keys()) if state.schema_definition else None
                    ),
                }

                # Check if session manager supports the expected methods
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data(f"schema_alignment_{checkpoint}", state_data)
                    logger.debug(f"Saved state to session at checkpoint: {checkpoint}")
                elif hasattr(self.session_manager, "save"):
                    await self.session_manager.save(f"schema_alignment_{checkpoint}", state_data)
                    logger.debug(f"Saved state to session at checkpoint: {checkpoint}")
                else:
                    # Session manager doesn't support the expected methods - this is fine
                    logger.debug(
                        f"Session manager {type(self.session_manager).__name__} does not support generic data saving - skipping checkpoint save"
                    )
        except Exception as e:
            logger.debug(
                f"Session checkpoint save failed at {checkpoint}: {e} - continuing without session persistence"
            )

    async def _get_cached_schema(self, program_id: str, core_id: str) -> Dict[str, Any]:
        """
        Get schema definition with session-based caching.

        Args:
            program_id: Schema program identifier
            core_id: Schema core identifier

        Returns:
            Schema definition dictionary
        """
        cache_key = f"{program_id}_{core_id}"

        # Check local cache first
        if cache_key in self._schema_cache:
            logger.debug(f"Schema cache hit (local) for {cache_key}")
            return self._schema_cache[cache_key]

        # Check session cache
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                cached_schema = None
                # Use session manager's actual method (may vary by implementation)
                if hasattr(self.session_manager, "get_data"):
                    cached_schema = await self.session_manager.get_data(f"schema_def_{cache_key}")
                elif hasattr(self.session_manager, "get"):
                    cached_schema = await self.session_manager.get(f"schema_def_{cache_key}")

                if cached_schema:
                    logger.debug(f"Schema cache hit (session) for {cache_key}")
                    self._schema_cache[cache_key] = cached_schema
                    return cached_schema
        except Exception as e:
            logger.debug(f"Session cache lookup failed for schema {cache_key}: {e} - using direct fetch")

        # Fetch from schema collector
        logger.debug(f"Fetching schema from collector for {cache_key}")
        schema_definition = await self.schema_collector.get_schema(program_id, core_id)

        # Cache in both local and session
        self._schema_cache[cache_key] = schema_definition
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Use session manager's actual method (may vary by implementation)
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data(f"schema_def_{cache_key}", schema_definition)
                    logger.debug(f"Cached schema in session for {cache_key}")
                elif hasattr(self.session_manager, "save"):
                    await self.session_manager.save(f"schema_def_{cache_key}", schema_definition)
                    logger.debug(f"Cached schema in session for {cache_key}")
        except Exception as e:
            logger.debug(f"Failed to cache schema in session for {cache_key}: {e} - using local cache only")

        return schema_definition

    async def _get_cached_columns(self, program_id: str, core_id: str) -> List[str]:
        """
        Get schema columns with session-based caching.

        Args:
            program_id: Schema program identifier
            core_id: Schema core identifier

        Returns:
            List of expected column names
        """
        cache_key = f"{program_id}_{core_id}"

        # Check local cache first
        if cache_key in self._columns_cache:
            logger.debug(f"Columns cache hit (local) for {cache_key}")
            return self._columns_cache[cache_key]

        # Check session cache
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                cached_columns = None
                # Use session manager's actual method (may vary by implementation)
                if hasattr(self.session_manager, "get_data"):
                    cached_columns = await self.session_manager.get_data(f"schema_cols_{cache_key}")
                elif hasattr(self.session_manager, "get"):
                    cached_columns = await self.session_manager.get(f"schema_cols_{cache_key}")

                if cached_columns:
                    logger.debug(f"Columns cache hit (session) for {cache_key}")
                    self._columns_cache[cache_key] = cached_columns
                    return cached_columns
        except Exception as e:
            logger.debug(f"Session cache lookup failed for columns {cache_key}: {e} - using direct fetch")

        # Fetch from schema collector
        logger.debug(f"Fetching columns from collector for {cache_key}")
        expected_columns = await self.schema_collector.get_schema_columns(program_id, core_id)

        # Cache in both local and session
        self._columns_cache[cache_key] = expected_columns
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Use session manager's actual method (may vary by implementation)
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data(f"schema_cols_{cache_key}", expected_columns)
                    logger.debug(f"Cached columns in session for {cache_key}")
                elif hasattr(self.session_manager, "save"):
                    await self.session_manager.save(f"schema_cols_{cache_key}", expected_columns)
                    logger.debug(f"Cached columns in session for {cache_key}")
        except Exception as e:
            logger.debug(f"Failed to cache columns in session for {cache_key}: {e} - using local cache only")

        return expected_columns

    def _find_column_mappings_batched(
        self,
        current_columns: List[str],
        expected_columns: List[str],
        state: ProcessorState,
    ) -> Dict[str, str]:
        """
        Find column mappings using batched LLM calls for large column sets.

        Args:
            current_columns: List of current column names
            expected_columns: List of expected column names

        Returns:
            Dictionary mapping current column names to expected names
        """
        logger.info(
            f"Using batched column matching for {len(current_columns)} current columns and {len(expected_columns)} expected columns"
        )

        # Create batches of expected columns
        batch_size = self.config.column_batch_size
        expected_batches = [expected_columns[i : i + batch_size] for i in range(0, len(expected_columns), batch_size)]

        all_matches = {}
        self._llm_confidence_data = {}

        for batch_idx, expected_batch in enumerate(expected_batches):
            logger.debug(
                f"Processing column batch {batch_idx + 1}/{len(expected_batches)} with {len(expected_batch)} expected columns"
            )

            try:
                batch_matches = self._llm_column_match(current_columns, expected_batch, state)
                all_matches.update(batch_matches)
                logger.debug(f"Batch {batch_idx + 1} found {len(batch_matches)} matches")
            except Exception as e:
                logger.warning(f"Batch {batch_idx + 1} LLM matching failed: {e}, using rule-based fallback")
                if self.config.fallback_on_llm_failure:
                    batch_matches = self._rule_based_match(current_columns, expected_batch)
                    all_matches.update(batch_matches)
                    logger.debug(f"Batch {batch_idx + 1} fallback found {len(batch_matches)} matches")

        # Convert matches to mappings
        mappings = {}
        for expected_col, current_col in all_matches.items():
            if current_col != expected_col:
                mappings[current_col] = expected_col

        logger.info(
            f"Batched column matching completed: {len(mappings)} total mappings from {len(expected_batches)} batches"
        )
        return mappings

    def _llm_column_match(
        self, csv_columns: List[str], schema_fields: List[str], state: ProcessorState
    ) -> Dict[str, str]:
        """
        Use LLM to match columns semantically with confidence scoring and reasoning.

        Args:
            csv_columns: List of source column names from CSV
            schema_fields: List of target column names from schema
            state: ProcessorState for token usage tracking

        Returns:
            Dictionary mapping schema fields to CSV columns

        Raises:
            Exception: If LLM matching fails
        """
        system_prompt = (
            "You are an expert data schema mapping specialist. Your task is to find the most "
            "semantically similar source column for each target column. Consider semantic meaning, "
            "word relationships, and potential data transformations.\n"
            f"{FENCING_INSTRUCTION}"
        )

        # Source columns come from the user's CSV, so they are fenced as untrusted data
        user_prompt = (
            f"Source Columns:\n{fence_list('source_columns', csv_columns)}\n"
            f"Target Columns: {', '.join(schema_fields)}\n\n"
            f"For each target column, identify the most semantically similar source column.\n\n"
            f"Output Format (one per line):\n"
            f"Target: [target_column] | Match: [source_column] | Confidence: [High|Medium|Low] | Reasoning: [brief_explanation]"
        )

        try:
            response = self.bedrock_runtime.converse(
                modelId=self.config.model_id,
                system=[{"text": system_prompt}],
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                inferenceConfig={
                    "maxTokens": self.config.llm_max_tokens,
                    "temperature": self.config.llm_temperature,
                },
            )

            # Track token usage
            self._track_token_usage(response, state)

            content = response["output"]["message"]["content"][0]["text"]

            # Initialize confidence data storage if not already done
            if not hasattr(self, "_llm_confidence_data"):
                self._llm_confidence_data = {}

            matches = {}

            # Columns were sanitized before fencing, so the model echoes the sanitized
            # form. Map back to the original names the rest of the pipeline expects.
            sanitized_to_original = {sanitize(col): col for col in csv_columns}

            # Parse response with enhanced regex for confidence and reasoning
            for line in content.split("\n"):
                if "Target:" in line and "Match:" in line:
                    try:
                        # Extract target and match (existing logic)
                        target_match = re.search(r"Target:\s*([^|]+)\|", line)
                        match_match = re.search(r"Match:\s*([^|]+)(?:\||$)", line)

                        # Extract confidence and reasoning (new logic)
                        confidence_match = re.search(r"Confidence:\s*([^|]+)(?:\||$)", line)
                        reasoning_match = re.search(r"Reasoning:\s*(.+)$", line)

                        if target_match and match_match:
                            target = target_match.group(1).strip()
                            match = match_match.group(1).strip()
                            confidence = confidence_match.group(1).strip() if confidence_match else "Low"
                            reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

                            # Validate confidence level using utility function
                            from ..utils.confidence_utils import (
                                confidence_level_to_score,
                                validate_confidence_level,
                            )

                            confidence = validate_confidence_level(confidence)

                            # Resolve the sanitized name back to the real column
                            match = sanitized_to_original.get(match, match)

                            # Allow-list: only keep mappings between columns that really exist
                            if target in schema_fields and match in csv_columns:
                                matches[target] = match

                                # Store confidence data for change detail creation
                                confidence_score = confidence_level_to_score(confidence)
                                self._llm_confidence_data[match] = {  # Key by source column for rename operations
                                    "confidence_level": confidence,
                                    "confidence_score": confidence_score,
                                    "reasoning": reasoning,
                                }

                    except Exception as e:
                        logger.debug(f"Failed to parse line '{line}': {e}")
                        continue

            logger.debug(f"LLM matching extracted {len(matches)} valid mappings with confidence data")
            return matches

        except Exception as e:
            logger.error(f"LLM column matching failed: {e}")
            # Clear confidence data on failure
            if hasattr(self, "_llm_confidence_data"):
                self._llm_confidence_data.clear()
            raise

    def _track_token_usage(self, response: Dict[str, Any], state: ProcessorState) -> None:
        """
        Extract and track token usage from Bedrock converse API response.

        Args:
            response: Response from Bedrock converse API
            state: ProcessorState to accumulate token usage
        """
        try:
            # Get or create token usage entry for this node
            node_name = "schema_alignment"
            if node_name not in state.token_usage:
                state.token_usage[node_name] = NodeTokenUsage(node_name=node_name, llm_model_id=self.config.model_id)

            node_usage = state.token_usage[node_name]

            # Extract token usage from response
            if "usage" in response:
                usage = response["usage"]
                input_tokens = usage.get("inputTokens", 0)
                output_tokens = usage.get("outputTokens", 0)

                # Accumulate token counts
                node_usage.llm_calls += 1
                node_usage.llm_input_tokens += input_tokens
                node_usage.llm_output_tokens += output_tokens

                logger.debug(
                    f"Token usage tracked: +{input_tokens} input, +{output_tokens} output "
                    f"(total: {node_usage.llm_input_tokens} input, {node_usage.llm_output_tokens} output, "
                    f"{node_usage.llm_calls} calls)"
                )
            else:
                logger.warning("Bedrock response does not contain usage metrics")

        except Exception as e:
            logger.warning(f"Failed to track token usage: {e}")

    def _create_change_detail_with_confidence(
        self,
        change_type: str,
        original_column: str = None,
        new_column: str = None,
        row_count_affected: int = 0,
    ) -> "SchemaAlignmentChangeDetail":
        """Create change detail with confidence information and enhanced reasoning.

        This method centralizes the creation of SchemaAlignmentChangeDetail objects
        with proper confidence scoring and enhanced reason formatting according to
        the Target/Match/Confidence/Reasoning structure.

        Args:
            change_type: Type of change ("rename", "add", "remove")
            original_column: Original column name (for rename/remove operations)
            new_column: New column name (for rename/add operations)
            row_count_affected: Number of rows affected by this change

        Returns:
            SchemaAlignmentChangeDetail with confidence information and enhanced reasoning
        """
        from ..models.schema_alignment_results import SchemaAlignmentChangeDetail
        from ..utils.confidence_utils import (
            confidence_level_to_score,
            validate_confidence_level,
        )

        # Get confidence data from LLM matching if available
        confidence_data = getattr(self, "_llm_confidence_data", {}).get(original_column, {})

        if change_type == "rename":
            if self.config.use_llm and confidence_data:
                # LLM-based confidence with validation
                raw_confidence_level = confidence_data.get("confidence_level", "Low")
                confidence_level = validate_confidence_level(raw_confidence_level)
                confidence_score = confidence_level_to_score(confidence_level)
                llm_reasoning = confidence_data.get("reasoning", "")

                # Create enhanced reason string with structured format
                enhanced_reason = f"Target: {new_column} | Match: {original_column} | Confidence: {confidence_level} | Reasoning: {llm_reasoning}"
            else:
                # Fallback confidence for rule-based matching
                confidence_level = "Medium"  # Rule-based matches get medium confidence
                confidence_score = confidence_level_to_score(confidence_level)
                enhanced_reason = f"Target: {new_column} | Match: {original_column} | Confidence: {confidence_level} | Reasoning: Rule-based pattern match"

        elif change_type == "add":
            # Add operations have high confidence as they're required by schema
            confidence_level = "High"
            confidence_score = confidence_level_to_score(confidence_level)
            enhanced_reason = f"Target: {new_column} | Confidence: {confidence_level} | Reasoning: Required by schema"

        elif change_type == "remove":
            # Remove operations have medium confidence as they're structural changes
            confidence_level = "Medium"
            confidence_score = confidence_level_to_score(confidence_level)
            enhanced_reason = (
                f"Source: {original_column} | Confidence: {confidence_level} | Reasoning: Not in target schema"
            )

        elif change_type == "split":
            # Split operations have high confidence as they're data transformations
            confidence_level = "High"
            confidence_score = confidence_level_to_score(confidence_level)
            enhanced_reason = f"Split: {original_column} → {new_column} | Confidence: {confidence_level} | Reasoning: Column splitting transformation"

        elif change_type == "combine":
            # Combine operations have high confidence as they're data transformations
            confidence_level = "High"
            confidence_score = confidence_level_to_score(confidence_level)
            enhanced_reason = f"Combine: {original_column} → {new_column} | Confidence: {confidence_level} | Reasoning: Column combining transformation"

        else:
            # Default fallback for unknown change types
            confidence_level = "Low"
            confidence_score = confidence_level_to_score(confidence_level)
            enhanced_reason = f"Schema alignment operation: {change_type}"

        return SchemaAlignmentChangeDetail(
            change_type=change_type,
            original_column=original_column,
            new_column=new_column,
            reason=enhanced_reason,
            row_count_affected=row_count_affected,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
        )

    def _rule_based_match(self, csv_columns: List[str], schema_fields: List[str]) -> Dict[str, str]:
        """
        Rule-based column matching as fallback when LLM is not available.

        Args:
            csv_columns: List of source column names from CSV
            schema_fields: List of target column names from schema

        Returns:
            Dictionary mapping schema fields to CSV columns
        """
        matches = {}

        for schema_field in schema_fields:
            # Exact match first
            if schema_field in csv_columns:
                matches[schema_field] = schema_field
                continue

            # Case-insensitive matching
            target_lower = schema_field.lower()
            for col in csv_columns:
                if col.lower() == target_lower:
                    matches[schema_field] = col
                    break
            else:
                # Variation matching (camelCase, snake_case, etc.)
                variations = [
                    "".join([word.capitalize() for word in schema_field.split("_")]),
                    "".join(["_" + c.lower() if c.isupper() else c for c in schema_field]).lstrip("_"),
                    schema_field.lower(),
                    schema_field.upper(),
                ]

                for variation in variations:
                    if variation in csv_columns:
                        matches[schema_field] = variation
                        break
                else:
                    # Substring matching and similarity scoring
                    best_match = None
                    best_score = self.config.similarity_threshold

                    for col in csv_columns:
                        # Cleaned name comparisons
                        target_clean = schema_field.lower().replace("_", "").replace("-", "")
                        source_clean = col.lower().replace("_", "").replace("-", "")

                        if target_clean in source_clean or source_clean in target_clean:
                            matches[schema_field] = col
                            break

                        # SequenceMatcher for similarity scoring
                        score = SequenceMatcher(None, schema_field.lower(), col.lower()).ratio()
                        if score > best_score:
                            best_score = score
                            best_match = col
                    else:
                        if best_match:
                            matches[schema_field] = best_match

        return matches

    async def _handle_column_transformations_llm(
        self, df: pd.DataFrame, expected_columns: Set[str], total_rows: int
    ) -> Tuple[pd.DataFrame, List["SchemaAlignmentChangeDetail"]]:
        """
        Handle column splitting and combining using LLM identification.

        Args:
            df: DataFrame to transform
            expected_columns: Set of expected column names
            total_rows: Total number of rows for change tracking

        Returns:
            Tuple of (transformed DataFrame, list of change details)
        """
        change_details = []
        current_columns = list(df.columns)
        expected_columns_list = list(expected_columns)

        # Use LLM to identify transformation opportunities
        transformations = await self._llm_identify_transformations(current_columns, expected_columns_list)

        # Apply identified transformations
        for transform in transformations:
            if transform["type"] == "split":
                df, split_changes = self._apply_split_transformation(df, transform, total_rows)
                change_details.extend(split_changes)
            elif transform["type"] == "combine":
                df, combine_changes = self._apply_combine_transformation(df, transform, total_rows)
                change_details.extend(combine_changes)

        return df, change_details

    async def _llm_identify_transformations(
        self, current_columns: List[str], expected_columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to identify column transformation opportunities.

        Args:
            current_columns: List of current column names
            expected_columns: List of expected column names

        Returns:
            List of transformation dictionaries
        """
        system_prompt = (
            "You are a data transformation expert. Analyze the current and target columns to identify "
            "opportunities for column splitting or combining. Look for semantic relationships between columns.\n"
            f"{FENCING_INSTRUCTION}"
        )

        # Current columns originate from the user's CSV, so they are fenced as untrusted data
        user_prompt = (
            f"Current Columns:\n{fence_list('current_columns', current_columns)}\n"
            f"Target Columns: {', '.join(expected_columns)}\n\n"
            f"Analyze these columns and identify transformations:\n\n"
            f"SPLIT opportunities (when one current column should become multiple target columns):\n"
            f"- Example: 'full_name' -> 'first_name' + 'last_name'\n"
            f"- Example: 'address' -> 'street' + 'city'\n\n"
            f"COMBINE opportunities (when multiple current columns should become one target column):\n"
            f"- Example: 'first_name' + 'last_name' -> 'full_name'\n"
            f"- Example: 'street' + 'city' -> 'full_address'\n\n"
            f"Output each transformation on a separate line using EXACTLY this format:\n"
            f"SPLIT: source_column -> [target_col1, target_col2]\n"
            f"COMBINE: [source_col1, source_col2] -> target_column\n\n"
            f"If no transformations are needed, respond with: NO_TRANSFORMATIONS"
        )

        try:
            response = self.bedrock_runtime.converse(
                modelId=self.config.model_id,
                system=[{"text": system_prompt}],
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                inferenceConfig={
                    "maxTokens": self.config.llm_max_tokens,
                    "temperature": self.config.llm_temperature,
                },
            )

            content = response["output"]["message"]["content"][0]["text"]
            logger.debug(f"LLM transformation response: {content}")

            transformations = self._parse_transformation_response(content, current_columns, expected_columns)
            logger.info(f"Parsed {len(transformations)} transformations from LLM response")

            return transformations

        except Exception as e:
            logger.error(f"LLM transformation identification failed: {e}")
            return []

    def _parse_transformation_response(
        self, content: str, current_columns: List[str], expected_columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Parse LLM response for transformation instructions.
        """
        transformations = []

        logger.debug(f"Parsing transformation response: {content}")
        logger.debug(f"Current columns: {current_columns}")
        logger.debug(f"Expected columns: {expected_columns}")

        # Current columns were sanitized before fencing, so the model echoes the
        # sanitized form. Map back to the original names before validating.
        sanitized_to_original = {sanitize(col): col for col in current_columns}

        for line in content.split("\n"):
            line = line.strip()
            logger.debug(f"Processing line: '{line}'")

            if line.startswith("SPLIT:"):
                # Parse: SPLIT: full_name -> [first_name, last_name]
                parts = line.split(" -> ")
                if len(parts) == 2:
                    source = parts[0].replace("SPLIT:", "").strip()
                    source = sanitized_to_original.get(source, source)
                    target_part = parts[1].strip()
                    # Handle both [col1, col2] and col1, col2 formats
                    targets = [col.strip() for col in target_part.strip("[]").split(",")]

                    logger.debug(f"Split candidate: {source} -> {targets}")

                    if source in current_columns and all(t in expected_columns for t in targets):
                        transformations.append(
                            {
                                "type": "split",
                                "source": source,
                                "targets": targets,
                                "method": "llm_identified",
                            }
                        )
                        logger.info(f"Added split transformation: {source} -> {targets}")
                    else:
                        logger.debug(
                            f"Split validation failed: source_in_current={source in current_columns}, targets_in_expected={[t in expected_columns for t in targets]}"
                        )

            elif line.startswith("COMBINE:"):
                # Parse: COMBINE: [first_name, last_name] -> full_name
                parts = line.split(" -> ")
                if len(parts) == 2:
                    source_part = parts[0].replace("COMBINE:", "").strip()
                    sources = [
                        sanitized_to_original.get(col.strip(), col.strip())
                        for col in source_part.strip("[]").split(",")
                    ]
                    target = parts[1].strip()

                    logger.debug(f"Combine candidate: {sources} -> {target}")

                    if all(s in current_columns for s in sources) and target in expected_columns:
                        transformations.append(
                            {
                                "type": "combine",
                                "sources": sources,
                                "target": target,
                                "method": "llm_identified",
                            }
                        )
                        logger.info(f"Added combine transformation: {sources} -> {target}")
                    else:
                        logger.debug(
                            f"Combine validation failed: sources_in_current={[s in current_columns for s in sources]}, target_in_expected={target in expected_columns}"
                        )

        logger.info(f"Parsed {len(transformations)} valid transformations")
        return transformations

    def _apply_split_transformation(
        self, df: pd.DataFrame, transform: Dict[str, Any], total_rows: int
    ) -> Tuple[pd.DataFrame, List["SchemaAlignmentChangeDetail"]]:
        """
        Apply a split transformation identified by LLM.
        """
        change_details = []
        source_col = transform["source"]
        target_cols = transform["targets"]

        logger.info(f"LLM-identified split: '{source_col}' -> {target_cols}")

        # Apply generic splitting logic
        split_data = self._generic_split(df[source_col], len(target_cols))

        # Add new columns
        for i, target_col in enumerate(target_cols):
            if i < len(split_data.columns):
                df[target_col] = split_data.iloc[:, i]
            else:
                df[target_col] = None

            if self.config.enable_change_tracking:
                change_detail = self._create_change_detail_with_confidence(
                    change_type="split",
                    original_column=source_col,
                    new_column=target_col,
                    row_count_affected=total_rows,
                )
                change_details.append(change_detail)

        # Remove original column
        df = df.drop(columns=[source_col])

        return df, change_details

    def _apply_combine_transformation(
        self, df: pd.DataFrame, transform: Dict[str, Any], total_rows: int
    ) -> Tuple[pd.DataFrame, List["SchemaAlignmentChangeDetail"]]:
        """
        Apply a combine transformation identified by LLM.
        """
        change_details = []
        source_cols = transform["sources"]
        target_col = transform["target"]

        logger.info(f"LLM-identified combine: {source_cols} -> '{target_col}'")

        # Apply generic combining logic
        combined_data = self._generic_combine(df[source_cols])
        df[target_col] = combined_data

        # Track changes
        if self.config.enable_change_tracking:
            change_detail = self._create_change_detail_with_confidence(
                change_type="combine",
                original_column=", ".join(source_cols),
                new_column=target_col,
                row_count_affected=total_rows,
            )
            change_details.append(change_detail)

        # Remove original columns
        df = df.drop(columns=source_cols)

        return df, change_details

    def _generic_split(self, series: pd.Series, num_parts: int) -> pd.DataFrame:
        """
        Generic column splitting logic.
        """

        def split_value(value):
            if pd.isna(value) or not str(value).strip():
                return pd.Series([None] * num_parts)

            parts = str(value).strip().split()
            result = []

            if len(parts) == 0:
                result = [None] * num_parts
            elif len(parts) == 1:
                result = [parts[0]] + [None] * (num_parts - 1)
            elif len(parts) >= num_parts:
                result = parts[: num_parts - 1] + [" ".join(parts[num_parts - 1 :])]
            else:
                result = parts + [None] * (num_parts - len(parts))

            return pd.Series(result)

        return series.apply(split_value)

    def _generic_combine(self, df: pd.DataFrame) -> pd.Series:
        """
        Generic column combining logic.
        """

        def combine_values(row):
            parts = [str(val).strip() for val in row if pd.notna(val) and str(val).strip()]
            return " ".join(parts) if parts else None

        return df.apply(combine_values, axis=1)

    async def cleanup_session_data(self) -> None:
        """
        Clean up session data for this node.
        """
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Only attempt cleanup if session manager supports it
                if hasattr(self.session_manager, "delete_data"):
                    # Clean up schema alignment specific session data
                    keys_to_clean = [
                        "schema_alignment_start",
                        "schema_alignment_complete",
                    ]

                    for key in keys_to_clean:
                        try:
                            await self.session_manager.delete_data(key)
                        except Exception as e:
                            logger.debug(f"Failed to clean session key {key}: {e}")

                    logger.debug("Schema alignment session data cleaned up")
                else:
                    logger.debug("Session manager does not support data cleanup - skipping")
        except Exception as e:
            logger.debug(f"Error during schema alignment session cleanup: {e} - continuing")
