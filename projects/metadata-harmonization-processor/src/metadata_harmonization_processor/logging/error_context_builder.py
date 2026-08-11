# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Error context builder for comprehensive debugging information.
"""

import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.job import MetadataUploadJob
from ..models.state import ProcessorState


def safe_isoformat(dt) -> Optional[str]:
    """
    Safely convert datetime to ISO format string.

    Args:
        dt: Datetime object or string

    Returns:
        ISO format string or None if conversion fails
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    try:
        return dt.isoformat()
    except (AttributeError, ValueError):
        return None


class ErrorContextBuilder:
    """Builds comprehensive error context for debugging."""

    @staticmethod
    def build_schema_alignment_context(
        state: ProcessorState,
        error: Exception,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build error context for schema alignment failures.

        Args:
            state: Current processor state
            error: Exception that occurred
            additional_info: Additional context information

        Returns:
            Comprehensive error context dictionary
        """
        context = {
            "error_category": "schema_alignment",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "timestamp": datetime.now().isoformat(),
            "job_id": state.job_id if state else None,
            "program_id": state.program_id if state else None,
            "core_id": state.core_id if state else None,
        }

        # Add input data information
        if state and state.has_metadata():
            context["input_data"] = {
                "shape": state.metadata_df.shape,
                "columns": list(state.metadata_df.columns),
                "dtypes": state.metadata_df.dtypes.to_dict(),
                "null_counts": state.metadata_df.isnull().sum().to_dict(),
                "sample_data": (state.metadata_df.head(3).to_dict() if len(state.metadata_df) > 0 else {}),
            }

        # Add schema information if available
        if state and state.schema_definition:
            context["schema_info"] = {
                "schema_keys": list(state.schema_definition.keys()),
                "expected_columns": (
                    state.schema_definition.get("properties", {}).keys()
                    if isinstance(state.schema_definition.get("properties"), dict)
                    else []
                ),
            }

        # Add alignment-specific diagnostics
        if state and state.has_metadata():
            context["alignment_diagnostics"] = ErrorContextBuilder._analyze_column_alignment_issues(
                state.metadata_df.columns.tolist(), state.schema_definition
            )

        if additional_info:
            context["additional_info"] = additional_info

        return context

    @staticmethod
    def build_validation_context(
        state: ProcessorState,
        error: Exception,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build error context for validation failures.

        Args:
            state: Current processor state
            error: Exception that occurred
            additional_info: Additional context information

        Returns:
            Comprehensive error context dictionary
        """
        context = {
            "error_category": "validation",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "timestamp": datetime.now().isoformat(),
            "job_id": state.job_id if state else None,
            "program_id": state.program_id if state else None,
            "core_id": state.core_id if state else None,
        }

        # Add aligned data information
        if state and state.has_aligned_data():
            context["aligned_data"] = {
                "shape": state.aligned_df.shape,
                "columns": list(state.aligned_df.columns),
                "dtypes": state.aligned_df.dtypes.to_dict(),
                "null_counts": state.aligned_df.isnull().sum().to_dict(),
                "sample_data": (state.aligned_df.head(3).to_dict() if len(state.aligned_df) > 0 else {}),
            }

        # Add validation results if available
        if state and state.has_validation_results():
            context["validation_info"] = {
                "total_errors": len(state.validation_results.validation_results),
                "error_types": state.validation_results.summary.error_types,
                "sample_errors": [
                    {
                        "row": err.row,
                        "column": err.column,
                        "error_type": err.error_type.value,
                        "current_value": err.current_value,
                    }
                    for err in state.validation_results.validation_results[:5]  # First 5 errors
                ],
            }

        # Add validation-specific diagnostics
        if state and state.has_aligned_data():
            context["validation_diagnostics"] = ErrorContextBuilder._analyze_validation_issues(state.aligned_df)

        if additional_info:
            context["additional_info"] = additional_info

        return context

    @staticmethod
    def build_prediction_context(
        state: ProcessorState,
        error: Exception,
        prediction_type: str = "unknown",
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build error context for prediction failures.

        Args:
            state: Current processor state
            error: Exception that occurred
            prediction_type: Type of prediction (semantic, pattern, etc.)
            additional_info: Additional context information

        Returns:
            Comprehensive error context dictionary
        """
        context = {
            "error_category": "prediction",
            "prediction_type": prediction_type,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "timestamp": datetime.now().isoformat(),
            "job_id": state.job_id if state else None,
            "program_id": state.program_id if state else None,
            "core_id": state.core_id if state else None,
        }

        # Add validation results for prediction input
        if state and state.has_validation_results():
            context["prediction_input"] = {
                "total_validation_errors": len(state.validation_results.validation_results),
                "error_distribution": state.validation_results.summary.error_types,
                "errors_by_column": ErrorContextBuilder._group_errors_by_column(
                    state.validation_results.validation_results
                ),
            }

        # Add prediction-specific diagnostics
        context["prediction_diagnostics"] = {
            "has_validation_results": (state.has_validation_results() if state else False),
            "validation_error_count": (
                len(state.validation_results.validation_results) if state and state.has_validation_results() else 0
            ),
        }

        if additional_info:
            context["additional_info"] = additional_info

        return context

    @staticmethod
    def build_job_status_context(
        job: Optional[MetadataUploadJob],
        error: Exception,
        operation: str = "unknown",
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build error context for job status management failures.

        Args:
            job: Job object (may be None if job creation failed)
            error: Exception that occurred
            operation: Operation that failed (create, update, save, etc.)
            additional_info: Additional context information

        Returns:
            Comprehensive error context dictionary
        """
        context = {
            "error_category": "job_status",
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "timestamp": datetime.now().isoformat(),
        }

        # Add job information if available
        if job:
            context["job_info"] = {
                "job_id": job.job_id,
                "user_id": job.user_id,
                "status": job.status,
                "core_schema_id": job.core_schema_id,
                "program_schema_id": job.program_schema_id,
                "created_at": safe_isoformat(job.created_at),
                "completed_at": safe_isoformat(job.completed_at),
            }
        else:
            context["job_info"] = {"job": "None - job creation may have failed"}

        if additional_info:
            context["additional_info"] = additional_info

        return context

    @staticmethod
    def _analyze_column_alignment_issues(
        input_columns: List[str], schema_definition: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze potential column alignment issues.

        Args:
            input_columns: List of input column names
            schema_definition: Schema definition dictionary

        Returns:
            Analysis of alignment issues
        """
        analysis = {
            "input_column_count": len(input_columns),
            "input_columns": input_columns,
        }

        if schema_definition and "properties" in schema_definition:
            expected_columns = list(schema_definition["properties"].keys())
            analysis["expected_column_count"] = len(expected_columns)
            analysis["expected_columns"] = expected_columns

            # Find missing and extra columns
            input_set = set(input_columns)
            expected_set = set(expected_columns)

            analysis["missing_columns"] = list(expected_set - input_set)
            analysis["extra_columns"] = list(input_set - expected_set)
            analysis["matching_columns"] = list(input_set & expected_set)

            # Analyze potential column name variations
            analysis["potential_mappings"] = ErrorContextBuilder._find_potential_column_mappings(
                input_columns, expected_columns
            )

        return analysis

    @staticmethod
    def _analyze_validation_issues(df) -> Dict[str, Any]:
        """
        Analyze potential validation issues in the DataFrame.

        Args:
            df: DataFrame to analyze

        Returns:
            Analysis of validation issues
        """
        analysis = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "null_value_analysis": {},
            "data_type_analysis": {},
            "value_distribution_analysis": {},
        }

        # Analyze null values
        null_counts = df.isnull().sum()
        analysis["null_value_analysis"] = {
            "columns_with_nulls": null_counts[null_counts > 0].to_dict(),
            "total_null_values": null_counts.sum(),
        }

        # Analyze data types
        analysis["data_type_analysis"] = df.dtypes.to_dict()

        # Analyze value distributions for object columns (first few columns only)
        for col in df.select_dtypes(include=["object"]).columns[:5]:
            value_counts = df[col].value_counts().head(10)
            analysis["value_distribution_analysis"][col] = value_counts.to_dict()

        return analysis

    @staticmethod
    def _group_errors_by_column(validation_errors) -> Dict[str, int]:
        """
        Group validation errors by column.

        Args:
            validation_errors: List of validation error objects

        Returns:
            Dictionary mapping column names to error counts
        """
        error_counts = {}
        for error in validation_errors:
            column = error.column
            error_counts[column] = error_counts.get(column, 0) + 1
        return error_counts

    @staticmethod
    def _find_potential_column_mappings(input_columns: List[str], expected_columns: List[str]) -> List[Dict[str, str]]:
        """
        Find potential column name mappings based on similarity.

        Args:
            input_columns: List of input column names
            expected_columns: List of expected column names

        Returns:
            List of potential mappings
        """
        mappings = []

        def normalize_name(name: str) -> str:
            return name.lower().replace(" ", "_").replace("-", "_").replace(".", "_")

        # Create normalized lookup
        expected_normalized = {normalize_name(col): col for col in expected_columns}

        for input_col in input_columns:
            normalized_input = normalize_name(input_col)
            if normalized_input in expected_normalized:
                expected_col = expected_normalized[normalized_input]
                if input_col != expected_col:
                    mappings.append(
                        {
                            "input_column": input_col,
                            "expected_column": expected_col,
                            "mapping_type": "normalized_match",
                        }
                    )

        return mappings
