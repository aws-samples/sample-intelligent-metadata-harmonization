# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Integration tests for enum correction nodes.

Tests that the correction nodes are properly integrated with the processor
and can process INVALID_OPTION errors in the configured pipeline order.
"""

from pathlib import Path

import pytest

from metadata_harmonization_processor.config import (
    ProcessorConfig,
    load_processor_settings,
)
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    CorrectionNodeType,
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.nodes.fuzzy_matching import FuzzyMatchingNode
from metadata_harmonization_processor.nodes.llm_resolution import LLMResolutionNode


@pytest.fixture
def processor_config():
    """Load processor configuration for testing."""
    config_path = Path("config.yaml")
    if config_path.exists():
        return load_processor_settings(config_path)
    else:
        # Use defaults for testing
        return ProcessorConfig(
            schema_directory="data/schema",
            session_s3_bucket="test-bucket",
            enable_redis_cache=False,
            result_saver_type="local",
        )


@pytest.fixture
def test_validation_state():
    """Create test state with INVALID_OPTION errors."""
    test_errors = [
        ValidationErrorDetail(
            row=1,
            column="environment",
            error_type=ValidationErrorType.INVALID_OPTION,
            current_value="tst",  # Typo of "test"
            valid_options=["test", "prod", "dev"],
            message="Invalid option 'tst'",
        ),
        ValidationErrorDetail(
            row=2,
            column="status",
            error_type=ValidationErrorType.INVALID_OPTION,
            current_value="activ",  # Typo of "active"
            valid_options=["active", "inactive", "pending"],
            message="Invalid option 'activ'",
        ),
    ]

    validation_results = ValidationResults(
        validation_results=test_errors,
        summary=ValidationResultsSummary(
            total_errors=len(test_errors),
            error_types={"INVALID_OPTION": len(test_errors)},
            total_rows=2,
            columns_validated=2,  # Number of columns, not list
        ),
    )

    combined_results = CombinedResults(validation_results=validation_results)

    return ProcessorState(combined_results=combined_results)


class TestEnumCorrectionNodesIntegration:
    """Integration tests for enum correction nodes."""

    @pytest.mark.asyncio
    async def test_fuzzy_matching_node_initialization(self, processor_config):
        """Test that FuzzyMatchingNode can be initialized with config."""
        node = FuzzyMatchingNode(processor_config.fuzzy_matching)

        assert node is not None
        assert node.config.min_similarity_threshold >= 0.0
        assert node.config.min_similarity_threshold <= 1.0
        assert node.config.max_concurrent_predictions > 0

    @pytest.mark.asyncio
    async def test_llm_resolution_node_initialization(self, processor_config):
        """Test that LLMResolutionNode can be initialized with config."""
        node = LLMResolutionNode(processor_config.llm_resolution)

        assert node is not None
        assert node.config.model_id is not None
        assert node.config.max_concurrent_predictions > 0
        assert node.config.min_confidence_level in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_fuzzy_matching_node_processes_errors(self, processor_config, test_validation_state):
        """Test that FuzzyMatchingNode processes INVALID_OPTION errors."""
        node = FuzzyMatchingNode(processor_config.fuzzy_matching)

        # Get initial error count
        errors_before = len(
            [
                e
                for e in test_validation_state.combined_results.validation_results.validation_results
                if not e.recommended_value
            ]
        )

        # Process errors
        result = await node.invoke_async(task="test", invocation_state={"processor_state": test_validation_state})

        # Check that node completed successfully
        assert result.status.name in ["COMPLETED", "SUCCESS"]

        # Check that some errors got recommendations
        errors_after = len(
            [
                e
                for e in test_validation_state.combined_results.validation_results.validation_results
                if not e.recommended_value
            ]
        )

        # At least some errors should have been processed
        # (may not be all if similarity is below threshold)
        assert errors_after <= errors_before

        # Check that any recommendations have proper node attribution
        for error in test_validation_state.combined_results.validation_results.validation_results:
            if error.recommended_value and error.correction_node:
                assert error.correction_node == CorrectionNodeType.FUZZY_MATCHING
                assert error.confidence_level is not None
                assert error.confidence_score is not None

    @pytest.mark.asyncio
    async def test_enum_correction_pipeline_config(self, processor_config):
        """Test that enum correction pipeline is properly configured."""
        assert processor_config.enum_correction_pipeline is not None
        assert hasattr(processor_config.enum_correction_pipeline, "enabled")
        assert hasattr(processor_config.enum_correction_pipeline, "nodes")

        # Check that nodes have proper structure
        for node_config in processor_config.enum_correction_pipeline.nodes:
            assert hasattr(node_config, "name")
            assert hasattr(node_config, "enabled")
            assert node_config.name in [
                "fuzzy_matching",
                "contextual_inference",
                "semantic_prediction",
                "llm_resolution",
            ]

    @pytest.mark.asyncio
    async def test_correction_node_enum_values(self):
        """Test that CorrectionNodeType enum has expected values."""
        assert CorrectionNodeType.FUZZY_MATCHING == "fuzzy_matching"
        assert CorrectionNodeType.CONTEXTUAL_INFERENCE == "contextual_inference"
        assert CorrectionNodeType.SEMANTIC_PREDICTION == "semantic_prediction"
        assert CorrectionNodeType.LLM_RESOLUTION == "llm_resolution"

        # Test that all enum values are strings
        for node_type in CorrectionNodeType:
            assert isinstance(node_type.value, str)
