# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Tests for cost metrics models.

This module tests the CostMetrics model and its integration with
NodeMetrics and EvaluationResult models.
"""

from datetime import datetime

import pytest

from metadata_harmonization_eval.models import (
    AccuracyMetrics,
    CostMetrics,
    ConfidenceMetrics,
    ErrorAnalysis,
    EvaluationResult,
    NodeMetrics,
    PerformanceMetrics,
)


class TestCostMetrics:
    """Tests for the CostMetrics model."""

    def test_cost_metrics_default_values(self):
        """Test that CostMetrics initializes with correct default values."""
        cost_metrics = CostMetrics()

        assert cost_metrics.llm_input_tokens == 0
        assert cost_metrics.llm_output_tokens == 0
        assert cost_metrics.llm_total_tokens == 0
        assert cost_metrics.llm_input_cost == 0.0
        assert cost_metrics.llm_output_cost == 0.0
        assert cost_metrics.llm_total_cost == 0.0
        assert cost_metrics.llm_api_calls == 0
        assert cost_metrics.embedding_tokens == 0
        assert cost_metrics.embedding_cost == 0.0
        assert cost_metrics.embedding_api_calls == 0
        assert cost_metrics.total_cost == 0.0
        assert cost_metrics.cost_per_error_detected is None
        assert cost_metrics.llm_model_id is None
        assert cost_metrics.embedding_model_id is None

    def test_cost_metrics_with_values(self):
        """Test CostMetrics with actual cost values."""
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

        assert cost_metrics.llm_input_tokens == 50000
        assert cost_metrics.llm_output_tokens == 15000
        assert cost_metrics.llm_total_tokens == 65000
        assert cost_metrics.llm_input_cost == 0.04
        assert cost_metrics.llm_output_cost == 0.06
        assert cost_metrics.llm_total_cost == 0.10
        assert cost_metrics.llm_api_calls == 25
        assert cost_metrics.embedding_tokens == 1170000
        assert cost_metrics.embedding_cost == 0.0234
        assert cost_metrics.embedding_api_calls == 150
        assert cost_metrics.total_cost == 0.1234
        assert cost_metrics.cost_per_error_detected == 0.0012
        assert cost_metrics.llm_model_id == "amazon.nova-pro-v1:0"
        assert cost_metrics.embedding_model_id == "amazon.titan-embed-text-v2:0"

    def test_cost_metrics_validation_negative_values(self):
        """Test that CostMetrics rejects negative values."""
        with pytest.raises(ValueError):
            CostMetrics(llm_input_tokens=-100)

        with pytest.raises(ValueError):
            CostMetrics(llm_input_cost=-0.01)

        with pytest.raises(ValueError):
            CostMetrics(total_cost=-1.0)

    def test_cost_metrics_none_cost_per_error(self):
        """Test that cost_per_error_detected can be None."""
        cost_metrics = CostMetrics(total_cost=0.1234, cost_per_error_detected=None)

        assert cost_metrics.cost_per_error_detected is None


class TestNodeMetricsWithCost:
    """Tests for NodeMetrics with cost metrics integration."""

    def test_node_metrics_without_cost(self):
        """Test NodeMetrics without cost metrics (backward compatibility)."""
        node_metrics = NodeMetrics(
            node_name="llm_resolution", total_corrections=100, successful_corrections=85, success_rate=0.85
        )

        assert node_metrics.node_name == "llm_resolution"
        assert node_metrics.total_corrections == 100
        assert node_metrics.successful_corrections == 85
        assert node_metrics.success_rate == 0.85
        assert node_metrics.cost_metrics is None
        assert node_metrics.cost_per_correction is None

    def test_node_metrics_with_cost(self):
        """Test NodeMetrics with cost metrics."""
        cost_metrics = CostMetrics(
            llm_input_tokens=50000,
            llm_output_tokens=15000,
            llm_total_cost=0.10,
            total_cost=0.10,
            llm_model_id="amazon.nova-pro-v1:0",
        )

        node_metrics = NodeMetrics(
            node_name="llm_resolution",
            total_corrections=100,
            successful_corrections=85,
            success_rate=0.85,
            cost_metrics=cost_metrics,
            cost_per_correction=0.0012,
        )

        assert node_metrics.cost_metrics is not None
        assert node_metrics.cost_metrics.llm_input_tokens == 50000
        assert node_metrics.cost_metrics.llm_output_tokens == 15000
        assert node_metrics.cost_metrics.llm_total_cost == 0.10
        assert node_metrics.cost_per_correction == 0.0012


class TestEvaluationResultWithCost:
    """Tests for EvaluationResult with cost metrics integration."""

    def test_evaluation_result_without_cost(self):
        """Test EvaluationResult without cost metrics (backward compatibility)."""
        result = EvaluationResult(
            dataset_name="test_dataset",
            timestamp=datetime.now(),
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

        assert result.dataset_name == "test_dataset"
        assert result.cost_metrics is None

    def test_evaluation_result_with_cost(self):
        """Test EvaluationResult with cost metrics."""
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

        result = EvaluationResult(
            dataset_name="test_dataset",
            timestamp=datetime.now(),
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

        assert result.cost_metrics is not None
        assert result.cost_metrics.total_cost == 0.1234
        assert result.cost_metrics.cost_per_error_detected == 0.0012
        assert result.cost_metrics.llm_model_id == "amazon.nova-pro-v1:0"
        assert result.cost_metrics.embedding_model_id == "amazon.titan-embed-text-v2:0"
