# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Report generation module for evaluation results.

This module provides functionality to generate evaluation reports in multiple formats
including JSON, Markdown, and batch comparison reports with text-based visualizations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


from .models import BatchEvaluationResult, EvaluationResult


class ReportGenerationError(Exception):
    """Exception raised when report generation fails."""

    pass


class ReportGenerator:
    """
    Generates evaluation reports in multiple formats.

    Supports JSON for programmatic access, Markdown for human readability,
    and batch comparison reports for analyzing multiple datasets.
    """

    def __init__(self, output_dir: Path):
        """
        Initialize the report generator.

        Args:
            output_dir: Directory where reports will be saved
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # Subtask 5.1: JSON Report Generation
    # ========================================================================

    def generate_json_report(self, evaluation_result: EvaluationResult, output_path: Path) -> None:
        """
        Generate a detailed JSON report from evaluation results.

        The JSON report includes all metrics with proper formatting and handles
        datetime serialization correctly. This format is suitable for programmatic
        access and further analysis.

        Args:
            evaluation_result: The evaluation result to serialize
            output_path: Path where the JSON report will be saved

        Raises:
            ReportGenerationError: If report generation or file writing fails
        """
        try:
            # Convert the Pydantic model to a dictionary
            report_data = evaluation_result.model_dump(mode="json")

            # Ensure datetime is properly formatted as ISO string
            if isinstance(report_data.get("timestamp"), datetime):
                report_data["timestamp"] = report_data["timestamp"].isoformat()

            # Write JSON with pretty formatting
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise ReportGenerationError(f"Failed to generate JSON report at {output_path}: {e}") from e

    # ========================================================================
    # Subtask 5.4: Text-based Visualizations
    # ========================================================================

    def _create_ascii_histogram(
        self, distribution: Dict[str, int], max_width: int = 50, title: str = "Distribution"
    ) -> str:
        """
        Create an ASCII histogram for confidence distributions.

        Args:
            distribution: Dictionary mapping bucket labels to counts
            max_width: Maximum width of the histogram bars
            title: Title for the histogram

        Returns:
            ASCII art histogram as a string
        """
        if not distribution:
            return f"{title}:\n  No data available\n"

        # Find the maximum count for scaling
        max_count = max(distribution.values()) if distribution else 1

        lines = [f"{title}:"]

        # Sort buckets by their range (e.g., "0.0-0.2" comes before "0.2-0.4")
        sorted_buckets = sorted(distribution.items())

        for bucket, count in sorted_buckets:
            # Calculate bar width proportional to count
            if max_count > 0:
                bar_width = int((count / max_count) * max_width)
            else:
                bar_width = 0

            bar = "█" * bar_width
            lines.append(f"  {bucket:10s} | {bar} {count}")

        return "\n".join(lines)

    def _create_bar_chart(self, data: List[tuple], max_width: int = 40, title: str = "Chart") -> str:
        """
        Create a bar chart for error type frequencies.

        Args:
            data: List of (label, value) tuples
            max_width: Maximum width of the bars
            title: Title for the chart

        Returns:
            ASCII art bar chart as a string
        """
        if not data:
            return f"{title}:\n  No data available\n"

        # Find the maximum value for scaling
        max_value = max(value for _, value in data) if data else 1

        lines = [f"{title}:"]

        for label, value in data:
            # Calculate bar width proportional to value
            if max_value > 0:
                bar_width = int((value / max_value) * max_width)
            else:
                bar_width = 0

            bar = "█" * bar_width
            lines.append(f"  {label:20s} | {bar} {value}")

        return "\n".join(lines)

    def _create_metrics_table(self, headers: List[str], rows: List[List[Any]]) -> str:
        """
        Create a formatted table for metric comparisons.

        Args:
            headers: List of column headers
            rows: List of rows, where each row is a list of values

        Returns:
            Formatted markdown table as a string
        """
        if not headers or not rows:
            return "No data available"

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Create header row
        header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"

        # Create separator row
        separator = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"

        # Create data rows
        data_lines = []
        for row in rows:
            line = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
            data_lines.append(line)

        return "\n".join([header_line, separator] + data_lines)

    # ========================================================================
    # Subtask 5.2: Markdown Report Generation
    # ========================================================================

    def generate_markdown_report(self, evaluation_result: EvaluationResult, output_path: Path) -> None:
        """
        Generate a human-readable markdown summary report.

        The markdown report includes:
        - Summary section with key metrics
        - Tables for per-field and per-error-type breakdowns
        - Text-based visualizations (ASCII histograms for confidence distribution)
        - Configuration and metadata sections

        Args:
            evaluation_result: The evaluation result to format
            output_path: Path where the markdown report will be saved

        Raises:
            ReportGenerationError: If report generation or file writing fails
        """
        try:
            lines = []

            # Title and metadata
            lines.append(f"# Evaluation Report: {evaluation_result.dataset_name}")
            lines.append("")
            lines.append(f"**Generated:** {evaluation_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"**Session ID:** {evaluation_result.session_id}")
            lines.append(f"**Processor Version:** {evaluation_result.processor_version}")
            lines.append("")

            # Configuration section
            lines.append("## Configuration")
            lines.append("")
            lines.append(f"- **Program ID:** {evaluation_result.program_id}")
            lines.append(f"- **Core ID:** {evaluation_result.core_id}")
            lines.append(f"- **Dataset Error Rate:** {evaluation_result.error_rate:.1%}")
            lines.append(f"- **Total Records:** {evaluation_result.total_records}")
            lines.append(f"- **Total Ground Truth Errors:** {evaluation_result.total_ground_truth_errors}")
            lines.append("")

            # Summary section with key metrics
            lines.append("## Summary")
            lines.append("")
            acc = evaluation_result.accuracy_metrics
            lines.append(f"- **Precision:** {acc.precision:.3f}")
            lines.append(f"- **Recall:** {acc.recall:.3f}")
            lines.append(f"- **F1 Score:** {acc.f1_score:.3f}")
            lines.append(f"- **Accuracy:** {acc.accuracy:.3f}")
            lines.append("")

            # Accuracy metrics detail
            lines.append("## Accuracy Metrics")
            lines.append("")
            lines.append(f"- **True Positives:** {acc.true_positives}")
            lines.append(f"- **False Positives:** {acc.false_positives}")
            lines.append(f"- **False Negatives:** {acc.false_negatives}")
            lines.append(f"- **True Negatives:** {acc.true_negatives}")
            lines.append("")

            # Per-field metrics table
            if acc.field_metrics:
                lines.append("### Per-Field Metrics")
                lines.append("")

                headers = ["Field", "Precision", "Recall", "F1 Score", "Accuracy", "Detected", "Missed"]
                rows = []
                fields_with_errors = []  # Track for weighted average

                for field_name, metrics in acc.field_metrics.items():
                    # Mark fields with no ground truth errors as N/A
                    if metrics.total_errors == 0:
                        rows.append([field_name, "N/A", "N/A", "N/A", "N/A", f"{metrics.detected_errors}", "0"])
                    else:
                        rows.append(
                            [
                                field_name,
                                f"{metrics.precision:.3f}",
                                f"{metrics.recall:.3f}",
                                f"{metrics.f1_score:.3f}",
                                f"{metrics.accuracy:.3f}",
                                f"{metrics.detected_errors}",
                                f"{metrics.missed_errors}",
                            ]
                        )
                        fields_with_errors.append(metrics)

                lines.append(self._create_metrics_table(headers, rows))
                lines.append("")

                # Add weighted field-level summary
                if fields_with_errors:
                    total_errors = sum(m.total_errors for m in fields_with_errors)
                    weighted_accuracy = sum(m.accuracy * m.total_errors for m in fields_with_errors) / total_errors
                    weighted_precision = sum(m.precision * m.total_errors for m in fields_with_errors) / total_errors
                    weighted_recall = sum(m.recall * m.total_errors for m in fields_with_errors) / total_errors
                    weighted_f1 = sum(m.f1_score * m.total_errors for m in fields_with_errors) / total_errors

                    lines.append("**Weighted Field-Level Averages** (weighted by error count):")
                    lines.append("")
                    lines.append(f"- Precision: {weighted_precision:.3f}")
                    lines.append(f"- Recall: {weighted_recall:.3f}")
                    lines.append(f"- F1 Score: {weighted_f1:.3f}")
                    lines.append(f"- Accuracy: {weighted_accuracy:.3f}")
                    lines.append("")

            # Per-error-type metrics table
            if acc.error_type_metrics:
                lines.append("### Per-Error-Type Metrics")
                lines.append("")

                headers = ["Error Type", "Detection Rate", "Total", "Detected"]
                rows = []
                for error_type, metrics in acc.error_type_metrics.items():
                    rows.append(
                        [
                            error_type,
                            f"{metrics.detection_rate:.1%}",
                            f"{metrics.total_count}",
                            f"{metrics.detected_count}",
                        ]
                    )

                lines.append(self._create_metrics_table(headers, rows))
                lines.append("")

            # Performance metrics
            lines.append("## Performance Metrics")
            lines.append("")
            perf = evaluation_result.performance_metrics
            lines.append(f"- **Total Duration:** {perf.total_duration_seconds:.2f}s")
            lines.append(f"- **Per-Record Duration:** {perf.per_record_duration_ms:.2f}ms")
            lines.append(f"- **Records Per Second:** {perf.records_per_second:.2f}")
            lines.append(f"- **Peak Memory:** {perf.peak_memory_mb:.2f} MB")
            lines.append("")
            lines.append("### Stage Timings")
            lines.append("")
            lines.append(f"- **Schema Alignment:** {perf.schema_alignment_duration:.2f}s")
            lines.append(f"- **Validation:** {perf.validation_duration:.2f}s")
            lines.append(f"- **Prediction:** {perf.prediction_duration:.2f}s")
            lines.append("")

            # Cost metrics section
            if evaluation_result.cost_metrics:
                lines.append("## Cost Metrics")
                lines.append("")
                cost = evaluation_result.cost_metrics

                # LLM Usage by Model (new section)
                if evaluation_result.node_metrics:
                    # Group token usage by model_id (use llm_model_id or embedding_model_id)
                    model_usage = {}  # model_id -> {nodes: [], llm_calls: 0, input_tokens: 0, ...}

                    for node_name, node_metrics in evaluation_result.node_metrics.items():
                        if node_metrics.cost_metrics:
                            # Use llm_model_id for LLM nodes, embedding_model_id for embedding nodes
                            model_id = (
                                node_metrics.cost_metrics.llm_model_id or node_metrics.cost_metrics.embedding_model_id
                            )
                            if model_id:
                                if model_id not in model_usage:
                                    model_usage[model_id] = {
                                        "nodes": [],
                                        "llm_calls": 0,
                                        "llm_input_tokens": 0,
                                        "llm_output_tokens": 0,
                                        "llm_input_cost": 0.0,
                                        "llm_output_cost": 0.0,
                                        "llm_total_cost": 0.0,
                                        "embedding_calls": 0,
                                        "embedding_tokens": 0,
                                        "embedding_cost": 0.0,
                                        "is_embedding_model": False,
                                    }

                                model_usage[model_id]["nodes"].append(node_name)

                                # Accumulate metrics with None-safety
                                if node_metrics.cost_metrics.llm_api_calls > 0:
                                    model_usage[model_id]["llm_calls"] += node_metrics.cost_metrics.llm_api_calls
                                    model_usage[model_id]["llm_input_tokens"] += (
                                        node_metrics.cost_metrics.llm_input_tokens or 0
                                    )
                                    model_usage[model_id]["llm_output_tokens"] += (
                                        node_metrics.cost_metrics.llm_output_tokens or 0
                                    )
                                    model_usage[model_id]["llm_input_cost"] += (
                                        node_metrics.cost_metrics.llm_input_cost or 0.0
                                    )
                                    model_usage[model_id]["llm_output_cost"] += (
                                        node_metrics.cost_metrics.llm_output_cost or 0.0
                                    )
                                    model_usage[model_id]["llm_total_cost"] += (
                                        node_metrics.cost_metrics.llm_total_cost or 0.0
                                    )

                                if node_metrics.cost_metrics.embedding_api_calls > 0:
                                    model_usage[model_id]["is_embedding_model"] = True
                                    model_usage[model_id][
                                        "embedding_calls"
                                    ] += node_metrics.cost_metrics.embedding_api_calls
                                    model_usage[model_id]["embedding_tokens"] += (
                                        node_metrics.cost_metrics.embedding_tokens or 0
                                    )
                                    model_usage[model_id]["embedding_cost"] += (
                                        node_metrics.cost_metrics.embedding_cost or 0.0
                                    )

                    if model_usage:
                        lines.append("### LLM Usage by Model")
                        lines.append("")

                        # Sort by total cost (highest first)
                        sorted_models = sorted(
                            model_usage.items(),
                            key=lambda x: x[1]["llm_total_cost"] + x[1]["embedding_cost"],
                            reverse=True,
                        )

                        for model_id, usage in sorted_models:
                            lines.append(f"#### Model: `{model_id}`")
                            lines.append(f"**Used by:** {', '.join(usage['nodes'])}")
                            lines.append("")

                            if usage["is_embedding_model"]:
                                # Embedding model table
                                headers = ["Metric", "Value"]
                                rows = [
                                    ["API Calls", f"{usage['embedding_calls']:,}"],
                                    ["Embedding Tokens", f"{usage['embedding_tokens']:,}"],
                                    ["**Total Cost**", f"**${usage['embedding_cost']:.8f}**"],
                                ]
                            else:
                                # LLM model table
                                headers = ["Metric", "Value"]
                                rows = [
                                    ["API Calls", f"{usage['llm_calls']:,}"],
                                    ["Input Tokens", f"{usage['llm_input_tokens']:,}"],
                                    ["Output Tokens", f"{usage['llm_output_tokens']:,}"],
                                    ["Input Cost", f"${usage['llm_input_cost']:.8f}"],
                                    ["Output Cost", f"${usage['llm_output_cost']:.8f}"],
                                    ["**Total Cost**", f"**${usage['llm_total_cost']:.8f}**"],
                                ]

                            lines.append(self._create_metrics_table(headers, rows))
                            lines.append("")

                        lines.append(f"### Total LLM Costs: ${cost.total_cost:.8f}")
                        lines.append("")

                # Overall costs summary (kept for backward compatibility)
                lines.append("### Overall Cost Summary")
                lines.append("")
                lines.append(f"- **Total Cost:** ${cost.total_cost:.8f}")

                # LLM cost breakdown
                llm_percentage = (cost.llm_total_cost / cost.total_cost * 100) if cost.total_cost > 0 else 0
                lines.append(f"- **LLM Cost:** ${cost.llm_total_cost:.8f} ({llm_percentage:.1f}%)")
                lines.append(f"  - Input tokens: {cost.llm_input_tokens:,} (${cost.llm_input_cost:.8f})")
                lines.append(f"  - Output tokens: {cost.llm_output_tokens:,} (${cost.llm_output_cost:.8f})")
                lines.append(f"  - API calls: {cost.llm_api_calls}")

                # Embedding cost breakdown
                embedding_percentage = (cost.embedding_cost / cost.total_cost * 100) if cost.total_cost > 0 else 0
                lines.append(f"- **Embedding Cost:** ${cost.embedding_cost:.8f} ({embedding_percentage:.1f}%)")
                lines.append(f"  - Tokens: {cost.embedding_tokens:,}")
                lines.append(f"  - API calls: {cost.embedding_api_calls}")

                # Cost per error detected
                if cost.cost_per_error_detected is not None:
                    lines.append(f"- **Cost per Error Detected:** ${cost.cost_per_error_detected:.8f}")
                else:
                    lines.append("- **Cost per Error Detected:** N/A (no errors detected)")
                lines.append("")

            # Confidence metrics with visualization
            lines.append("## Confidence Metrics")
            lines.append("")
            conf = evaluation_result.confidence_metrics
            lines.append(f"- **Mean Confidence:** {conf.mean_confidence:.3f}")
            lines.append(f"- **Median Confidence:** {conf.median_confidence:.3f}")
            lines.append(f"- **Std Deviation:** {conf.std_deviation:.3f}")
            lines.append(f"- **Min Confidence:** {conf.min_confidence:.3f}")
            lines.append(f"- **Max Confidence:** {conf.max_confidence:.3f}")
            lines.append("")
            lines.append(f"- **High Confidence Accuracy (>0.8):** {conf.high_confidence_accuracy:.3f}")
            lines.append(f"- **Low Confidence Accuracy (<0.5):** {conf.low_confidence_accuracy:.3f}")
            lines.append("")

            # Confidence distribution histogram
            if conf.confidence_distribution:
                lines.append("### Confidence Distribution")
                lines.append("")
                lines.append("```")
                lines.append(
                    self._create_ascii_histogram(conf.confidence_distribution, title="Confidence Score Distribution")
                )
                lines.append("```")
                lines.append("")

            # Per-Node Correction Metrics
            if evaluation_result.node_metrics:
                lines.append("## Per-Node Correction Metrics")
                lines.append("")
                lines.append("Performance of individual correction nodes in the enum correction pipeline:")
                lines.append("")

                # Main metrics table with cost columns
                headers = [
                    "Node",
                    "Corrections",
                    "Accuracy",
                    "Avg Confidence",
                    "Median Conf",
                    "High Conf (>0.8)",
                    "LLM Cost",
                    "Embedding Cost",
                    "Total Cost",
                    "Cost/Correction",
                ]
                rows = []

                # Sort nodes by total corrections (most active first)
                sorted_nodes = sorted(
                    evaluation_result.node_metrics.items(), key=lambda x: x[1].total_corrections, reverse=True
                )

                for node_name, metrics in sorted_nodes:
                    # Build base row
                    row = [
                        node_name,
                        str(metrics.total_corrections),
                        f"{metrics.success_rate:.1%}",
                        f"{metrics.mean_confidence:.3f}",
                        f"{metrics.median_confidence:.3f}",
                        f"{metrics.high_confidence_percentage:.1%}",
                    ]

                    # Add cost columns if cost metrics are available
                    if metrics.cost_metrics:
                        row.extend(
                            [
                                f"${metrics.cost_metrics.llm_total_cost:.8f}"
                                if metrics.cost_metrics.llm_total_cost is not None
                                else "-",
                                f"${metrics.cost_metrics.embedding_cost:.8f}"
                                if metrics.cost_metrics.embedding_cost is not None
                                else "-",
                                f"${metrics.cost_metrics.total_cost:.8f}"
                                if metrics.cost_metrics.total_cost is not None
                                else "-",
                                f"${metrics.cost_per_correction:.8f}"
                                if metrics.cost_per_correction is not None
                                else "N/A",
                            ]
                        )
                    else:
                        row.extend(["-", "-", "-", "-"])

                    rows.append(row)

                lines.append(self._create_metrics_table(headers, rows))
                lines.append("")

                # Add cost breakdown by node if cost data is available
                has_cost_data = any(m.cost_metrics for m in evaluation_result.node_metrics.values())
                if has_cost_data:
                    lines.append("### Cost by Correction Node")
                    lines.append("")

                    cost_headers = ["Node", "LLM Cost", "Embedding Cost", "Total Cost", "Cost/Correction"]
                    cost_rows = []

                    for node_name, metrics in sorted_nodes:
                        if metrics.cost_metrics:
                            cost_rows.append(
                                [
                                    node_name,
                                    f"${metrics.cost_metrics.llm_total_cost:.8f}"
                                    if metrics.cost_metrics.llm_total_cost is not None
                                    else "-",
                                    f"${metrics.cost_metrics.embedding_cost:.8f}"
                                    if metrics.cost_metrics.embedding_cost is not None
                                    else "-",
                                    f"${metrics.cost_metrics.total_cost:.8f}"
                                    if metrics.cost_metrics.total_cost is not None
                                    else "-",
                                    f"${metrics.cost_per_correction:.8f}"
                                    if metrics.cost_per_correction is not None
                                    else "N/A",
                                ]
                            )

                    if cost_rows:
                        lines.append(self._create_metrics_table(cost_headers, cost_rows))
                        lines.append("")

                # Error type breakdown per node
                lines.append("### Node Contribution by Error Type")
                lines.append("")

                # Collect all unique error types across all nodes
                all_error_types = set()
                for metrics in evaluation_result.node_metrics.values():
                    all_error_types.update(metrics.error_type_breakdown.keys())

                if all_error_types:
                    # Create a table showing which nodes handled which error types
                    error_headers = ["Error Type"] + [name for name, _ in sorted_nodes]
                    error_rows = []

                    for error_type in sorted(all_error_types):
                        row = [error_type]
                        for node_name, _ in sorted_nodes:
                            count = evaluation_result.node_metrics[node_name].error_type_breakdown.get(error_type, 0)
                            row.append(str(count) if count > 0 else "-")
                        error_rows.append(row)

                    lines.append(self._create_metrics_table(error_headers, error_rows))
                    lines.append("")
                else:
                    lines.append("No error type data available.")
                    lines.append("")

            # Error analysis
            lines.append("## Error Analysis")
            lines.append("")
            err = evaluation_result.error_analysis

            # Calculate proper error rate: errors / (records × fields)
            num_validated_fields = len(acc.field_metrics) if acc.field_metrics else 0
            total_cells = (
                evaluation_result.total_records * num_validated_fields
                if num_validated_fields > 0
                else evaluation_result.total_records
            )
            error_rate_pct = (err.total_errors / total_cells * 100) if total_cells > 0 else 0.0

            lines.append(f"- **Total Errors:** {err.total_errors}")
            lines.append(
                f"- **Error Rate:** {error_rate_pct:.1f}% ({err.total_errors} errors across {num_validated_fields} fields × {evaluation_result.total_records} records)"
            )
            lines.append(f"- **Detected Errors:** {err.detected_errors}")
            lines.append(f"- **Missed Errors:** {err.missed_errors}")
            lines.append(f"- **False Alarms:** {err.false_alarms}")
            lines.append("")

            # Most common error types
            if err.most_common_error_types:
                lines.append("### Most Common Error Types")
                lines.append("")
                lines.append("```")
                lines.append(self._create_bar_chart(err.most_common_error_types, title="Error Type Frequencies"))
                lines.append("```")
                lines.append("")

            # Most problematic fields
            if err.most_problematic_fields:
                lines.append("### Most Problematic Fields")
                lines.append("")
                lines.append("```")
                lines.append(
                    self._create_bar_chart(err.most_problematic_fields, title="Fields with Most Missed Errors")
                )
                lines.append("```")
                lines.append("")

            # False positives summary
            if err.false_positives:
                lines.append(f"### False Positives ({len(err.false_positives)} total)")
                lines.append("")
                lines.append("Top 5 false positives:")
                lines.append("")
                for fp in err.false_positives[:5]:
                    conf_str = f"{fp.confidence:.3f}" if fp.confidence is not None else "N/A"
                    lines.append(
                        f"- Row {fp.row}, Field `{fp.field}`: "
                        f"Predicted error but actual value was correct "
                        f"(confidence: {conf_str})"
                    )
                lines.append("")

            # False negatives summary
            if err.false_negatives:
                lines.append(f"### False Negatives ({len(err.false_negatives)} total)")
                lines.append("")
                lines.append("Top 5 false negatives:")
                lines.append("")
                for fn in err.false_negatives[:5]:
                    lines.append(f"- Row {fn.row}, Field `{fn.field}`: " f"Missed {fn.error_type} error")
                lines.append("")

            # Write the markdown file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        except Exception as e:
            raise ReportGenerationError(f"Failed to generate markdown report at {output_path}: {e}") from e

    # ========================================================================
    # Subtask 5.3: Batch Comparison Report
    # ========================================================================

    def generate_batch_report(self, batch_result: BatchEvaluationResult, output_path: Path) -> None:
        """
        Generate a comparative analysis report across multiple datasets.

        The batch report includes:
        - Aggregate metrics table (average precision, recall, F1)
        - Best and worst performing datasets
        - Correlation between error rate and accuracy
        - Side-by-side comparison tables

        Args:
            batch_result: The batch evaluation result to format
            output_path: Path where the batch report will be saved

        Raises:
            ReportGenerationError: If report generation or file writing fails
        """
        try:
            lines = []

            # Title and metadata
            lines.append("# Batch Evaluation Report")
            lines.append("")
            lines.append(f"**Batch ID:** {batch_result.batch_id}")
            lines.append(f"**Generated:** {batch_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"**Datasets Evaluated:** {len(batch_result.datasets)}")
            lines.append("")

            # Aggregate metrics summary
            lines.append("## Aggregate Metrics")
            lines.append("")
            lines.append(f"- **Average Precision:** {batch_result.average_precision:.3f}")
            lines.append(f"- **Average Recall:** {batch_result.average_recall:.3f}")
            lines.append(f"- **Average F1 Score:** {batch_result.average_f1:.3f}")
            lines.append("")
            lines.append(f"- **Best Performing Dataset:** {batch_result.best_performing_dataset}")
            lines.append(f"- **Worst Performing Dataset:** {batch_result.worst_performing_dataset}")
            lines.append(f"- **Error Rate vs Accuracy Correlation:** {batch_result.error_rate_correlation:.3f}")
            lines.append("")

            # Side-by-side comparison table
            lines.append("## Dataset Comparison")
            lines.append("")

            headers = ["Dataset", "Error Rate", "Precision", "Recall", "F1 Score", "Accuracy", "Duration (s)"]

            rows = []
            for result in batch_result.datasets:
                rows.append(
                    [
                        result.dataset_name,
                        f"{result.error_rate:.1%}",
                        f"{result.accuracy_metrics.precision:.3f}",
                        f"{result.accuracy_metrics.recall:.3f}",
                        f"{result.accuracy_metrics.f1_score:.3f}",
                        f"{result.accuracy_metrics.accuracy:.3f}",
                        f"{result.performance_metrics.total_duration_seconds:.2f}",
                    ]
                )

            lines.append(self._create_metrics_table(headers, rows))
            lines.append("")

            # Performance comparison
            lines.append("## Performance Comparison")
            lines.append("")

            perf_headers = ["Dataset", "Total Time (s)", "Per-Record (ms)", "Records/sec", "Peak Memory (MB)"]

            perf_rows = []
            for result in batch_result.datasets:
                perf = result.performance_metrics
                perf_rows.append(
                    [
                        result.dataset_name,
                        f"{perf.total_duration_seconds:.2f}",
                        f"{perf.per_record_duration_ms:.2f}",
                        f"{perf.records_per_second:.2f}",
                        f"{perf.peak_memory_mb:.2f}",
                    ]
                )

            lines.append(self._create_metrics_table(perf_headers, perf_rows))
            lines.append("")

            # Confidence metrics comparison
            lines.append("## Confidence Metrics Comparison")
            lines.append("")

            conf_headers = ["Dataset", "Mean Conf", "Median Conf", "Std Dev", "High Conf Acc", "Low Conf Acc"]

            conf_rows = []
            for result in batch_result.datasets:
                conf = result.confidence_metrics
                conf_rows.append(
                    [
                        result.dataset_name,
                        f"{conf.mean_confidence:.3f}",
                        f"{conf.median_confidence:.3f}",
                        f"{conf.std_deviation:.3f}",
                        f"{conf.high_confidence_accuracy:.3f}",
                        f"{conf.low_confidence_accuracy:.3f}",
                    ]
                )

            lines.append(self._create_metrics_table(conf_headers, conf_rows))
            lines.append("")

            # Error analysis comparison
            lines.append("## Error Analysis Comparison")
            lines.append("")

            err_headers = ["Dataset", "Total Errors", "Detected", "Missed", "False Alarms", "Detection Rate"]

            err_rows = []
            for result in batch_result.datasets:
                err = result.error_analysis
                detection_rate = err.detected_errors / err.total_errors if err.total_errors > 0 else 0.0
                err_rows.append(
                    [
                        result.dataset_name,
                        f"{err.total_errors}",
                        f"{err.detected_errors}",
                        f"{err.missed_errors}",
                        f"{err.false_alarms}",
                        f"{detection_rate:.1%}",
                    ]
                )

            lines.append(self._create_metrics_table(err_headers, err_rows))
            lines.append("")

            # Insights section
            # Error Rate Correlation Analysis
            lines.append("## Error Rate Correlation")
            lines.append("")

            # Calculate correlation interpretation
            corr = batch_result.error_rate_correlation
            if corr < -0.7:
                corr_interpretation = "strong negative correlation (higher error rates lead to lower accuracy)"
            elif corr < -0.3:
                corr_interpretation = "moderate negative correlation"
            elif corr < 0.3:
                corr_interpretation = "weak or no correlation"
            elif corr < 0.7:
                corr_interpretation = "moderate positive correlation"
            else:
                corr_interpretation = "strong positive correlation"

            lines.append(f"**Correlation Coefficient:** {corr:.3f}")
            lines.append("")
            lines.append(f"**Interpretation:** The correlation of {corr:.3f} indicates a {corr_interpretation}.")
            lines.append("")

            # Show error rates vs accuracies
            lines.append("### Error Rate vs Accuracy Data")
            lines.append("")

            corr_headers = ["Dataset", "Error Rate", "Accuracy"]
            corr_rows = []
            for result in batch_result.datasets:
                corr_rows.append(
                    [result.dataset_name, f"{result.error_rate:.1%}", f"{result.accuracy_metrics.accuracy:.3f}"]
                )

            lines.append(self._create_metrics_table(corr_headers, corr_rows))
            lines.append("")

            lines.append("## Insights")
            lines.append("")

            lines.append(f"- The error rate vs accuracy correlation of {corr:.3f} indicates a {corr_interpretation}.")
            lines.append("")

            # Find datasets with unusual performance
            f1_scores = [r.accuracy_metrics.f1_score for r in batch_result.datasets]
            avg_f1 = sum(f1_scores) / len(f1_scores)

            overperformers = [r for r in batch_result.datasets if r.accuracy_metrics.f1_score > avg_f1 + 0.1]
            underperformers = [r for r in batch_result.datasets if r.accuracy_metrics.f1_score < avg_f1 - 0.1]

            if overperformers:
                lines.append("- **Overperforming datasets** (F1 > average + 0.1):")
                for r in overperformers:
                    lines.append(f"  - {r.dataset_name} (F1: {r.accuracy_metrics.f1_score:.3f})")
                lines.append("")

            if underperformers:
                lines.append("- **Underperforming datasets** (F1 < average - 0.1):")
                for r in underperformers:
                    lines.append(f"  - {r.dataset_name} (F1: {r.accuracy_metrics.f1_score:.3f})")
                lines.append("")

            # Write the markdown file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        except Exception as e:
            raise ReportGenerationError(f"Failed to generate batch report at {output_path}: {e}") from e
