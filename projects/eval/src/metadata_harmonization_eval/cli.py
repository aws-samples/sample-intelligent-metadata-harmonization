# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
CLI interface for the evaluation package.

This module provides the command-line interface for running evaluations
on metadata harmonization datasets.
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple

import click
from loguru import logger

from .config import load_config, ConfigurationError
from .logging_config import LoggingConfig
from .models import EvaluationConfig
from .orchestrator import EvaluationOrchestrator


# ============================================================================
# Subtask 7.2: Helper Functions for CLI Execution Logic
# ============================================================================


def _configure_logging(verbose: bool, output_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Configure logging based on verbose flag and output directory.

    Args:
        verbose: Whether to enable verbose logging
        output_dir: Optional output directory for log files

    Returns:
        Path to log file if file logging is enabled, None otherwise
    """
    # Use the centralized logging configuration
    log_file = None

    if output_dir:
        # Create a session-specific log file
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = output_dir / f"evaluation_{timestamp}.log"

    LoggingConfig.configure_logging(
        verbose=verbose,
        log_file=log_file,
        log_level="DEBUG" if verbose else "INFO",
    )

    return log_file


def _parse_and_validate_arguments(
    dataset_paths: Tuple[Path, ...],
    auto_discover: Optional[Path],
    error_rate_filter: Optional[str],
    dataset_pattern: Optional[str],
    batch: bool,
) -> List:
    """
    Parse and validate command-line arguments to get dataset pairs.

    Args:
        dataset_paths: Explicitly provided dataset paths
        auto_discover: Directory to auto-discover datasets
        error_rate_filter: Filter by error rate pattern
        dataset_pattern: Filter by dataset name pattern
        batch: Whether batch mode is enabled

    Returns:
        List of DatasetPair objects

    Raises:
        click.ClickException: If arguments are invalid
    """
    from .dataset_loader import DatasetLoader
    from .models import DatasetPair

    loader = DatasetLoader()
    dataset_pairs = []

    # Check for conflicting options
    if dataset_paths and auto_discover:
        raise click.ClickException("Cannot use both explicit dataset paths and --auto-discover. " "Choose one method.")

    if not dataset_paths and not auto_discover:
        raise click.ClickException("No datasets specified. Provide dataset paths or use --auto-discover.")

    # Auto-discovery mode (Subtask 7.4)
    if auto_discover:
        logger.info(f"Auto-discovering datasets in: {auto_discover}")
        discovered = loader.discover_datasets(auto_discover)

        if not discovered:
            raise click.ClickException(f"No dataset pairs found in {auto_discover}")

        logger.info(f"Found {len(discovered)} dataset pairs")

        # Apply filters
        if error_rate_filter:
            discovered = [dp for dp in discovered if error_rate_filter.lower() in dp.dataset_name.lower()]
            logger.info(f"After error rate filter '{error_rate_filter}': " f"{len(discovered)} datasets")

        if dataset_pattern:
            discovered = [dp for dp in discovered if dataset_pattern.lower() in dp.dataset_name.lower()]
            logger.info(f"After name pattern filter '{dataset_pattern}': " f"{len(discovered)} datasets")

        if not discovered:
            raise click.ClickException("No datasets match the specified filters")

        # Display found datasets and prompt for confirmation
        _display_discovered_datasets(discovered)

        if not _confirm_dataset_selection(discovered, batch):
            logger.info("Evaluation cancelled by user")
            sys.exit(0)

        dataset_pairs = discovered

    # Explicit dataset paths mode
    else:
        logger.info(f"Processing {len(dataset_paths)} dataset path(s)")

        for csv_path in dataset_paths:
            # Try to find corresponding ground truth JSON
            json_path = _find_ground_truth_for_csv(csv_path)

            if not json_path:
                logger.warning(f"No ground truth JSON found for {csv_path.name}, skipping")
                continue

            # Validate the pair
            if not loader.validate_dataset_pair(csv_path, json_path):
                logger.warning(f"Invalid dataset pair: {csv_path.name}, skipping")
                continue

            # Extract dataset name and error rate
            dataset_name = csv_path.stem
            error_rate = _extract_error_rate_from_filename(dataset_name)

            dataset_pair = DatasetPair(
                csv_path=csv_path,
                ground_truth_path=json_path,
                dataset_name=dataset_name,
                error_rate=error_rate,
            )
            dataset_pairs.append(dataset_pair)
            logger.info(f"  ✓ {dataset_name} (error rate: {error_rate:.1%})")

    return dataset_pairs


def _find_ground_truth_for_csv(csv_path: Path) -> Optional[Path]:
    """
    Find the corresponding ground truth JSON file for a CSV dataset.

    Args:
        csv_path: Path to CSV dataset file

    Returns:
        Path to ground truth JSON file, or None if not found
    """
    # Try common naming patterns
    base_name = csv_path.stem
    json_patterns = [
        csv_path.parent / f"{base_name}_mappings.json",
        csv_path.parent / f"{base_name}.json",
        csv_path.with_suffix(".json"),
    ]

    for json_path in json_patterns:
        if json_path.exists():
            return json_path

    return None


def _extract_error_rate_from_filename(filename: str) -> float:
    """
    Extract error rate from dataset filename.

    Args:
        filename: Dataset filename (e.g., "dataset_1_err40")

    Returns:
        Error rate as float (e.g., 0.40)
    """
    import re

    # Look for pattern like "err40", "err50", etc.
    match = re.search(r"err(\d+)", filename.lower())
    if match:
        error_percentage = int(match.group(1))
        return error_percentage / 100.0

    # Default to 0.0 if not found
    return 0.0


def _load_evaluation_config(
    config_path: Optional[Path],
    output_dir: Path,
    report_format: str,
    verbose: bool,
) -> EvaluationConfig:
    """
    Load or create evaluation configuration.

    Uses the config module's load_config function which provides:
    - Comprehensive validation of required fields
    - Graceful error handling with helpful messages
    - Automatic defaults for optional fields
    - Path existence checks

    Args:
        config_path: Path to config file (optional)
        output_dir: Output directory override
        report_format: Report format override
        verbose: Verbose logging flag

    Returns:
        EvaluationConfig instance

    Raises:
        click.ClickException: If config loading fails
    """
    try:
        # Use the config module's load_config function for better validation
        eval_config = load_config(config_path)

        # Apply CLI overrides
        eval_config.output_directory = output_dir
        eval_config.verbose_logging = verbose

        # Set report formats based on CLI option
        if report_format == "json":
            eval_config.report_formats = ["json"]
        elif report_format == "markdown":
            eval_config.report_formats = ["markdown"]
        else:  # both
            eval_config.report_formats = ["json", "markdown"]

        logger.info(f"Output directory: {eval_config.output_directory}")
        logger.info(f"Report formats: {', '.join(eval_config.report_formats)}")

        return eval_config

    except ConfigurationError as e:
        raise click.ClickException(f"Configuration error: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load configuration: {e}")


async def _run_single_evaluation(
    orchestrator: EvaluationOrchestrator,
    dataset_pair,
) -> bool:
    """
    Run evaluation on a single dataset.

    Args:
        orchestrator: Evaluation orchestrator instance
        dataset_pair: Dataset pair to evaluate

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("")
        logger.info("Starting single dataset evaluation...")
        logger.info(f"Dataset: {dataset_pair.dataset_name}")

        result = await orchestrator.evaluate_dataset(dataset_pair)

        # Print summary
        _print_evaluation_summary(result)

        return True

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return False


async def _run_batch_evaluation(
    orchestrator: EvaluationOrchestrator,
    dataset_pairs: List,
) -> bool:
    """
    Run batch evaluation on multiple datasets.

    Args:
        orchestrator: Evaluation orchestrator instance
        dataset_pairs: List of dataset pairs to evaluate

    Returns:
        True if at least one dataset succeeded, False otherwise
    """
    try:
        logger.info("")
        logger.info("Starting batch evaluation...")
        logger.info(f"Total datasets: {len(dataset_pairs)}")

        batch_result = await orchestrator.evaluate_batch(dataset_pairs)

        # Print batch summary
        _print_batch_summary(batch_result)

        return True

    except Exception as e:
        logger.error(f"Batch evaluation failed: {e}")
        return False


# ============================================================================
# Subtask 7.1: Main CLI Command Structure
# ============================================================================


@click.command()
@click.argument(
    "dataset_paths",
    nargs=-1,
    type=click.Path(exists=True, path_type=Path),
    required=False,
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to evaluation configuration YAML file",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default="evaluation_results",
    help="Output directory for evaluation results (default: evaluation_results)",
)
@click.option(
    "--format",
    "-f",
    "report_format",
    type=click.Choice(["json", "markdown", "both"], case_sensitive=False),
    default="both",
    help="Report format to generate (default: both)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging output",
)
@click.option(
    "--batch",
    "-b",
    is_flag=True,
    help="Run batch evaluation mode on multiple datasets",
)
@click.option(
    "--auto-discover",
    "-a",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Auto-discover datasets in the specified directory",
)
@click.option(
    "--error-rate-filter",
    type=str,
    help="Filter datasets by error rate pattern (e.g., 'err40', 'err50')",
)
@click.option(
    "--dataset-pattern",
    type=str,
    help="Filter datasets by name pattern (e.g., 'synthetic_cyclospora')",
)
@click.option(
    "--program-id",
    type=str,
    help="Override schema program ID from config",
)
@click.option(
    "--core-id",
    type=str,
    help="Override schema core ID from config",
)
def evaluate(
    dataset_paths: Tuple[Path, ...],
    config: Optional[Path],
    output_dir: Path,
    report_format: str,
    verbose: bool,
    batch: bool,
    auto_discover: Optional[Path],
    error_rate_filter: Optional[str],
    dataset_pattern: Optional[str],
    program_id: Optional[str],
    core_id: Optional[str],
):
    """
    Run evaluation on metadata harmonization datasets.

    DATASET_PATHS: One or more paths to CSV dataset files. If not provided,
    use --auto-discover to find datasets automatically.

    Examples:

        # Evaluate a single dataset
        mh-eval data/synthetic_dataset/dataset_1_err40.csv

        # Evaluate multiple datasets
        mh-eval dataset1.csv dataset2.csv dataset3.csv

        # Batch evaluation with custom config
        mh-eval --batch --config eval_config.yaml dataset*.csv

        # Auto-discover and evaluate all datasets
        mh-eval --auto-discover data/synthetic_dataset --batch

        # Auto-discover with filtering
        mh-eval --auto-discover data/synthetic_dataset --error-rate-filter err40

        # Verbose output with JSON reports only
        mh-eval --verbose --format json dataset.csv
    """
    # ========================================================================
    # Subtask 7.2: CLI Execution Logic
    # ========================================================================

    exit_code = 0

    try:
        # Step 1: Initialize logging based on verbose flag
        # Create output directory early so we can log to it
        output_dir.mkdir(parents=True, exist_ok=True)
        _configure_logging(verbose, output_dir)

        logger.info("Metadata Harmonization Evaluation Tool")
        logger.info("=" * 60)

        # Step 2: Parse and validate command-line arguments
        try:
            dataset_pairs = _parse_and_validate_arguments(
                dataset_paths=dataset_paths,
                auto_discover=auto_discover,
                error_rate_filter=error_rate_filter,
                dataset_pattern=dataset_pattern,
                batch=batch,
            )
        except click.ClickException as e:
            logger.error(str(e))
            sys.exit(1)

        if not dataset_pairs:
            logger.error("No datasets to evaluate. Provide dataset paths or use --auto-discover.")
            sys.exit(1)

        # Step 3: Load or create EvaluationConfig
        eval_config = _load_evaluation_config(
            config_path=config,
            output_dir=output_dir,
            report_format=report_format,
            verbose=verbose,
        )

        # Override schema IDs if provided
        if program_id:
            eval_config.schema_program_id = program_id
            logger.info(f"Using program ID: {program_id}")
        if core_id:
            eval_config.schema_core_id = core_id
            logger.info(f"Using core ID: {core_id}")

        # Step 4: Create EvaluationOrchestrator instance
        logger.info("Initializing evaluation orchestrator...")
        orchestrator = EvaluationOrchestrator(eval_config)

        # Step 5: Execute evaluation (single or batch mode)
        import asyncio

        if batch or len(dataset_pairs) > 1:
            # Batch evaluation mode
            logger.info(f"Running batch evaluation on {len(dataset_pairs)} datasets")
            result = asyncio.run(_run_batch_evaluation(orchestrator, dataset_pairs))
            exit_code = 0 if result else 1
        else:
            # Single dataset evaluation mode
            logger.info("Running single dataset evaluation")
            result = asyncio.run(_run_single_evaluation(orchestrator, dataset_pairs[0]))
            exit_code = 0 if result else 1

        if exit_code == 0:
            logger.info("=" * 60)
            logger.info("✓ Evaluation completed successfully")
        else:
            logger.error("=" * 60)
            logger.error("✗ Evaluation completed with errors")

        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.warning("\nEvaluation interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(f"Fatal error during evaluation: {e}")
        if verbose:
            logger.exception("Detailed error traceback:")
        sys.exit(1)


# ============================================================================
# Subtask 7.3: Progress Indicators and Output
# ============================================================================


def _print_evaluation_summary(result) -> None:
    """
    Print summary of evaluation results.

    Args:
        result: EvaluationResult instance
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Dataset: {result.dataset_name}")
    logger.info(f"Session ID: {result.session_id}")
    logger.info(f"Error Rate: {result.error_rate:.1%}")
    logger.info("")
    logger.info("Accuracy Metrics:")
    logger.info(f"  Precision: {result.accuracy_metrics.precision:.3f}")
    logger.info(f"  Recall:    {result.accuracy_metrics.recall:.3f}")
    logger.info(f"  F1 Score:  {result.accuracy_metrics.f1_score:.3f}")
    logger.info(f"  Accuracy:  {result.accuracy_metrics.accuracy:.3f}")
    logger.info("")
    logger.info("Performance Metrics:")
    logger.info(f"  Total Duration:     {result.performance_metrics.total_duration_seconds:.2f}s")
    logger.info(f"  Per-Record Time:    {result.performance_metrics.per_record_duration_ms:.2f}ms")
    logger.info(f"  Records/Second:     {result.performance_metrics.records_per_second:.2f}")
    logger.info("")
    logger.info("Confidence Metrics:")
    logger.info(f"  Mean Confidence:    {result.confidence_metrics.mean_confidence:.3f}")
    logger.info(f"  Median Confidence:  {result.confidence_metrics.median_confidence:.3f}")
    logger.info("")
    logger.info("Error Analysis:")
    logger.info(f"  Total Errors:       {result.error_analysis.total_errors}")
    logger.info(f"  Detected:           {result.error_analysis.detected_errors}")
    logger.info(f"  Missed:             {result.error_analysis.missed_errors}")
    logger.info(f"  False Alarms:       {result.error_analysis.false_alarms}")
    logger.info("=" * 60)


def _print_batch_summary(batch_result) -> None:
    """
    Print summary of batch evaluation results.

    Args:
        batch_result: BatchEvaluationResult instance
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("BATCH EVALUATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Batch ID: {batch_result.batch_id}")
    logger.info(f"Total Datasets: {len(batch_result.datasets)}")
    logger.info("")
    logger.info("Aggregate Metrics:")
    logger.info(f"  Average Precision: {batch_result.average_precision:.3f}")
    logger.info(f"  Average Recall:    {batch_result.average_recall:.3f}")
    logger.info(f"  Average F1:        {batch_result.average_f1:.3f}")
    logger.info("")
    logger.info("Performance Comparison:")
    logger.info(f"  Best Dataset:  {batch_result.best_performing_dataset}")
    logger.info(f"  Worst Dataset: {batch_result.worst_performing_dataset}")
    logger.info("")
    logger.info("Correlation Analysis:")
    logger.info(f"  Error Rate vs Accuracy: {batch_result.error_rate_correlation:.3f}")
    logger.info("")
    logger.info("Individual Dataset Results:")
    logger.info("-" * 60)

    # Sort by F1 score descending
    sorted_results = sorted(
        batch_result.datasets,
        key=lambda r: r.accuracy_metrics.f1_score,
        reverse=True,
    )

    for i, result in enumerate(sorted_results, 1):
        logger.info(
            f"{i:2d}. {result.dataset_name:40s} "
            f"F1: {result.accuracy_metrics.f1_score:.3f} "
            f"(P: {result.accuracy_metrics.precision:.3f}, "
            f"R: {result.accuracy_metrics.recall:.3f})"
        )

    logger.info("=" * 60)


# ============================================================================
# Subtask 7.4: Auto-Discovery Mode
# ============================================================================


def _display_discovered_datasets(dataset_pairs: List) -> None:
    """
    Display found datasets in a formatted table.

    Args:
        dataset_pairs: List of discovered DatasetPair objects
    """
    logger.info("")
    logger.info("Discovered Datasets:")
    logger.info("-" * 80)
    logger.info(f"{'#':<4} {'Dataset Name':<50} {'Error Rate':<12}")
    logger.info("-" * 80)

    for i, dp in enumerate(dataset_pairs, 1):
        logger.info(f"{i:<4} {dp.dataset_name:<50} {dp.error_rate:>10.1%}")

    logger.info("-" * 80)
    logger.info(f"Total: {len(dataset_pairs)} dataset(s)")
    logger.info("")


def _confirm_dataset_selection(
    dataset_pairs: List,
    batch_mode: bool,
) -> bool:
    """
    Prompt user to confirm dataset selection.

    Args:
        dataset_pairs: List of dataset pairs to confirm
        batch_mode: Whether batch mode is enabled

    Returns:
        True if user confirms, False otherwise
    """
    if batch_mode:
        mode_str = "batch evaluation"
    else:
        mode_str = "evaluation"

    # In non-interactive environments, auto-confirm
    if not sys.stdin.isatty():
        logger.info(f"Auto-confirming {mode_str} (non-interactive mode)")
        return True

    try:
        response = click.confirm(
            f"\nProceed with {mode_str} on {len(dataset_pairs)} dataset(s)?",
            default=True,
        )
        return response
    except (KeyboardInterrupt, EOFError):
        return False


if __name__ == "__main__":
    evaluate()
