# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Tests for cost calculation integration in MetricsEngine.

This module tests the integration of cost calculation functionality
into the MetricsEngine, including overall cost metrics and per-node
cost metrics calculation.
"""

import pytest
from metadata_harmonization_processor.models import ProcessorState, NodeTokenUsage
from metadata_harmonization_eval.metrics_engine import MetricsEngine
from metadata_harmonization_eval.models import (
    BedrockPricingConfig,
    GroundTruth,
    GroundTruthEntry,
    NodeMetrics,
)


@pytest.fixture
def sample_ground_truth():
    """Create a sample ground truth for testing."""
    return GroundTruth(
        entries=[
            GroundTruthEntry(
                row=0,
                field="state",
                schema_field="state",
                original="California",
                error="CA",
                error_type="abbreviation",
                valid_options=["California", "Texas", "New York"],
            ),
            GroundTruthEntry(
                row=1,
                field="country",
                schema_field="country",
                original="United States",
                error="USA",
                error_type="abbreviation",
                valid_options=["United States", "Canada", "Mexico"],
            ),
        ],
        error_rate=0.5,
        total_errors=2,
    )


@pytest.fixture
def sample_processor_state():
    """Create a sample processor state with token usage."""
    state = ProcessorState(job_id="test-job", current_stage="completed")

    # Add token usage for LLM resolution node
    state.token_usage["llm_resolution"] = NodeTokenUsage(
        node_name="llm_resolution",
        llm_model_id="amazon.nova-pro-v1:0",
        llm_calls=5,
        llm_input_tokens=10000,
        llm_output_tokens=3000,
        embedding_calls=0,
        embedding_tokens=0,
    )

    # Add token usage for semantic prediction node
    state.token_usage["semantic_prediction"] = NodeTokenUsage(
        node_name="semantic_prediction",
        embedding_model_id="amazon.titan-embed-text-v2:0",
        llm_calls=0,
        llm_input_tokens=0,
        llm_output_tokens=0,
        embedding_calls=10,
        embedding_tokens=50000,
    )

    return state


@pytest.fixture
def sample_pricing_config():
    """Create a sample pricing configuration."""
    return BedrockPricingConfig(
        llm_models={"amazon.nova-pro-v1:0": {"input_price_per_1k": 0.0008, "output_price_per_1k": 0.0032}},
        embedding_models={"amazon.titan-embed-text-v2:0": 0.00002},
    )


@pytest.fixture
def sample_node_metrics():
    """Create sample node metrics."""
    return {
        "llm_resolution": NodeMetrics(
            node_name="llm_resolution",
            total_corrections=10,
            successful_corrections=8,
            success_rate=0.8,
            mean_confidence=0.85,
            median_confidence=0.87,
            high_confidence_count=7,
            high_confidence_percentage=0.7,
            error_type_breakdown={"abbreviation": 8, "fuzzy": 2},
        ),
        "semantic_prediction": NodeMetrics(
            node_name="semantic_prediction",
            total_corrections=5,
            successful_corrections=4,
            success_rate=0.8,
            mean_confidence=0.75,
            median_confidence=0.76,
            high_confidence_count=3,
            high_confidence_percentage=0.6,
            error_type_breakdown={"abbreviation": 4, "fuzzy": 1},
        ),
    }


class TestCostMetricsCalculation:
    """Tests for calculate_cost_metrics method."""

    def test_calculate_cost_metrics_basic(self, sample_ground_truth, sample_processor_state, sample_pricing_config):
        """Test basic cost metrics calculation."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        cost_metrics = metrics_engine.calculate_cost_metrics(
            state=sample_processor_state, pricing_config=sample_pricing_config, detected_errors_count=2
        )

        # Verify LLM token counts
        assert cost_metrics.llm_input_tokens == 10000
        assert cost_metrics.llm_output_tokens == 3000
        assert cost_metrics.llm_total_tokens == 13000
        assert cost_metrics.llm_api_calls == 5

        # Verify embedding token counts
        assert cost_metrics.embedding_tokens == 50000
        assert cost_metrics.embedding_api_calls == 10

        # Verify LLM costs
        expected_llm_input_cost = (10000 / 1000) * 0.0008
        expected_llm_output_cost = (3000 / 1000) * 0.0032
        expected_llm_total_cost = expected_llm_input_cost + expected_llm_output_cost

        assert cost_metrics.llm_input_cost == pytest.approx(expected_llm_input_cost, rel=1e-6)
        assert cost_metrics.llm_output_cost == pytest.approx(expected_llm_output_cost, rel=1e-6)
        assert cost_metrics.llm_total_cost == pytest.approx(expected_llm_total_cost, rel=1e-6)

        # Verify embedding costs
        expected_embedding_cost = (50000 / 1000) * 0.00002
        assert cost_metrics.embedding_cost == pytest.approx(expected_embedding_cost, rel=1e-6)

        # Verify total cost
        expected_total_cost = expected_llm_total_cost + expected_embedding_cost
        assert cost_metrics.total_cost == pytest.approx(expected_total_cost, rel=1e-6)

        # Verify cost per error
        expected_cost_per_error = expected_total_cost / 2
        assert cost_metrics.cost_per_error_detected == pytest.approx(expected_cost_per_error, rel=1e-6)

        # Verify model IDs
        assert cost_metrics.llm_model_id == "amazon.nova-pro-v1:0"
        assert cost_metrics.embedding_model_id == "amazon.titan-embed-text-v2:0"

    def test_calculate_cost_metrics_no_errors_detected(
        self, sample_ground_truth, sample_processor_state, sample_pricing_config
    ):
        """Test cost metrics calculation when no errors are detected."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        cost_metrics = metrics_engine.calculate_cost_metrics(
            state=sample_processor_state, pricing_config=sample_pricing_config, detected_errors_count=0
        )

        # Cost per error should be None when no errors detected
        assert cost_metrics.cost_per_error_detected is None

        # Total cost should still be calculated
        assert cost_metrics.total_cost > 0

    def test_calculate_cost_metrics_empty_token_usage(self, sample_ground_truth, sample_pricing_config):
        """Test cost metrics calculation with empty token usage."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        # Create state with no token usage
        empty_state = ProcessorState(job_id="test-job", current_stage="completed")

        cost_metrics = metrics_engine.calculate_cost_metrics(
            state=empty_state, pricing_config=sample_pricing_config, detected_errors_count=2
        )

        # All costs should be zero
        assert cost_metrics.llm_input_tokens == 0
        assert cost_metrics.llm_output_tokens == 0
        assert cost_metrics.embedding_tokens == 0
        assert cost_metrics.total_cost == 0.0
        assert cost_metrics.cost_per_error_detected == 0.0

    def test_calculate_cost_metrics_unknown_model(self, sample_ground_truth, sample_pricing_config):
        """Test cost metrics calculation with unknown model ID."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        # Create state with token usage but no model IDs set
        state = ProcessorState(job_id="test-job", current_stage="completed")
        state.token_usage["llm_resolution"] = NodeTokenUsage(
            node_name="llm_resolution",
            llm_calls=5,
            llm_input_tokens=10000,
            llm_output_tokens=3000,
            embedding_calls=0,
            embedding_tokens=0,
        )
        state.token_usage["semantic_prediction"] = NodeTokenUsage(
            node_name="semantic_prediction",
            llm_calls=0,
            llm_input_tokens=0,
            llm_output_tokens=0,
            embedding_calls=10,
            embedding_tokens=50000,
        )

        cost_metrics = metrics_engine.calculate_cost_metrics(
            state=state, pricing_config=sample_pricing_config, detected_errors_count=2
        )

        # Token counts should still be tracked
        assert cost_metrics.llm_input_tokens == 10000
        assert cost_metrics.llm_output_tokens == 3000
        assert cost_metrics.embedding_tokens == 50000

        # Costs should be zero due to missing pricing for "unknown" model
        assert cost_metrics.llm_total_cost == 0.0
        assert cost_metrics.embedding_cost == 0.0
        assert cost_metrics.total_cost == 0.0


class TestNodeCostMetricsCalculation:
    """Tests for calculate_node_cost_metrics method."""

    def test_calculate_node_cost_metrics_basic(
        self, sample_ground_truth, sample_processor_state, sample_pricing_config, sample_node_metrics
    ):
        """Test basic per-node cost metrics calculation."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        updated_node_metrics = metrics_engine.calculate_node_cost_metrics(
            state=sample_processor_state, pricing_config=sample_pricing_config, node_metrics=sample_node_metrics
        )

        # Verify llm_resolution node has cost metrics
        llm_node = updated_node_metrics["llm_resolution"]
        assert llm_node.cost_metrics is not None
        assert llm_node.cost_metrics.llm_input_tokens == 10000
        assert llm_node.cost_metrics.llm_output_tokens == 3000
        assert llm_node.cost_metrics.embedding_tokens == 0
        assert llm_node.cost_metrics.total_cost > 0

        # Verify cost per correction
        assert llm_node.cost_per_correction is not None
        expected_cost_per_correction = llm_node.cost_metrics.total_cost / 8  # 8 successful corrections
        assert llm_node.cost_per_correction == pytest.approx(expected_cost_per_correction, rel=1e-6)

        # Verify semantic_prediction node has cost metrics
        semantic_node = updated_node_metrics["semantic_prediction"]
        assert semantic_node.cost_metrics is not None
        assert semantic_node.cost_metrics.llm_input_tokens == 0
        assert semantic_node.cost_metrics.llm_output_tokens == 0
        assert semantic_node.cost_metrics.embedding_tokens == 50000
        assert semantic_node.cost_metrics.total_cost > 0

        # Verify cost per correction
        assert semantic_node.cost_per_correction is not None
        expected_cost_per_correction = semantic_node.cost_metrics.total_cost / 4  # 4 successful corrections
        assert semantic_node.cost_per_correction == pytest.approx(expected_cost_per_correction, rel=1e-6)

    def test_calculate_node_cost_metrics_no_successful_corrections(
        self, sample_ground_truth, sample_processor_state, sample_pricing_config
    ):
        """Test per-node cost metrics when node has no successful corrections."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        # Create node metrics with zero successful corrections
        node_metrics = {
            "llm_resolution": NodeMetrics(
                node_name="llm_resolution",
                total_corrections=5,
                successful_corrections=0,  # No successful corrections
                success_rate=0.0,
                mean_confidence=0.5,
                median_confidence=0.5,
                high_confidence_count=0,
                high_confidence_percentage=0.0,
                error_type_breakdown={},
            )
        }

        updated_node_metrics = metrics_engine.calculate_node_cost_metrics(
            state=sample_processor_state, pricing_config=sample_pricing_config, node_metrics=node_metrics
        )

        # Cost metrics should be populated
        assert updated_node_metrics["llm_resolution"].cost_metrics is not None

        # Cost per correction should be None
        assert updated_node_metrics["llm_resolution"].cost_per_correction is None

    def test_calculate_node_cost_metrics_node_not_in_metrics(self, sample_ground_truth, sample_pricing_config):
        """Test per-node cost metrics when node has token usage but no metrics."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        # Create state with token usage for a node not in node_metrics
        state = ProcessorState(job_id="test-job", current_stage="completed")
        state.token_usage["unknown_node"] = NodeTokenUsage(
            node_name="unknown_node",
            llm_calls=1,
            llm_input_tokens=1000,
            llm_output_tokens=500,
            embedding_calls=0,
            embedding_tokens=0,
        )

        # Empty node metrics
        node_metrics = {}

        # Should not raise an error
        updated_node_metrics = metrics_engine.calculate_node_cost_metrics(
            state=state, pricing_config=sample_pricing_config, node_metrics=node_metrics
        )

        # Node metrics should still be empty
        assert len(updated_node_metrics) == 0


class TestCostMetricsIntegration:
    """Integration tests for cost metrics in the full evaluation flow."""

    def test_cost_metrics_values_are_reasonable(
        self, sample_ground_truth, sample_processor_state, sample_pricing_config
    ):
        """Test that calculated cost values are reasonable."""
        metrics_engine = MetricsEngine(sample_ground_truth)

        cost_metrics = metrics_engine.calculate_cost_metrics(
            state=sample_processor_state, pricing_config=sample_pricing_config, detected_errors_count=2
        )

        # Costs should be positive
        assert cost_metrics.total_cost > 0
        assert cost_metrics.llm_total_cost > 0
        assert cost_metrics.embedding_cost > 0

        # Total cost should equal sum of components
        assert cost_metrics.total_cost == pytest.approx(
            cost_metrics.llm_total_cost + cost_metrics.embedding_cost, rel=1e-6
        )

        # LLM total should equal sum of input and output
        assert cost_metrics.llm_total_cost == pytest.approx(
            cost_metrics.llm_input_cost + cost_metrics.llm_output_cost, rel=1e-6
        )

        # Costs should be reasonable (not astronomical)
        assert cost_metrics.total_cost < 1.0  # Less than $1 for this small test
        assert cost_metrics.cost_per_error_detected < 0.1  # Less than $0.10 per error
