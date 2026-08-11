# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Logging configuration module for the evaluation package.

This module provides centralized logging configuration using loguru,
with support for different log levels, file logging, and structured output.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


class LoggingConfig:
    """
    Centralized logging configuration for the evaluation package.

    Provides methods to configure loguru with appropriate formatters,
    handlers, and log levels for different execution contexts.
    """

    # Log level mappings
    LOG_LEVELS = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
    }

    # Console log formats
    CONSOLE_FORMAT_VERBOSE = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    CONSOLE_FORMAT_NORMAL = (
        "<green>{time:HH:mm:ss}</green> | " "<level>{level: <8}</level> | " "<level>{message}</level>"
    )

    # File log format (always detailed)
    FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | " "{level: <8} | " "{name}:{function}:{line} | " "{message}"

    @classmethod
    def configure_logging(
        cls,
        verbose: bool = False,
        log_file: Optional[Path] = None,
        log_level: str = "INFO",
    ) -> None:
        """
        Configure loguru logging with console and optional file output.

        Args:
            verbose: Enable verbose logging with detailed context
            log_file: Optional path to log file for persistent logging
            log_level: Base log level (DEBUG, INFO, WARNING, ERROR)
        """
        # Remove any existing loggers
        logger.remove()

        # Validate log level
        if log_level not in cls.LOG_LEVELS:
            log_level = "INFO"

        # Configure console logging
        console_level = "DEBUG" if verbose else log_level
        console_format = cls.CONSOLE_FORMAT_VERBOSE if verbose else cls.CONSOLE_FORMAT_NORMAL

        logger.add(
            sys.stderr,
            format=console_format,
            level=console_level,
            colorize=True,
            backtrace=verbose,
            diagnose=verbose,
        )

        # Configure file logging if requested
        if log_file:
            # Ensure log directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)

            logger.add(
                log_file,
                format=cls.FILE_FORMAT,
                level="DEBUG",  # Always log everything to file
                rotation="10 MB",  # Rotate when file gets large
                retention="7 days",  # Keep logs for a week
                compression="gz",  # Compress old logs
                backtrace=True,
                diagnose=True,
                enqueue=True,  # Thread-safe logging
            )

            logger.debug(f"File logging enabled: {log_file}")

        logger.debug(
            f"Logging configured - Console: {console_level}, " f"Verbose: {verbose}, File: {log_file is not None}"
        )

    @classmethod
    def add_structured_context(cls, **context_fields) -> None:
        """
        Add structured context fields to all subsequent log messages.

        This method uses loguru's contextualize feature to add
        structured data to log messages for better analysis.

        Args:
            **context_fields: Key-value pairs to add as context

        Example:
            >>> LoggingConfig.add_structured_context(
            ...     session_id="eval-123",
            ...     dataset="test_data.csv"
            ... )
        """
        logger.configure(extra=context_fields)

    @classmethod
    def log_evaluation_start(
        cls,
        dataset_name: str,
        session_id: str,
        config_summary: dict,
    ) -> None:
        """
        Log structured information about evaluation start.

        Args:
            dataset_name: Name of dataset being evaluated
            session_id: Unique session identifier
            config_summary: Summary of configuration settings
        """
        logger.info(
            "Evaluation started",
            extra={
                "event_type": "evaluation_start",
                "dataset_name": dataset_name,
                "session_id": session_id,
                "config": config_summary,
            },
        )

    @classmethod
    def log_dataset_loading(
        cls,
        dataset_path: Path,
        ground_truth_path: Path,
        record_count: int,
        error_count: int,
    ) -> None:
        """
        Log structured information about dataset loading.

        Args:
            dataset_path: Path to dataset CSV file
            ground_truth_path: Path to ground truth JSON file
            record_count: Number of records loaded
            error_count: Number of errors in ground truth
        """
        logger.info(
            "Dataset loaded successfully",
            extra={
                "event_type": "dataset_loaded",
                "dataset_path": str(dataset_path),
                "ground_truth_path": str(ground_truth_path),
                "record_count": record_count,
                "error_count": error_count,
            },
        )

    @classmethod
    def log_processor_execution(
        cls,
        session_id: str,
        job_id: str,
        program_id: str,
        core_id: str,
        duration_seconds: float,
        record_count: int,
    ) -> None:
        """
        Log structured information about processor execution.

        Args:
            session_id: Processor session identifier
            job_id: Job identifier
            program_id: Schema program ID
            core_id: Schema core ID
            duration_seconds: Processing duration
            record_count: Number of records processed
        """
        logger.info(
            "Processor execution completed",
            extra={
                "event_type": "processor_completed",
                "session_id": session_id,
                "job_id": job_id,
                "program_id": program_id,
                "core_id": core_id,
                "duration_seconds": duration_seconds,
                "record_count": record_count,
                "records_per_second": record_count / duration_seconds if duration_seconds > 0 else 0,
            },
        )

    @classmethod
    def log_metrics_calculation(
        cls,
        precision: float,
        recall: float,
        f1_score: float,
        accuracy: float,
        confidence_mean: float,
    ) -> None:
        """
        Log structured information about metrics calculation results.

        Args:
            precision: Precision score
            recall: Recall score
            f1_score: F1 score
            accuracy: Overall accuracy
            confidence_mean: Mean confidence score
        """
        logger.info(
            "Metrics calculation completed",
            extra={
                "event_type": "metrics_calculated",
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "accuracy": accuracy,
                "confidence_mean": confidence_mean,
            },
        )

    @classmethod
    def log_report_generation(
        cls,
        report_type: str,
        output_path: Path,
        file_size_bytes: int,
    ) -> None:
        """
        Log structured information about report generation.

        Args:
            report_type: Type of report (json, markdown, batch)
            output_path: Path where report was saved
            file_size_bytes: Size of generated report file
        """
        logger.info(
            "Report generated successfully",
            extra={
                "event_type": "report_generated",
                "report_type": report_type,
                "output_path": str(output_path),
                "file_size_bytes": file_size_bytes,
            },
        )

    @classmethod
    def log_evaluation_completion(
        cls,
        dataset_name: str,
        session_id: str,
        total_duration_seconds: float,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log structured information about evaluation completion.

        Args:
            dataset_name: Name of evaluated dataset
            session_id: Session identifier
            total_duration_seconds: Total evaluation duration
            success: Whether evaluation succeeded
            error_message: Error message if evaluation failed
        """
        if success:
            logger.info(
                "Evaluation completed successfully",
                extra={
                    "event_type": "evaluation_completed",
                    "dataset_name": dataset_name,
                    "session_id": session_id,
                    "duration_seconds": total_duration_seconds,
                    "success": True,
                },
            )
        else:
            logger.error(
                "Evaluation failed",
                extra={
                    "event_type": "evaluation_failed",
                    "dataset_name": dataset_name,
                    "session_id": session_id,
                    "duration_seconds": total_duration_seconds,
                    "success": False,
                    "error_message": error_message,
                },
            )
