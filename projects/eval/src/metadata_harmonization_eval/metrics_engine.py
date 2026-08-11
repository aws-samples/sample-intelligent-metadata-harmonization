# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Metrics engine module for the evaluation package.

This module provides functionality to calculate performance and accuracy metrics
by comparing processor results against ground truth data.
"""

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from .models import (
    AccuracyMetrics,
    ConfidenceMetrics,
    CostMetrics,
    ErrorAnalysis,
    ErrorTypeMetrics,
    FalseNegative,
    FalsePositive,
    FieldMetrics,
    GroundTruth,
    GroundTruthEntry,
    NodeMetrics,
    PerformanceMetrics,
)

# Import processor models with proper type checking
# These imports are required for the evaluation package to work
from metadata_harmonization_processor.models import (
    ProcessorState,
    ValidationResults,
    SchemaAlignmentResults,
)

# Import cost calculator
from .cost_calculator import CostCalculator
from .models import BedrockPricingConfig


class MetricsCalculationError(Exception):
    """Exception raised when metrics calculation fails."""

    pass


class MetricsEngine:
    """
    Engine for calculating performance and accuracy metrics.

    This class compares processor results against ground truth data to calculate
    various metrics including accuracy, precision, recall, confidence distributions,
    and detailed error analysis.
    """

    def __init__(self, ground_truth: GroundTruth):
        """
        Initialize the metrics engine with ground truth data.

        Args:
            ground_truth: Ground truth data containing expected corrections
        """
        self.ground_truth = ground_truth

        # Create lookup structures for efficient comparison
        self._build_lookup_structures()

    def _build_lookup_structures(self) -> None:
        """Build efficient lookup structures from ground truth data."""
        # Map (row, schema_field) -> GroundTruthEntry for quick lookups
        # Use schema_field instead of field because validation results use aligned schema names
        self.error_lookup: Dict[Tuple[int, str], GroundTruthEntry] = {}

        for entry in self.ground_truth.entries:
            key = (entry.row, entry.schema_field)
            self.error_lookup[key] = entry

        logger.debug(f"Built lookup structures for {len(self.error_lookup)} ground truth errors")

    def calculate_accuracy_metrics(
        self,
        validation_results: ValidationResults,
        schema_alignment_results: Optional[SchemaAlignmentResults] = None,
    ) -> AccuracyMetrics:
        """
        Calculate precision, recall, F1 score, and related accuracy metrics.

        This method compares the processor's validation results against ground truth
        to determine how accurately the system detected and corrected errors.

        Args:
            validation_results: Validation results from the processor
            schema_alignment_results: Optional schema alignment results

        Returns:
            AccuracyMetrics containing all accuracy measurements

        Raises:
            MetricsCalculationError: If metrics cannot be calculated
        """
        if validation_results is None:
            raise MetricsCalculationError("validation_results cannot be None")

        logger.info("Calculating accuracy metrics...")

        # Extract detected errors from validation results
        detected_errors = self._extract_detected_errors(validation_results)

        # Calculate confusion matrix values
        true_positives = 0
        false_positives = 0
        false_negatives = 0

        # Track per-field and per-error-type metrics
        field_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "detected": 0, "missed": 0})
        error_type_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "detected": 0})

        # Check each ground truth error to see if it was detected
        for gt_entry in self.ground_truth.entries:
            # Use schema_field for stats since validation results use schema field names
            field_stats[gt_entry.schema_field]["total"] += 1
            error_type_stats[gt_entry.error_type]["total"] += 1

            # Check if this error was detected
            # An error is detected if there's a validation error for the same row/schema_field
            key = (gt_entry.row, gt_entry.schema_field)

            if key in detected_errors:
                # True positive: error was correctly detected
                true_positives += 1
                field_stats[gt_entry.schema_field]["detected"] += 1
                error_type_stats[gt_entry.error_type]["detected"] += 1
            else:
                # False negative: error was missed
                false_negatives += 1
                field_stats[gt_entry.schema_field]["missed"] += 1

        # Check for false positives (detected errors that aren't in ground truth)
        for detected_key in detected_errors:
            if detected_key not in self.error_lookup:
                false_positives += 1

        # Determine total number of records
        # Get max row from ground truth (0-based indexing)
        total_records = max(entry.row for entry in self.ground_truth.entries) + 1 if self.ground_truth.entries else 0

        # Calculate improved true negatives
        # Get unique fields being validated
        validated_fields = set(field_stats.keys())
        for error in validation_results.validation_results:
            validated_fields.add(error.column)

        # Total possible errors = total records × number of fields validated
        total_possible_errors = total_records * len(validated_fields) if validated_fields else 0

        # True negatives = correctly identified non-errors
        true_negatives = total_possible_errors - true_positives - false_positives - false_negatives
        true_negatives = max(0, true_negatives)  # Ensure non-negative

        # Calculate overall metrics
        precision = self._calculate_precision(true_positives, false_positives)
        recall = self._calculate_recall(true_positives, false_negatives)
        f1_score = self._calculate_f1(precision, recall)
        accuracy = self._calculate_accuracy(true_positives, true_negatives, false_positives, false_negatives)

        # Calculate enhanced per-field metrics with full confusion matrix
        field_metrics = self._calculate_field_metrics(field_stats, validation_results, detected_errors, total_records)

        # Calculate per-error-type metrics
        error_type_metrics = self._calculate_error_type_metrics(error_type_stats)

        logger.info(
            f"Accuracy metrics calculated: " f"Precision={precision:.3f}, Recall={recall:.3f}, F1={f1_score:.3f}"
        )

        return AccuracyMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            true_negatives=true_negatives,
            accuracy=accuracy,
            field_metrics=field_metrics,
            error_type_metrics=error_type_metrics,
        )

    def _extract_detected_errors(self, validation_results: ValidationResults) -> Set[Tuple[int, str]]:
        """
        Extract detected errors from validation results.

        Args:
            validation_results: Validation results from processor

        Returns:
            Set of (row, field) tuples for detected errors
        """
        detected = set()

        for error in validation_results.validation_results:
            # Note: ValidationErrorDetail uses 1-based row indexing
            # Ground truth uses 0-based indexing, so we need to convert
            row = error.row - 1  # Convert to 0-based
            field = error.column
            detected.add((row, field))

        logger.debug(f"Extracted {len(detected)} detected errors from validation results")
        return detected

    def _calculate_precision(self, true_positives: int, false_positives: int) -> float:
        """Calculate precision score."""
        if true_positives + false_positives == 0:
            return 0.0
        return true_positives / (true_positives + false_positives)

    def _calculate_recall(self, true_positives: int, false_negatives: int) -> float:
        """Calculate recall score."""
        if true_positives + false_negatives == 0:
            return 0.0
        return true_positives / (true_positives + false_negatives)

    def _calculate_f1(self, precision: float, recall: float) -> float:
        """Calculate F1 score."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def _calculate_accuracy(
        self,
        true_positives: int,
        true_negatives: int,
        false_positives: int,
        false_negatives: int,
    ) -> float:
        """Calculate overall accuracy."""
        total = true_positives + true_negatives + false_positives + false_negatives
        if total == 0:
            return 0.0
        return (true_positives + true_negatives) / total

    def _calculate_field_metrics(
        self,
        field_stats: Dict[str, Dict[str, int]],
        validation_results: ValidationResults,
        detected_errors: Set[Tuple[int, str]],
        total_records: int,
    ) -> Dict[str, FieldMetrics]:
        """
        Calculate comprehensive per-field accuracy metrics.

        This enhanced version calculates full confusion matrix, confidence statistics,
        and error type breakdown for each field.

        Args:
            field_stats: Basic field statistics from initial pass
            validation_results: Full validation results for confidence extraction
            detected_errors: Set of detected error keys
            total_records: Total number of records in dataset

        Returns:
            Dictionary mapping field names to enhanced FieldMetrics
        """
        import statistics

        field_metrics = {}

        # Get all unique fields from both ground truth and validation results
        all_fields = set(field_stats.keys())
        for error in validation_results.validation_results:
            all_fields.add(error.column)

        for field_name in all_fields:
            # Get basic stats (may be empty for fields only in validation results)
            stats = field_stats.get(field_name, {"total": 0, "detected": 0, "missed": 0})
            total_gt_errors = stats["total"]
            detected_gt_errors = stats["detected"]
            missed_errors = stats["missed"]

            # Calculate confusion matrix for this field
            tp = detected_gt_errors  # True positives (ground truth errors detected)
            fn = missed_errors  # False negatives (ground truth errors missed)

            # Count false positives for this field
            fp = 0
            confidence_scores = []

            for error in validation_results.validation_results:
                if error.column != field_name:
                    continue

                row = error.row - 1
                key = (row, field_name)

                # Only collect confidence scores for errors with recommendations
                if error.recommended_value is not None and error.confidence_score is not None:
                    confidence_scores.append(error.confidence_score)

                # If detected but not in ground truth, it's a false positive
                if key not in self.error_lookup:
                    fp += 1

            # Calculate true negatives for this field
            # TN = records where field has no error and none was detected
            tn = total_records - tp - fp - fn
            tn = max(0, tn)  # Ensure non-negative

            # Calculate metrics
            precision = self._calculate_precision(tp, fp)
            recall = self._calculate_recall(tp, fn)
            f1 = self._calculate_f1(precision, recall)
            accuracy = self._calculate_accuracy(tp, tn, fp, fn)

            # Calculate confidence statistics
            mean_conf = statistics.mean(confidence_scores) if confidence_scores else 0.0
            median_conf = statistics.median(confidence_scores) if confidence_scores else 0.0

            # Calculate error type breakdown for this field
            error_type_counts = Counter()
            error_type_detections = Counter()

            for gt_entry in self.ground_truth.entries:
                if gt_entry.schema_field == field_name:
                    error_type_counts[gt_entry.error_type] += 1

                    key = (gt_entry.row, gt_entry.schema_field)
                    if key in detected_errors:
                        error_type_detections[gt_entry.error_type] += 1

            # Calculate detection rates per error type
            error_type_detection_rates = {
                error_type: error_type_detections[error_type] / count if count > 0 else 0.0
                for error_type, count in error_type_counts.items()
            }

            field_metrics[field_name] = FieldMetrics(
                field_name=field_name,
                precision=precision,
                recall=recall,
                f1_score=f1,
                accuracy=accuracy,
                total_errors=total_gt_errors,
                detected_errors=detected_gt_errors,
                missed_errors=missed_errors,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                true_negatives=tn,
                total_records_checked=total_records,
                mean_confidence=mean_conf,
                median_confidence=median_conf,
                error_type_counts=dict(error_type_counts),
                error_type_detection_rates=error_type_detection_rates,
            )

        return field_metrics

    def _calculate_error_type_metrics(self, error_type_stats: Dict[str, Dict[str, int]]) -> Dict[str, ErrorTypeMetrics]:
        """Calculate per-error-type detection metrics."""
        error_type_metrics = {}

        for error_type, stats in error_type_stats.items():
            total = stats["total"]
            detected = stats["detected"]

            detection_rate = detected / total if total > 0 else 0.0

            error_type_metrics[error_type] = ErrorTypeMetrics(
                error_type=error_type,
                detection_rate=detection_rate,
                total_count=total,
                detected_count=detected,
            )

        return error_type_metrics

    def calculate_performance_metrics(self, state: ProcessorState, total_records: int) -> PerformanceMetrics:
        """
        Calculate timing and throughput performance metrics.

        This method extracts timing data from the processor state and calculates
        various performance measurements including duration, throughput, and
        stage-specific timings.

        Args:
            state: Processor state containing timing information
            total_records: Total number of records processed

        Returns:
            PerformanceMetrics containing all performance measurements

        Raises:
            MetricsCalculationError: If metrics cannot be calculated
        """
        if state is None:
            raise MetricsCalculationError("state cannot be None")

        logger.info("Calculating performance metrics...")

        # Get total processing duration
        total_duration = state.get_processing_duration()
        if total_duration is None:
            logger.warning("Processing duration not available, using 0.0")
            total_duration = 0.0

        # Calculate per-record metrics
        per_record_duration_ms = 0.0
        records_per_second = 0.0

        if total_records > 0 and total_duration > 0:
            per_record_duration_ms = (total_duration * 1000) / total_records
            records_per_second = total_records / total_duration

        # Extract stage timings from state
        # Note: The processor doesn't currently track stage-specific timings
        # We'll use placeholders for now and can enhance this later
        schema_alignment_duration = 0.0
        validation_duration = 0.0
        prediction_duration = 0.0

        # Try to extract timing information if available
        if hasattr(state, "transformation_summary") and state.transformation_summary:
            # Check if timing info is in transformation summary
            if "timing" in state.transformation_summary:
                timing = state.transformation_summary["timing"]
                schema_alignment_duration = timing.get("schema_alignment", 0.0)
                validation_duration = timing.get("validation", 0.0)
                prediction_duration = timing.get("prediction", 0.0)

        # Calculate peak memory usage
        # Note: This would require memory profiling during execution
        # For now, we'll use a placeholder
        peak_memory_mb = 0.0

        logger.info(
            f"Performance metrics calculated: "
            f"Duration={total_duration:.2f}s, "
            f"Throughput={records_per_second:.2f} records/s"
        )

        return PerformanceMetrics(
            total_duration_seconds=total_duration,
            per_record_duration_ms=per_record_duration_ms,
            records_per_second=records_per_second,
            schema_alignment_duration=schema_alignment_duration,
            validation_duration=validation_duration,
            prediction_duration=prediction_duration,
            peak_memory_mb=peak_memory_mb,
        )

    def calculate_confidence_metrics(self, validation_results: ValidationResults) -> ConfidenceMetrics:
        """
        Analyze confidence score distribution and correlation with accuracy.

        This method extracts confidence scores from validation results and
        calculates statistical measures and distribution histograms.

        Args:
            validation_results: Validation results containing confidence scores

        Returns:
            ConfidenceMetrics containing confidence analysis

        Raises:
            MetricsCalculationError: If metrics cannot be calculated
        """
        if validation_results is None:
            raise MetricsCalculationError("validation_results cannot be None")

        logger.info("Calculating confidence metrics...")

        # Extract confidence scores from validation results
        # Only consider errors with recommendations (corrections made)
        confidence_scores = []
        high_confidence_predictions = []  # confidence > 0.8
        low_confidence_predictions = []  # confidence < 0.5

        for error in validation_results.validation_results:
            # Only collect confidence scores for errors with recommendations
            if error.recommended_value is not None and error.confidence_score is not None:
                score = error.confidence_score
                confidence_scores.append(score)

                if score > 0.8:
                    high_confidence_predictions.append(error)
                elif score < 0.5:
                    low_confidence_predictions.append(error)

        if not confidence_scores:
            logger.warning("No confidence scores found in validation results")
            return ConfidenceMetrics(
                mean_confidence=0.0,
                median_confidence=0.0,
                std_deviation=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                confidence_distribution={},
                high_confidence_accuracy=0.0,
                low_confidence_accuracy=0.0,
            )

        # Calculate statistical measures
        import statistics

        mean_confidence = statistics.mean(confidence_scores)
        median_confidence = statistics.median(confidence_scores)
        std_deviation = statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.0
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)

        # Generate confidence distribution histogram
        confidence_distribution = self._calculate_confidence_distribution(confidence_scores)

        # Calculate accuracy for high vs low confidence predictions
        high_confidence_accuracy = self._calculate_confidence_accuracy(high_confidence_predictions, validation_results)
        low_confidence_accuracy = self._calculate_confidence_accuracy(low_confidence_predictions, validation_results)

        logger.info(
            f"Confidence metrics calculated: "
            f"Mean={mean_confidence:.3f}, Median={median_confidence:.3f}, "
            f"StdDev={std_deviation:.3f}"
        )

        return ConfidenceMetrics(
            mean_confidence=mean_confidence,
            median_confidence=median_confidence,
            std_deviation=std_deviation,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            confidence_distribution=confidence_distribution,
            high_confidence_accuracy=high_confidence_accuracy,
            low_confidence_accuracy=low_confidence_accuracy,
        )

    def _calculate_confidence_distribution(self, confidence_scores: List[float]) -> Dict[str, int]:
        """
        Calculate confidence distribution histogram.

        Args:
            confidence_scores: List of confidence scores

        Returns:
            Dictionary mapping bucket ranges to counts
        """
        # Define buckets: 0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0
        buckets = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }

        for score in confidence_scores:
            if score < 0.2:
                buckets["0.0-0.2"] += 1
            elif score < 0.4:
                buckets["0.2-0.4"] += 1
            elif score < 0.6:
                buckets["0.4-0.6"] += 1
            elif score < 0.8:
                buckets["0.6-0.8"] += 1
            else:
                buckets["0.8-1.0"] += 1

        return buckets

    def _calculate_confidence_accuracy(self, predictions: List, validation_results: ValidationResults) -> float:
        """
        Calculate accuracy for a subset of predictions.

        Args:
            predictions: List of validation error details
            validation_results: Full validation results

        Returns:
            Accuracy score for the subset
        """
        if not predictions:
            return 0.0

        # Count how many of these predictions match ground truth
        correct = 0

        for pred in predictions:
            row = pred.row - 1  # Convert to 0-based
            field = pred.column
            key = (row, field)

            # Check if this is a true positive
            if key in self.error_lookup:
                correct += 1

        return correct / len(predictions)

    def calculate_node_metrics(
        self, validation_results: ValidationResults, schema_alignment_results: Optional[SchemaAlignmentResults] = None
    ) -> Dict[str, NodeMetrics]:
        """
        Calculate performance metrics for each correction node in the enum correction pipeline.

        This method analyzes which node made each correction recommendation and calculates
        success rates, confidence statistics, and error type breakdowns for each node.
        Also includes schema alignment as a correction node if results are available.

        Args:
            validation_results: Validation results containing correction recommendations
            schema_alignment_results: Optional schema alignment results containing column corrections

        Returns:
            Dictionary mapping node names to NodeMetrics
        """
        import statistics
        from collections import defaultdict

        logger.info("Calculating per-node correction metrics...")

        # Group corrections by node
        node_corrections: Dict[str, List] = defaultdict(list)

        # Collect all corrections with their node attribution
        for error in validation_results.validation_results:
            # Only consider errors with recommendations from correction nodes
            if error.recommended_value and error.correction_node:
                node_name = error.correction_node
                node_corrections[node_name].append(error)

        # Calculate metrics for each node
        node_metrics = {}

        for node_name, corrections in node_corrections.items():
            total_corrections = len(corrections)
            successful_corrections = 0
            confidence_scores = []
            high_confidence_count = 0
            error_type_breakdown: Dict[str, int] = Counter()

            # Analyze each correction from this node
            for correction in corrections:
                row = correction.row - 1  # Convert to 0-based
                field = correction.column
                key = (row, field)
                confidence_scores.append(correction.confidence_score)

                if correction.confidence_score > 0.8:
                    high_confidence_count += 1

                # Check if this correction matches ground truth
                if key in self.error_lookup:
                    gt_entry = self.error_lookup[key]

                    # Count error type
                    error_type_breakdown[gt_entry.error_type] += 1

                    # Check if recommended value matches ground truth original
                    if correction.recommended_value == gt_entry.original:
                        successful_corrections += 1

            # Calculate statistics
            success_rate = successful_corrections / total_corrections if total_corrections > 0 else 0.0
            mean_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.0
            median_confidence = statistics.median(confidence_scores) if confidence_scores else 0.0
            high_confidence_percentage = high_confidence_count / total_corrections if total_corrections > 0 else 0.0

            node_metrics[node_name] = NodeMetrics(
                node_name=node_name,
                total_corrections=total_corrections,
                successful_corrections=successful_corrections,
                success_rate=success_rate,
                mean_confidence=mean_confidence,
                median_confidence=median_confidence,
                high_confidence_count=high_confidence_count,
                high_confidence_percentage=high_confidence_percentage,
                error_type_breakdown=dict(error_type_breakdown),
            )

            logger.debug(
                f"Node {node_name}: {total_corrections} corrections, "
                f"{success_rate:.1%} success rate, "
                f"mean confidence {mean_confidence:.3f}"
            )

        # Add schema alignment metrics if available
        if schema_alignment_results and schema_alignment_results.schema_alignment_results:
            logger.info("Processing schema alignment corrections...")

            changes = schema_alignment_results.schema_alignment_results
            total_corrections = len(changes)
            successful_corrections = total_corrections  # All schema alignment changes are successful

            # Extract confidence scores from changes
            confidence_scores = [change.confidence_score for change in changes if change.confidence_score]
            high_confidence_count = sum(1 for score in confidence_scores if score > 0.8)

            # Calculate error type breakdown based on change types
            error_type_breakdown: Dict[str, int] = Counter()
            for change in changes:
                # Map change types to error type categories
                error_type_breakdown[change.change_type] += 1

            # Calculate statistics
            mean_confidence = statistics.mean(confidence_scores) if confidence_scores else 1.0
            median_confidence = statistics.median(confidence_scores) if confidence_scores else 1.0
            high_confidence_percentage = high_confidence_count / total_corrections if total_corrections > 0 else 0.0

            node_metrics["schema_alignment"] = NodeMetrics(
                node_name="schema_alignment",
                total_corrections=total_corrections,
                successful_corrections=successful_corrections,
                success_rate=1.0,  # Schema alignment always succeeds
                mean_confidence=mean_confidence,
                median_confidence=median_confidence,
                high_confidence_count=high_confidence_count,
                high_confidence_percentage=high_confidence_percentage,
                error_type_breakdown=dict(error_type_breakdown),
            )

            logger.info(
                f"Schema alignment: {total_corrections} corrections, "
                f"100.0% success rate, "
                f"mean confidence {mean_confidence:.3f}"
            )

        logger.info(f"Calculated metrics for {len(node_metrics)} correction nodes")
        return node_metrics

    def analyze_errors(self, validation_results: ValidationResults) -> ErrorAnalysis:
        """
        Perform detailed error pattern analysis.

        This method categorizes errors by type, identifies common failure patterns,
        and tracks false positives and false negatives with context.

        Args:
            validation_results: Validation results from processor

        Returns:
            ErrorAnalysis containing detailed error breakdown

        Raises:
            MetricsCalculationError: If analysis cannot be performed
        """
        if validation_results is None:
            raise MetricsCalculationError("validation_results cannot be None")

        logger.info("Analyzing error patterns...")

        # Extract detected errors
        detected_errors = self._extract_detected_errors(validation_results)

        # Track statistics
        total_errors = len(self.ground_truth.entries)
        detected_errors_count = 0
        missed_errors_count = 0
        false_alarms_count = 0

        # Track false positives and false negatives
        false_positives_list: List[FalsePositive] = []
        false_negatives_list: List[FalseNegative] = []

        # Count error types
        error_type_counter = Counter()

        # Analyze each ground truth error
        for gt_entry in self.ground_truth.entries:
            error_type_counter[gt_entry.error_type] += 1

            # Use schema_field for comparison since validation results use schema field names
            key = (gt_entry.row, gt_entry.schema_field)

            if key in detected_errors:
                detected_errors_count += 1
            else:
                # False negative: error was missed
                missed_errors_count += 1
                false_negatives_list.append(
                    FalseNegative(
                        row=gt_entry.row,
                        field=gt_entry.schema_field,
                        expected_correction=gt_entry.original,
                        actual_error=gt_entry.error,
                        error_type=gt_entry.error_type,
                    )
                )

        # Find false positives (detected but not in ground truth)
        for error in validation_results.validation_results:
            row = error.row - 1  # Convert to 0-based
            field = error.column
            key = (row, field)

            if key not in self.error_lookup:
                false_alarms_count += 1
                false_positives_list.append(
                    FalsePositive(
                        row=row,
                        field=field,
                        predicted_error=error.recommended_value or "",
                        actual_value=error.current_value,
                        confidence=error.confidence_score,
                    )
                )

        # Identify most common error types
        most_common_error_types = error_type_counter.most_common()

        # Identify most problematic fields (fields with most missed errors)
        field_missed_counter = Counter()
        for fn in false_negatives_list:
            field_missed_counter[fn.field] += 1
        most_problematic_fields = field_missed_counter.most_common()

        logger.info(
            f"Error analysis complete: "
            f"Detected={detected_errors_count}/{total_errors}, "
            f"Missed={missed_errors_count}, FalseAlarms={false_alarms_count}"
        )

        return ErrorAnalysis(
            total_errors=total_errors,
            detected_errors=detected_errors_count,
            missed_errors=missed_errors_count,
            false_alarms=false_alarms_count,
            most_common_error_types=most_common_error_types,
            most_problematic_fields=most_problematic_fields,
            false_positives=false_positives_list,
            false_negatives=false_negatives_list,
        )

    def calculate_cost_metrics(
        self,
        state: ProcessorState,
        pricing_config: BedrockPricingConfig,
        detected_errors_count: int,
    ) -> CostMetrics:
        """
        Calculate cost metrics from token usage in processor state.

        This method extracts token usage data from the processor state,
        uses the CostCalculator to compute costs based on pricing configuration,
        and calculates aggregate cost metrics including cost per error detected.
        Model IDs are extracted from the actual token usage data.

        Args:
            state: Processor state containing token usage data
            pricing_config: Bedrock pricing configuration
            detected_errors_count: Number of errors detected (for cost per error calculation)

        Returns:
            CostMetrics containing all cost information

        Raises:
            MetricsCalculationError: If cost calculation fails
        """
        if state is None:
            raise MetricsCalculationError("state cannot be None")

        logger.info("Calculating cost metrics from token usage...")

        # Initialize cost calculator
        calculator = CostCalculator(pricing_config)

        # Extract model IDs from actual token usage
        llm_models = set()
        embedding_models = set()

        for node_usage in state.token_usage.values():
            if node_usage.llm_model_id:
                llm_models.add(node_usage.llm_model_id)
            if node_usage.embedding_model_id:
                embedding_models.add(node_usage.embedding_model_id)

        # Use primary model (first found) or "unknown" if none
        llm_model_id = next(iter(llm_models), "unknown")
        embedding_model_id = next(iter(embedding_models), "unknown")

        logger.info(f"Extracted model IDs from usage: LLM={llm_model_id}, Embedding={embedding_model_id}")

        # Initialize aggregate counters
        total_llm_input_tokens = 0
        total_llm_output_tokens = 0
        total_llm_calls = 0
        total_embedding_tokens = 0
        total_embedding_calls = 0

        # Aggregate token usage across all nodes
        for node_name, node_usage in state.token_usage.items():
            total_llm_input_tokens += node_usage.llm_input_tokens
            total_llm_output_tokens += node_usage.llm_output_tokens
            total_llm_calls += node_usage.llm_calls
            total_embedding_tokens += node_usage.embedding_tokens
            total_embedding_calls += node_usage.embedding_calls

            logger.debug(
                f"Node '{node_name}': "
                f"LLM tokens={node_usage.llm_input_tokens + node_usage.llm_output_tokens}, "
                f"Embedding tokens={node_usage.embedding_tokens}"
            )

        # Calculate total LLM tokens
        total_llm_tokens = total_llm_input_tokens + total_llm_output_tokens

        # Calculate LLM costs
        llm_input_cost, llm_output_cost, llm_total_cost = calculator.calculate_llm_cost(
            llm_model_id, total_llm_input_tokens, total_llm_output_tokens
        )

        # Calculate embedding costs
        embedding_cost = calculator.calculate_embedding_cost(embedding_model_id, total_embedding_tokens)

        # Calculate total cost
        total_cost = llm_total_cost + embedding_cost

        # Calculate cost per error detected
        cost_per_error_detected = None
        if detected_errors_count > 0:
            cost_per_error_detected = total_cost / detected_errors_count

        cost_per_error_str = f"{cost_per_error_detected:.4f}" if cost_per_error_detected is not None else "N/A"
        logger.info(
            f"Cost metrics calculated: "
            f"Total=${total_cost:.4f}, "
            f"LLM=${llm_total_cost:.4f}, "
            f"Embedding=${embedding_cost:.4f}, "
            f"Cost/Error=${cost_per_error_str}"
        )

        return CostMetrics(
            llm_input_tokens=total_llm_input_tokens,
            llm_output_tokens=total_llm_output_tokens,
            llm_total_tokens=total_llm_tokens,
            llm_input_cost=llm_input_cost,
            llm_output_cost=llm_output_cost,
            llm_total_cost=llm_total_cost,
            llm_api_calls=total_llm_calls,
            embedding_tokens=total_embedding_tokens,
            embedding_cost=embedding_cost,
            embedding_api_calls=total_embedding_calls,
            total_cost=total_cost,
            cost_per_error_detected=cost_per_error_detected,
            llm_model_id=llm_model_id,
            embedding_model_id=embedding_model_id,
        )

    def calculate_node_cost_metrics(
        self,
        state: ProcessorState,
        pricing_config: BedrockPricingConfig,
        node_metrics: Dict[str, NodeMetrics],
    ) -> Dict[str, NodeMetrics]:
        """
        Calculate and populate cost metrics for each correction node.

        This method updates the provided node_metrics dictionary with cost
        information extracted from the processor state's token usage data.
        Model IDs are extracted from each node's own token usage.

        Args:
            state: Processor state containing token usage data
            pricing_config: Bedrock pricing configuration
            node_metrics: Dictionary of NodeMetrics to update with cost data

        Returns:
            Updated dictionary of NodeMetrics with cost information

        Raises:
            MetricsCalculationError: If cost calculation fails
        """
        if state is None:
            raise MetricsCalculationError("state cannot be None")

        logger.info("Calculating per-node cost metrics...")

        # Initialize cost calculator
        calculator = CostCalculator(pricing_config)

        # Calculate costs for each node that has token usage
        for node_name, node_usage in state.token_usage.items():
            # Calculate LLM costs only if node used LLM
            llm_input_cost = 0.0
            llm_output_cost = 0.0
            llm_total_cost = 0.0

            if node_usage.llm_model_id and (node_usage.llm_input_tokens > 0 or node_usage.llm_output_tokens > 0):
                llm_input_cost, llm_output_cost, llm_total_cost = calculator.calculate_llm_cost(
                    node_usage.llm_model_id, node_usage.llm_input_tokens, node_usage.llm_output_tokens
                )

            # Calculate embedding costs only if node used embeddings
            embedding_cost = 0.0
            if node_usage.embedding_model_id and node_usage.embedding_tokens > 0:
                embedding_cost = calculator.calculate_embedding_cost(
                    node_usage.embedding_model_id, node_usage.embedding_tokens
                )

            total_node_cost = llm_total_cost + embedding_cost

            # Create CostMetrics for this node with node-specific model IDs
            node_cost_metrics = CostMetrics(
                llm_input_tokens=node_usage.llm_input_tokens,
                llm_output_tokens=node_usage.llm_output_tokens,
                llm_total_tokens=node_usage.llm_input_tokens + node_usage.llm_output_tokens,
                llm_input_cost=llm_input_cost,
                llm_output_cost=llm_output_cost,
                llm_total_cost=llm_total_cost,
                llm_api_calls=node_usage.llm_calls,
                embedding_tokens=node_usage.embedding_tokens,
                embedding_cost=embedding_cost,
                embedding_api_calls=node_usage.embedding_calls,
                total_cost=total_node_cost,
                llm_model_id=node_usage.llm_model_id,
                embedding_model_id=node_usage.embedding_model_id,
            )

            # Calculate cost per correction if this node exists in node_metrics
            cost_per_correction = None
            if node_name in node_metrics:
                successful_corrections = node_metrics[node_name].successful_corrections
                if successful_corrections > 0:
                    cost_per_correction = total_node_cost / successful_corrections

                # Update the node metrics with cost information
                node_metrics[node_name].cost_metrics = node_cost_metrics
                node_metrics[node_name].cost_per_correction = cost_per_correction

                cost_per_correction_str = f"{cost_per_correction:.4f}" if cost_per_correction is not None else "N/A"
                logger.debug(
                    f"Node '{node_name}': "
                    f"Cost=${total_node_cost:.4f}, "
                    f"Cost/Correction=${cost_per_correction_str}"
                )
            else:
                # Node has token usage but no correction metrics
                # This can happen if the node made API calls but didn't produce corrections
                logger.debug(f"Node '{node_name}' has token usage but no correction metrics")

        logger.info(f"Calculated cost metrics for {len(state.token_usage)} nodes")

        return node_metrics
