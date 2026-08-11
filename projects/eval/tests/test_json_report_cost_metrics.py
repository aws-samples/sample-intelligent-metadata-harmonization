# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Tests for JSON report generation with cost metrics.

This module tests that cost metrics are properly included in JSON
serialization of EvaluationResult and NodeMetrics.
"""

import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


from metadata_harmonization_eval.models import (
    AccuracyMetrics,
    CostMetrics,
    ConfidenceMetrics,
    ErrorAnalysis,
    EvaluationResult,
    NodeMetrics,
    PerformanceMetrics,
)
from metadata_harmonization_eval.report_generator import ReportGenerator


class TestJSONReportCostMetrics:
    """Tests for cost metrics in JSON reports."""

    def test_evaluation_result_json_serialization_with_cost_metrics(self):
        """Test that EvaluationResult with cost_metrics serializes to JSON correctly."""
        # Create cost metrics
        cost_metrics = CostMetrics(
            llm_input_tokens=50000,
            llm_output_tokens=15000,
            llm_total_tokens=65000,
            llm_input_cost=0.04,
            llm_output_cost=0.06,
            llm_total_cost=0.10,
            llm_api_calls=25,
            embedding_tokens=1170000,
            embedding_cost=0.0234,
            embedding_api_calls=150,
            total_cost=0.1234,
            cost_per_error_detected=0.0012,
            llm_model_id="amazon.nova-pro-v1:0",
            embedding_model_id="amazon.titan-embed-text-v2:0",
        )

        # Create evaluation result with cost metrics
        result = EvaluationResult(
            dataset_name="test_dataset",
            timestamp=datetime(2025, 11, 21, 12, 0, 0),
            session_id="test-session",
            program_id="test-program",
            core_id="test-core",
            error_rate=0.4,
            accuracy_metrics=AccuracyMetrics(
                precision=0.9,
                recall=0.85,
                f1_score=0.87,
                true_positives=85,
                false_positives=10,
                false_negatives=15,
                true_negatives=890,
                accuracy=0.975,
            ),
            performance_metrics=PerformanceMetrics(
                total_duration_seconds=120.5,
                per_record_duration_ms=120.5,
                records_per_second=8.3,
                schema_alignment_duration=10.0,
                validation_duration=50.0,
                prediction_duration=60.5,
                peak_memory_mb=512.0,
            ),
            confidence_metrics=ConfidenceMetrics(
                mean_confidence=0.75,
                median_confidence=0.80,
                std_deviation=0.15,
                min_confidence=0.2,
                max_confidence=0.99,
                high_confidence_accuracy=0.95,
                low_confidence_accuracy=0.65,
            ),
            error_analysis=ErrorAnalysis(total_errors=100, detected_errors=85, missed_errors=15, false_alarms=10),
            total_records=1000,
            total_ground_truth_errors=100,
            cost_metrics=cost_metrics,
        )

        # Serialize to JSON
        json_data = result.model_dump(mode="json")

        # Verify cost_metrics is present in JSON
        assert "cost_metrics" in json_data
        assert json_data["cost_metrics"] is not None

        # Verify all cost metric fields are present
        cost_data = json_data["cost_metrics"]
        assert cost_data["llm_input_tokens"] == 50000
        assert cost_data["llm_output_tokens"] == 15000
        assert cost_data["llm_total_tokens"] == 65000
        assert cost_data["llm_input_cost"] == 0.04
        assert cost_data["llm_output_cost"] == 0.06
        assert cost_data["llm_total_cost"] == 0.10
        assert cost_data["llm_api_calls"] == 25
        assert cost_data["embedding_tokens"] == 1170000
        assert cost_data["embedding_cost"] == 0.0234
        assert cost_data["embedding_api_calls"] == 150
        assert cost_data["total_cost"] == 0.1234
        assert cost_data["cost_per_error_detected"] == 0.0012
        assert cost_data["llm_model_id"] == "amazon.nova-pro-v1:0"
        assert cost_data["embedding_model_id"] == "amazon.titan-embed-text-v2:0"

    def test_evaluation_result_json_serialization_without_cost_metrics(self):
        """Test that EvaluationResult without cost_metrics serializes correctly (backward compatibility)."""
        result = EvaluationResult(
            dataset_name="test_dataset",
            timestamp=datetime(2025, 11, 21, 12, 0, 0),
            session_id="test-session",
            program_id="test-program",
            core_id="test-core",
            error_rate=0.4,
            accuracy_metrics=AccuracyMetrics(
                precision=0.9,
                recall=0.85,
                f1_score=0.87,
                true_positives=85,
                false_positives=10,
                false_negatives=15,
                true_negatives=890,
                accuracy=0.975,
            ),
            performance_metrics=PerformanceMetrics(
                total_duration_seconds=120.5,
                per_record_duration_ms=120.5,
                records_per_second=8.3,
                schema_alignment_duration=10.0,
                validation_duration=50.0,
                prediction_duration=60.5,
                peak_memory_mb=512.0,
            ),
            confidence_metrics=ConfidenceMetrics(
                mean_confidence=0.75,
                median_confidence=0.80,
                std_deviation=0.15,
                min_confidence=0.2,
                max_confidence=0.99,
                high_confidence_accuracy=0.95,
                low_confidence_accuracy=0.65,
            ),
            error_analysis=ErrorAnalysis(total_errors=100, detected_errors=85, missed_errors=15, false_alarms=10),
            total_records=1000,
            total_ground_truth_errors=100,
        )

        # Serialize to JSON
        json_data = result.model_dump(mode="json")

        # Verify cost_metrics is present but None
        assert "cost_metrics" in json_data
        assert json_data["cost_metrics"] is None

    def test_node_metrics_json_serialization_with_cost_metrics(self):
        """Test that NodeMetrics with cost_metrics serializes to JSON correctly."""
        # Create cost metrics for a node
        cost_metrics = CostMetrics(
            llm_input_tokens=25000,
            llm_output_tokens=7500,
            llm_total_tokens=32500,
            llm_input_cost=0.02,
            llm_output_cost=0.03,
            llm_total_cost=0.05,
            llm_api_calls=10,
            total_cost=0.05,
            llm_model_id="amazon.nova-pro-v1:0",
        )

        # Create node metrics with cost
        node_metrics = NodeMetrics(
            node_name="llm_resolution",
            total_corrections=100,
            successful_corrections=85,
            success_rate=0.85,
            cost_metrics=cost_metrics,
            cost_per_correction=0.0006,
        )

        # Serialize to JSON
        json_data = node_metrics.model_dump(mode="json")

        # Verify cost_metrics is present
        assert "cost_metrics" in json_data
        assert json_data["cost_metrics"] is not None

        # Verify cost metric fields
        cost_data = json_data["cost_metrics"]
        assert cost_data["llm_input_tokens"] == 25000
        assert cost_data["llm_output_tokens"] == 7500
        assert cost_data["llm_total_cost"] == 0.05
        assert cost_data["total_cost"] == 0.05

        # Verify cost_per_correction
        assert json_data["cost_per_correction"] == 0.0006

    def test_generate_json_report_includes_cost_metrics(self):
        """Test that generate_json_report includes cost metrics in the output file."""
        # Create cost metrics
        cost_metrics = CostMetrics(
            llm_input_tokens=50000,
            llm_output_tokens=15000,
            llm_total_tokens=65000,
            llm_input_cost=0.04,
            llm_output_cost=0.06,
            llm_total_cost=0.10,
            llm_api_calls=25,
            embedding_tokens=1170000,
            embedding_cost=0.0234,
            embedding_api_calls=150,
            total_cost=0.1234,
            cost_per_error_detected=0.0012,
            llm_model_id="amazon.nova-pro-v1:0",
            embedding_model_id="amazon.titan-embed-text-v2:0",
        )

        # Create node metrics with cost
        node_cost_metrics = CostMetrics(
            llm_input_tokens=25000,
            llm_output_tokens=7500,
            llm_total_cost=0.05,
            total_cost=0.05,
            llm_model_id="amazon.nova-pro-v1:0",
        )

        node_metrics = NodeMetrics(
            node_name="llm_resolution",
            total_corrections=100,
            successful_corrections=85,
            success_rate=0.85,
            cost_metrics=node_cost_metrics,
            cost_per_correction=0.0006,
        )

        # Create evaluation result with cost metrics
        result = EvaluationResult(
            dataset_name="test_dataset",
            timestamp=datetime(2025, 11, 21, 12, 0, 0),
            session_id="test-session",
            program_id="test-program",
            core_id="test-core",
            error_rate=0.4,
            accuracy_metrics=AccuracyMetrics(
                precision=0.9,
                recall=0.85,
                f1_score=0.87,
                true_positives=85,
                false_positives=10,
                false_negatives=15,
                true_negatives=890,
                accuracy=0.975,
            ),
            performance_metrics=PerformanceMetrics(
                total_duration_seconds=120.5,
                per_record_duration_ms=120.5,
                records_per_second=8.3,
                schema_alignment_duration=10.0,
                validation_duration=50.0,
                prediction_duration=60.5,
                peak_memory_mb=512.0,
            ),
            confidence_metrics=ConfidenceMetrics(
                mean_confidence=0.75,
                median_confidence=0.80,
                std_deviation=0.15,
                min_confidence=0.2,
                max_confidence=0.99,
                high_confidence_accuracy=0.95,
                low_confidence_accuracy=0.65,
            ),
            error_analysis=ErrorAnalysis(total_errors=100, detected_errors=85, missed_errors=15, false_alarms=10),
            total_records=1000,
            total_ground_truth_errors=100,
            cost_metrics=cost_metrics,
            node_metrics={"llm_resolution": node_metrics},
        )

        # Generate JSON report
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            report_gen = ReportGenerator(output_dir)
            output_path = output_dir / "test_report.json"

            report_gen.generate_json_report(result, output_path)

            # Read and parse the generated JSON file
            with open(output_path, "r") as f:
                report_data = json.load(f)

            # Verify cost_metrics is in the report
            assert "cost_metrics" in report_data
            assert report_data["cost_metrics"] is not None

            # Verify cost metric values
            cost_data = report_data["cost_metrics"]
            assert cost_data["total_cost"] == 0.1234
            assert cost_data["cost_per_error_detected"] == 0.0012
            assert cost_data["llm_model_id"] == "amazon.nova-pro-v1:0"
            assert cost_data["embedding_model_id"] == "amazon.titan-embed-text-v2:0"

            # Verify node_metrics includes cost_metrics
            assert "node_metrics" in report_data
            assert "llm_resolution" in report_data["node_metrics"]
            node_data = report_data["node_metrics"]["llm_resolution"]
            assert "cost_metrics" in node_data
            assert node_data["cost_metrics"] is not None
            assert node_data["cost_metrics"]["total_cost"] == 0.05
            assert node_data["cost_per_correction"] == 0.0006
