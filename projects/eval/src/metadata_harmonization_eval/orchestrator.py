# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Evaluation orchestrator module.

This module coordinates the entire evaluation workflow, managing processor lifecycle,
dataset loading, metrics calculation, and report generation.
"""

import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .dataset_loader import DatasetLoader
from .logging_config import LoggingConfig
from .metrics_engine import MetricsEngine
from .models import (
    BatchEvaluationResult,
    DatasetPair,
    EvaluationConfig,
    EvaluationResult,
)
from .report_generator import ReportGenerator

# Import processor components
try:
    from metadata_harmonization_processor import (
        MetadataHarmonizationProcessor,
        load_processor_settings,
    )
    from metadata_harmonization_processor.models import ProcessorState
except ImportError:
    logger.warning("Could not import processor components. " "Ensure metadata-harmonization-processor is installed.")
    MetadataHarmonizationProcessor = None
    load_processor_settings = None
    ProcessorState = None


class EvaluationError(Exception):
    """Base exception for evaluation errors."""

    pass


class ProcessorInitializationError(EvaluationError):
    """Processor initialization failures."""

    pass


class DatasetProcessingError(EvaluationError):
    """Dataset processing failures."""

    pass


class MetricsCalculationError(EvaluationError):
    """Metrics calculation failures."""

    pass


class EvaluationOrchestrator:
    """
    Orchestrates the evaluation workflow.

    This class manages the complete evaluation process including:
    - Processor session management
    - Dataset loading and processing
    - Metrics calculation
    - Report generation
    """

    def __init__(self, config: EvaluationConfig):
        """
        Initialize orchestrator with evaluation configuration.

        Args:
            config: Evaluation configuration

        Raises:
            EvaluationError: If initialization fails
        """
        self.config = config
        self.dataset_loader = DatasetLoader()

        # Load processor configuration
        try:
            self.processor_config = load_processor_settings(config.processor_config_path)
            logger.info(f"Loaded processor config from {config.processor_config_path}")
        except Exception as e:
            raise EvaluationError(f"Failed to load processor configuration: {e}") from e

        # Create output directory
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {self.config.output_directory}")

    # ========================================================================
    # Subtask 6.1: Processor Session Management
    # ========================================================================

    def _create_session_id(self) -> str:
        """
        Generate unique session ID for evaluation run.

        Returns:
            Session ID in format: eval-{timestamp}-{uuid}

        Example:
            >>> orchestrator._create_session_id()
            'eval-20251028-103045-a1b2c3d4'
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"eval-{timestamp}-{short_uuid}"

        logger.debug(f"Generated session ID: {session_id}")
        return session_id

    def _initialize_processor(self, session_id: str, session_storage_dir: Path) -> MetadataHarmonizationProcessor:
        """
        Initialize MetadataHarmonizationProcessor with evaluation config.

        Args:
            session_id: Unique session identifier
            session_storage_dir: Directory for session storage

        Returns:
            Initialized processor instance

        Raises:
            ProcessorInitializationError: If processor cannot be initialized
        """
        if MetadataHarmonizationProcessor is None:
            raise ProcessorInitializationError(
                "MetadataHarmonizationProcessor not available. " "Install metadata-harmonization-processor package."
            )

        try:
            # Create session storage directory
            session_storage_dir.mkdir(parents=True, exist_ok=True)

            # Configure session for evaluation
            session_config = {
                "storage_dir": str(session_storage_dir),
                "session_type": "file",  # Use file-based session for evaluation
            }

            # Initialize processor
            processor = MetadataHarmonizationProcessor(
                config=self.processor_config,
                session_id=session_id,
                session_config=session_config,
            )

            logger.info(f"Initialized processor with session_id: {session_id}, " f"storage: {session_storage_dir}")

            return processor

        except Exception as e:
            raise ProcessorInitializationError(f"Failed to initialize processor: {e}") from e

    def _cleanup_processor(self, processor: MetadataHarmonizationProcessor) -> None:
        """
        Clean up processor resources.

        Args:
            processor: Processor instance to clean up
        """
        try:
            # Processor cleanup if needed
            # Currently, the processor doesn't require explicit cleanup
            # but this method is here for future extensibility
            logger.debug("Processor cleanup completed")
        except Exception as e:
            logger.warning(f"Error during processor cleanup: {e}")

    def _save_partial_results(
        self,
        dataset_name: str,
        session_id: str,
        error: str,
        stage: str = "unknown",
    ) -> None:
        """
        Save partial results when processing fails.

        This method saves error context and any available partial data
        to help with debugging and recovery.

        Args:
            dataset_name: Name of the dataset being processed
            session_id: Session identifier
            error: Error message
            stage: Pipeline stage where failure occurred
        """
        try:
            import json

            partial_results_dir = self.config.output_directory / session_id
            partial_results_dir.mkdir(parents=True, exist_ok=True)

            error_info = {
                "dataset_name": dataset_name,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "stage": stage,
                "error": error,
                "status": "failed",
            }

            error_path = partial_results_dir / f"{dataset_name}_error.json"
            with open(error_path, "w") as f:
                json.dump(error_info, f, indent=2)

            logger.info(f"Saved partial results to: {error_path}")

        except Exception as e:
            logger.warning(f"Failed to save partial results: {e}")

    # ========================================================================
    # Subtask 6.2: Single Dataset Evaluation
    # ========================================================================

    async def evaluate_dataset(
        self,
        dataset_pair: DatasetPair,
        program_id: Optional[str] = None,
        core_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate a single dataset through the complete pipeline.

        This method:
        1. Loads dataset and ground truth
        2. Initializes processor with unique session
        3. Executes processor pipeline with timing tracking
        4. Calculates all metrics using MetricsEngine
        5. Generates reports using ReportGenerator
        6. Returns EvaluationResult

        Args:
            dataset_pair: Dataset and ground truth file pair
            program_id: Schema program ID (uses config default if not provided)
            core_id: Schema core ID (uses config default if not provided)

        Returns:
            EvaluationResult containing all metrics and analysis

        Raises:
            DatasetProcessingError: If dataset processing fails
            MetricsCalculationError: If metrics calculation fails
        """
        # Use config defaults if not provided
        program_id = program_id or self.config.schema_program_id
        core_id = core_id or self.config.schema_core_id

        logger.info(f"Starting evaluation of dataset: {dataset_pair.dataset_name}")
        logger.info(f"  Error rate: {dataset_pair.error_rate:.1%}")
        logger.info(f"  Program ID: {program_id}, Core ID: {core_id}")

        # Create session ID and storage directory
        session_id = self._create_session_id()
        session_storage_dir = self.config.output_directory / session_id / "session_data"

        # Track evaluation start time
        eval_start_time = time.time()
        timestamp = datetime.now()

        # Log structured evaluation start
        config_summary = {
            "program_id": program_id,
            "core_id": core_id,
            "error_rate": dataset_pair.error_rate,
            "processor_config_path": str(self.config.processor_config_path),
            "output_directory": str(self.config.output_directory),
            "report_formats": self.config.report_formats,
        }
        LoggingConfig.log_evaluation_start(
            dataset_name=dataset_pair.dataset_name,
            session_id=session_id,
            config_summary=config_summary,
        )

        processor = None

        try:
            # Step 1: Load dataset and ground truth
            logger.info("Loading dataset and ground truth...")
            try:
                dataset_df = self.dataset_loader.load_dataset(dataset_pair.csv_path)
                ground_truth = self.dataset_loader.load_ground_truth(dataset_pair.ground_truth_path)
                total_records = len(dataset_df)
                logger.info(f"Loaded {total_records} records")

                # Log structured dataset loading information
                LoggingConfig.log_dataset_loading(
                    dataset_path=dataset_pair.csv_path,
                    ground_truth_path=dataset_pair.ground_truth_path,
                    record_count=total_records,
                    error_count=ground_truth.total_errors,
                )

            except Exception as e:
                logger.error(f"Failed to load dataset: {e}")
                raise DatasetProcessingError(f"Dataset loading failed: {e}") from e

            # Step 2: Initialize processor
            logger.info("Initializing processor...")
            try:
                processor = self._initialize_processor(session_id, session_storage_dir)
            except Exception as e:
                logger.error(f"Failed to initialize processor: {e}")
                raise ProcessorInitializationError(f"Processor initialization failed: {e}") from e

            # Step 3: Execute processor pipeline with timing
            logger.info("Executing processor pipeline...")
            pipeline_start_time = time.time()

            try:
                # Generate job ID for this evaluation
                job_id = f"eval-job-{session_id}"

                # Process the dataset
                # processor.process() now returns CombinedResults containing both validation and schema alignment
                combined_results = await processor.process(
                    metadata_df=dataset_df,
                    program_id=program_id,
                    core_id=core_id,
                    job_id=job_id,
                )

                pipeline_duration = time.time() - pipeline_start_time
                logger.info(f"Pipeline completed in {pipeline_duration:.2f}s")

                # Log structured processor execution information
                LoggingConfig.log_processor_execution(
                    session_id=session_id,
                    job_id=job_id,
                    program_id=program_id,
                    core_id=core_id,
                    duration_seconds=pipeline_duration,
                    record_count=total_records,
                )

                # Get processor state for performance metrics
                processor_state = processor.get_current_state()

            except Exception as e:
                logger.error(f"Pipeline execution failed: {e}")
                # Try to save partial results if available
                self._save_partial_results(
                    dataset_pair.dataset_name,
                    session_id,
                    error=str(e),
                )
                raise DatasetProcessingError(f"Pipeline execution failed: {e}") from e

            # Step 4: Calculate metrics
            logger.info("Calculating metrics...")
            try:
                metrics_engine = MetricsEngine(ground_truth)

                # Calculate accuracy metrics
                accuracy_metrics = metrics_engine.calculate_accuracy_metrics(
                    validation_results=combined_results.validation_results,
                    schema_alignment_results=combined_results.schema_alignment_results,
                )

                # Calculate performance metrics
                performance_metrics = metrics_engine.calculate_performance_metrics(
                    state=processor_state,
                    total_records=total_records,
                )

                # Calculate confidence metrics
                confidence_metrics = metrics_engine.calculate_confidence_metrics(
                    validation_results=combined_results.validation_results
                )

                # Perform error analysis
                error_analysis = metrics_engine.analyze_errors(validation_results=combined_results.validation_results)

                # Calculate per-node correction metrics
                node_metrics = metrics_engine.calculate_node_metrics(
                    validation_results=combined_results.validation_results,
                    schema_alignment_results=combined_results.schema_alignment_results,
                )

                # Calculate cost metrics from token usage
                cost_metrics = None
                try:
                    # Calculate overall cost metrics (model IDs extracted from actual usage)
                    cost_metrics = metrics_engine.calculate_cost_metrics(
                        state=processor_state,
                        pricing_config=self.config.bedrock_pricing,
                        detected_errors_count=accuracy_metrics.true_positives,
                    )

                    # Calculate per-node cost metrics (using each node's own model IDs)
                    node_metrics = metrics_engine.calculate_node_cost_metrics(
                        state=processor_state,
                        pricing_config=self.config.bedrock_pricing,
                        node_metrics=node_metrics,
                    )

                    logger.info(f"Cost metrics calculated: Total=${cost_metrics.total_cost:.4f}")
                except Exception as e:
                    logger.warning(f"Cost metrics calculation failed: {e}. Continuing without cost data.")
                    cost_metrics = None

                logger.info("Metrics calculation completed")

                # Log structured metrics calculation results
                LoggingConfig.log_metrics_calculation(
                    precision=accuracy_metrics.precision,
                    recall=accuracy_metrics.recall,
                    f1_score=accuracy_metrics.f1_score,
                    accuracy=accuracy_metrics.accuracy,
                    confidence_mean=confidence_metrics.mean_confidence,
                )

            except Exception as e:
                logger.error(f"Metrics calculation failed: {e}")
                # Try to save partial results
                self._save_partial_results(
                    dataset_pair.dataset_name,
                    session_id,
                    error=str(e),
                    stage="metrics_calculation",
                )
                raise MetricsCalculationError(f"Metrics calculation failed: {e}") from e

            # Step 5: Create evaluation result
            evaluation_result = EvaluationResult(
                dataset_name=dataset_pair.dataset_name,
                timestamp=timestamp,
                session_id=session_id,
                program_id=program_id,
                core_id=core_id,
                error_rate=dataset_pair.error_rate,
                accuracy_metrics=accuracy_metrics,
                performance_metrics=performance_metrics,
                confidence_metrics=confidence_metrics,
                error_analysis=error_analysis,
                node_metrics=node_metrics,
                total_records=total_records,
                total_ground_truth_errors=ground_truth.total_errors,
                processor_version=getattr(processor, "__version__", "unknown"),
                cost_metrics=cost_metrics,
            )

            # Step 6: Generate reports
            logger.info("Generating reports...")
            try:
                report_generator = ReportGenerator(output_dir=self.config.output_directory / session_id)

                # Generate JSON report
                if "json" in self.config.report_formats:
                    json_path = self.config.output_directory / session_id / f"{dataset_pair.dataset_name}_results.json"
                    report_generator.generate_json_report(evaluation_result, json_path)
                    logger.info(f"JSON report saved to: {json_path}")

                    # Log structured report generation
                    if json_path.exists():
                        LoggingConfig.log_report_generation(
                            report_type="json",
                            output_path=json_path,
                            file_size_bytes=json_path.stat().st_size,
                        )

                # Generate markdown report
                if "markdown" in self.config.report_formats:
                    md_path = self.config.output_directory / session_id / f"{dataset_pair.dataset_name}_summary.md"
                    report_generator.generate_markdown_report(evaluation_result, md_path)
                    logger.info(f"Markdown report saved to: {md_path}")

                    # Log structured report generation
                    if md_path.exists():
                        LoggingConfig.log_report_generation(
                            report_type="markdown",
                            output_path=md_path,
                            file_size_bytes=md_path.stat().st_size,
                        )

            except Exception as e:
                logger.error(f"Report generation failed: {e}")
                # Don't fail the entire evaluation if report generation fails
                logger.warning("Continuing despite report generation failure")

            eval_duration = time.time() - eval_start_time
            logger.info(f"Evaluation completed in {eval_duration:.2f}s: " f"{dataset_pair.dataset_name}")
            logger.info(
                f"  Precision: {accuracy_metrics.precision:.3f}, "
                f"Recall: {accuracy_metrics.recall:.3f}, "
                f"F1: {accuracy_metrics.f1_score:.3f}"
            )

            # Log structured evaluation completion
            LoggingConfig.log_evaluation_completion(
                dataset_name=dataset_pair.dataset_name,
                session_id=session_id,
                total_duration_seconds=eval_duration,
                success=True,
            )

            return evaluation_result

        except Exception as e:
            eval_duration = time.time() - eval_start_time
            logger.error(
                f"Evaluation failed for {dataset_pair.dataset_name}: {e}",
                exc_info=True if self.config.verbose_logging else False,
            )

            # Log structured evaluation failure
            LoggingConfig.log_evaluation_completion(
                dataset_name=dataset_pair.dataset_name,
                session_id=session_id,
                total_duration_seconds=eval_duration,
                success=False,
                error_message=str(e),
            )

            raise DatasetProcessingError(f"Failed to evaluate dataset {dataset_pair.dataset_name}: {e}") from e

        finally:
            # Cleanup processor resources
            if processor is not None:
                self._cleanup_processor(processor)

    # ========================================================================
    # Subtask 6.3: Batch Evaluation
    # ========================================================================

    async def evaluate_batch(
        self,
        dataset_pairs: List[DatasetPair],
        program_id: Optional[str] = None,
        core_id: Optional[str] = None,
    ) -> BatchEvaluationResult:
        """
        Evaluate multiple datasets sequentially and aggregate results.

        This method:
        1. Processes multiple datasets sequentially
        2. Aggregates results across all datasets
        3. Generates batch comparison report
        4. Returns BatchEvaluationResult

        Args:
            dataset_pairs: List of dataset pairs to evaluate
            program_id: Schema program ID (uses config default if not provided)
            core_id: Schema core ID (uses config default if not provided)

        Returns:
            BatchEvaluationResult containing aggregated metrics

        Raises:
            EvaluationError: If batch evaluation fails
        """
        if not dataset_pairs:
            raise EvaluationError("No datasets provided for batch evaluation")

        logger.info(f"Starting batch evaluation of {len(dataset_pairs)} datasets")

        # Generate batch ID
        batch_id = f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        batch_timestamp = datetime.now()

        # Track results and failures
        evaluation_results: List[EvaluationResult] = []
        failed_datasets: List[str] = []

        # Process each dataset sequentially
        for i, dataset_pair in enumerate(dataset_pairs, 1):
            logger.info(f"Processing dataset {i}/{len(dataset_pairs)}: " f"{dataset_pair.dataset_name}")

            try:
                result = await self.evaluate_dataset(
                    dataset_pair=dataset_pair,
                    program_id=program_id,
                    core_id=core_id,
                )
                evaluation_results.append(result)
                logger.info(
                    f"✓ Successfully evaluated {dataset_pair.dataset_name} "
                    f"(F1: {result.accuracy_metrics.f1_score:.3f})"
                )

            except Exception as e:
                # Log detailed error context but continue with remaining datasets
                logger.error(
                    f"✗ Failed to evaluate {dataset_pair.dataset_name}: {e}",
                    exc_info=True if self.config.verbose_logging else False,
                )
                failed_datasets.append(dataset_pair.dataset_name)

                # Save error information for later analysis
                try:
                    self._save_partial_results(
                        dataset_name=dataset_pair.dataset_name,
                        session_id=batch_id,
                        error=str(e),
                        stage="batch_evaluation",
                    )
                except Exception as save_error:
                    logger.warning(f"Could not save error info for {dataset_pair.dataset_name}: " f"{save_error}")

                # Continue with next dataset (error handling from subtask 6.4)
                logger.info(f"Continuing with remaining datasets " f"({len(dataset_pairs) - i} left)")
                continue

        if not evaluation_results:
            raise EvaluationError("All datasets failed to evaluate. No results to aggregate.")

        logger.info(
            f"Batch evaluation completed: " f"{len(evaluation_results)} successful, " f"{len(failed_datasets)} failed"
        )

        # Calculate aggregate metrics
        logger.info("Calculating aggregate metrics...")

        precisions = [r.accuracy_metrics.precision for r in evaluation_results]
        recalls = [r.accuracy_metrics.recall for r in evaluation_results]
        f1_scores = [r.accuracy_metrics.f1_score for r in evaluation_results]

        average_precision = sum(precisions) / len(precisions)
        average_recall = sum(recalls) / len(recalls)
        average_f1 = sum(f1_scores) / len(f1_scores)

        # Find best and worst performing datasets
        best_result = max(evaluation_results, key=lambda r: r.accuracy_metrics.f1_score)
        worst_result = min(evaluation_results, key=lambda r: r.accuracy_metrics.f1_score)

        # Calculate correlation between error rate and accuracy
        error_rates = [r.error_rate for r in evaluation_results]
        accuracies = [r.accuracy_metrics.accuracy for r in evaluation_results]

        error_rate_correlation = self._calculate_correlation(error_rates, accuracies)

        # Aggregate field-level metrics across all datasets
        logger.info("Aggregating field-level metrics across datasets...")
        aggregated_field_metrics = self._aggregate_field_metrics(evaluation_results)
        logger.info(f"Aggregated {len(aggregated_field_metrics)} field metrics")

        # Create batch result with aggregated field metrics
        batch_result = BatchEvaluationResult(
            batch_id=batch_id,
            timestamp=batch_timestamp,
            datasets=evaluation_results,
            average_precision=average_precision,
            average_recall=average_recall,
            average_f1=average_f1,
            best_performing_dataset=best_result.dataset_name,
            worst_performing_dataset=worst_result.dataset_name,
            error_rate_correlation=error_rate_correlation,
            aggregated_field_metrics=aggregated_field_metrics,
        )

        # Generate batch comparison report
        logger.info("Generating batch comparison report...")
        report_generator = ReportGenerator(self.config.output_directory)

        batch_report_path = self.config.output_directory / f"{batch_id}_comparison.md"
        report_generator.generate_batch_report(batch_result, batch_report_path)
        logger.info(f"Batch report saved to: {batch_report_path}")

        # Log structured batch report generation
        if batch_report_path.exists():
            LoggingConfig.log_report_generation(
                report_type="batch",
                output_path=batch_report_path,
                file_size_bytes=batch_report_path.stat().st_size,
            )

        # Log summary
        logger.info("Batch Evaluation Summary:")
        logger.info(f"  Average Precision: {average_precision:.3f}")
        logger.info(f"  Average Recall: {average_recall:.3f}")
        logger.info(f"  Average F1: {average_f1:.3f}")
        logger.info(f"  Best: {best_result.dataset_name} (F1: {best_result.accuracy_metrics.f1_score:.3f})")
        logger.info(f"  Worst: {worst_result.dataset_name} (F1: {worst_result.accuracy_metrics.f1_score:.3f})")
        logger.info(f"  Error Rate Correlation: {error_rate_correlation:.3f}")

        if failed_datasets:
            logger.warning(f"Failed datasets: {', '.join(failed_datasets)}")

        return batch_result

    def _aggregate_field_metrics(self, evaluation_results: List[EvaluationResult]) -> Dict[str, "FieldMetrics"]:
        """
        Aggregate field metrics across multiple evaluation results.

        This method combines field-level metrics from all datasets in a batch,
        summing confusion matrix values and recalculating aggregate metrics.

        Args:
            evaluation_results: List of evaluation results to aggregate

        Returns:
            Dictionary mapping field names to aggregated FieldMetrics
        """
        from collections import Counter
        from .models import FieldMetrics

        # Collect all unique fields across all datasets
        all_fields = set()
        for result in evaluation_results:
            all_fields.update(result.accuracy_metrics.field_metrics.keys())

        aggregated_metrics = {}

        for field_name in all_fields:
            # Initialize aggregation counters
            total_tp = 0
            total_fp = 0
            total_fn = 0
            total_tn = 0
            total_gt_errors = 0
            total_detected_errors = 0
            total_records = 0

            # Aggregate error type counts and detections
            combined_error_type_counts = Counter()
            combined_error_type_detections = Counter()

            # Process each result
            for result in evaluation_results:
                field_metrics = result.accuracy_metrics.field_metrics.get(field_name)

                if field_metrics is None:
                    continue

                # Sum confusion matrix values
                total_tp += field_metrics.true_positives
                total_fp += field_metrics.false_positives
                total_fn += field_metrics.false_negatives
                total_tn += field_metrics.true_negatives

                # Sum volume metrics
                total_gt_errors += field_metrics.total_errors
                total_detected_errors += field_metrics.detected_errors
                total_records += field_metrics.total_records_checked

                # Aggregate error type information
                for error_type, count in field_metrics.error_type_counts.items():
                    combined_error_type_counts[error_type] += count

                    # Calculate detections from detection rate
                    detection_rate = field_metrics.error_type_detection_rates.get(error_type, 0.0)
                    detected = int(detection_rate * count)
                    combined_error_type_detections[error_type] += detected

            # Calculate aggregated metrics
            precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
            recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            accuracy = (
                (total_tp + total_tn) / (total_tp + total_tn + total_fp + total_fn)
                if (total_tp + total_tn + total_fp + total_fn) > 0
                else 0.0
            )

            # Calculate aggregated error type detection rates
            aggregated_detection_rates = {
                error_type: combined_error_type_detections[error_type] / count if count > 0 else 0.0
                for error_type, count in combined_error_type_counts.items()
            }

            # Create aggregated FieldMetrics
            aggregated_metrics[field_name] = FieldMetrics(
                field_name=field_name,
                precision=precision,
                recall=recall,
                f1_score=f1,
                accuracy=accuracy,
                total_errors=total_gt_errors,
                detected_errors=total_tp,  # TP = detected ground truth errors
                missed_errors=total_fn,
                true_positives=total_tp,
                false_positives=total_fp,
                false_negatives=total_fn,
                true_negatives=total_tn,
                total_records_checked=total_records,
                mean_confidence=0.0,  # Can't meaningfully aggregate mean confidence
                median_confidence=0.0,  # Can't meaningfully aggregate median confidence
                error_type_counts=dict(combined_error_type_counts),
                error_type_detection_rates=aggregated_detection_rates,
            )

        logger.info(
            f"Aggregated metrics for {len(aggregated_metrics)} fields across {len(evaluation_results)} datasets"
        )

        return aggregated_metrics

    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient between two lists.

        Args:
            x_values: First list of values
            y_values: Second list of values

        Returns:
            Correlation coefficient between -1 and 1
        """
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        # Calculate means
        mean_x = sum(x_values) / len(x_values)
        mean_y = sum(y_values) / len(y_values)

        # Calculate correlation
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))

        sum_sq_x = sum((x - mean_x) ** 2 for x in x_values)
        sum_sq_y = sum((y - mean_y) ** 2 for y in y_values)

        denominator = (sum_sq_x * sum_sq_y) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator
