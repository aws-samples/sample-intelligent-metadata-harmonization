# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Enhanced job status logging with detailed state tracking.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from ..models.job import MetadataUploadJob
from ..models.validation import ValidationResults


class JobStatusLogger:
    """Enhanced job status logging with detailed state tracking."""

    def __init__(self):
        """Initialize the job status logger."""
        pass

    async def log_job_creation(self, job: MetadataUploadJob) -> None:
        """
        Log job creation with full job details.

        Args:
            job: Created job object
        """
        context = {
            "job_lifecycle_event": "created",
            "job_id": job.job_id,
            "user_id": job.user_id,
            "core_schema_id": job.core_schema_id,
            "program_schema_id": job.program_schema_id,
            "initial_status": job.status,
            "created_at": job.created_at,  # Already a string in ISO format
        }

        logger.info(f"Job created: {job.job_id} - {context}")

    async def log_status_transition(
        self,
        job_id: str,
        from_status: Optional[str],
        to_status: str,
        reason: str,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log job status transitions with detailed reasoning.

        Args:
            job_id: Job identifier
            from_status: Previous status (None for initial status)
            to_status: New status
            reason: Reason for the status change
            additional_context: Additional context information
        """
        context = {
            "job_lifecycle_event": "status_transition",
            "job_id": job_id,
            "from_status": from_status,
            "to_status": to_status,
            "transition_reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        if additional_context:
            context.update(additional_context)

        # Determine log level based on status
        level = "ERROR" if to_status == "failed" else "INFO"

        status_msg = f"Job {job_id} status: {from_status} → {to_status}"
        if reason:
            status_msg += f" (Reason: {reason})"

        if level == "ERROR":
            logger.error(f"{status_msg} - {context}")
        else:
            logger.info(f"{status_msg} - {context}")

    async def log_completion_with_results(
        self, job_id: str, results: ValidationResults, metrics: Dict[str, Any]
    ) -> None:
        """
        Log job completion with comprehensive results and metrics.

        Args:
            job_id: Job identifier
            results: Validation results
            metrics: Performance and processing metrics
        """
        # Determine completion status based on results
        has_errors = results.summary.total_errors > 0
        completion_status = "completed_with_errors" if has_errors else "completed_successfully"

        # Calculate error rate as percentage of total validation points
        total_validation_points = results.summary.total_rows * results.summary.columns_validated
        error_rate = (
            (results.summary.total_errors / total_validation_points * 100) if total_validation_points > 0 else 0
        )

        # Get duration from metrics
        duration_seconds = metrics.get("processing_duration_seconds", 0)
        duration_minutes = int(duration_seconds // 60)
        duration_secs = int(duration_seconds % 60)
        duration_str = f"{duration_seconds:.1f}s"
        if duration_minutes > 0:
            duration_str += f" ({duration_minutes}m {duration_secs}s)"

        level = "WARNING" if has_errors else "INFO"

        # Format multi-line summary
        summary_lines = [
            "═" * 60,
            "JOB COMPLETION",
            "═" * 60,
            f"Job ID: {job_id}",
            f"Status: {completion_status}",
            f"Duration: {duration_str}",
            "",
        ]

        # Results summary
        summary_lines.append("Results Summary:")
        summary_lines.append(f"  • Total Rows: {results.summary.total_rows}")
        summary_lines.append(f"  • Total Errors: {results.summary.total_errors}")
        summary_lines.append(f"  • Error Rate: {error_rate:.1f}%")
        summary_lines.append("")

        if has_errors:
            # Error breakdown by type
            summary_lines.append("Error Breakdown by Type:")
            for error_type, count in results.summary.error_types.items():
                # Clean enum representation
                type_name = error_type.value if hasattr(error_type, "value") else str(error_type)
                percentage = (count / results.summary.total_errors * 100) if results.summary.total_errors > 0 else 0
                summary_lines.append(f"  • {type_name}: {count} errors ({percentage:.1f}%)")
            summary_lines.append("")

            # Get error breakdown
            error_breakdown = self._create_error_breakdown(results)

            # Top 5 problematic columns
            if error_breakdown.get("errors_by_column"):
                sorted_columns = sorted(
                    error_breakdown["errors_by_column"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]

                summary_lines.append("Top 5 Problematic Columns:")
                for column, count in sorted_columns:
                    summary_lines.append(f"  • {column}: {count} errors")
                summary_lines.append("")

            # Sample errors (first 3)
            if error_breakdown.get("sample_errors"):
                sample_count = min(3, len(error_breakdown["sample_errors"]))
                summary_lines.append(f"Sample Errors (first {sample_count}):")
                for error in error_breakdown["sample_errors"][:3]:
                    value_preview = str(error["current_value"])[:50]
                    summary_lines.append(f"  • Row {error['row']}, {error['column']}: '{value_preview}'")
                summary_lines.append("")

        summary_lines.append("═" * 60)

        # Log each line separately
        for line in summary_lines:
            if level == "WARNING":
                logger.warning(line)
            elif level == "ERROR":
                logger.error(line)
            else:
                logger.info(line)

    async def log_failure_with_context(self, job_id: str, error: Exception, context: Dict[str, Any]) -> None:
        """
        Log job failure with comprehensive error context.

        Args:
            job_id: Job identifier
            error: Exception that caused the failure
            context: Error context information
        """
        failure_context = {
            "job_lifecycle_event": "failure",
            "job_id": job_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failure_context": context,
            "timestamp": datetime.now().isoformat(),
        }

        logger.error(f"Job {job_id} failed: {str(error)} - {failure_context}")

    async def log_status_update_failure(self, job_id: str, intended_status: str, error: Exception) -> None:
        """
        Log failures to update job status.

        Args:
            job_id: Job identifier
            intended_status: Status that was intended to be set
            error: Exception that occurred during status update
        """
        context = {
            "job_lifecycle_event": "status_update_failure",
            "job_id": job_id,
            "intended_status": intended_status,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
        }

        logger.error(f"Failed to update job {job_id} status to {intended_status}: {str(error)} - {context}")

    async def log_results_save_operation(
        self,
        job_id: str,
        success: bool,
        storage_info: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """
        Log results save operations.

        Args:
            job_id: Job identifier
            success: Whether the save operation was successful
            storage_info: Information about where results were saved
            error: Exception if save failed
        """
        context = {
            "job_lifecycle_event": "results_save",
            "job_id": job_id,
            "save_success": success,
            "timestamp": datetime.now().isoformat(),
        }

        if storage_info:
            context["storage_info"] = storage_info

        if error:
            context["error_type"] = type(error).__name__
            context["error_message"] = str(error)

        level = "INFO" if success else "ERROR"
        message = f"Job {job_id} results save {'succeeded' if success else 'failed'}"
        if storage_info and success:
            message += f" to {storage_info.get('location', 'unknown location')}"

        if level == "WARNING":
            logger.warning(f"{message} - {context}")
        elif level == "ERROR":
            logger.error(f"{message} - {context}")
        else:
            logger.info(f"{message} - {context}")

    def _create_error_breakdown(self, results: ValidationResults) -> Dict[str, Any]:
        """
        Create a detailed breakdown of validation errors.

        Args:
            results: Validation results

        Returns:
            Error breakdown dictionary
        """
        breakdown = {
            "errors_by_type": results.summary.error_types,
            "errors_by_column": {},
            "sample_errors": [],
        }

        # Group errors by column
        for error in results.validation_results:
            column = error.column
            if column not in breakdown["errors_by_column"]:
                breakdown["errors_by_column"][column] = 0
            breakdown["errors_by_column"][column] += 1

        # Include sample errors (first 10)
        for error in results.validation_results[:10]:
            breakdown["sample_errors"].append(
                {
                    "row": error.row,
                    "column": error.column,
                    "error_type": error.error_type.value,
                    "current_value": error.current_value,
                    "valid_options": error.valid_options,
                }
            )

        return breakdown
