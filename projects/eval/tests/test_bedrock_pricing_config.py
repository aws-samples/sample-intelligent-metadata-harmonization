# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Tests for BedrockPricingConfig model and YAML loading.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from metadata_harmonization_eval.models import BedrockPricingConfig, EvaluationConfig


class TestBedrockPricingConfig:
    """Test suite for BedrockPricingConfig model."""

    def test_default_pricing(self):
        """Test that default pricing values are set correctly."""
        config = BedrockPricingConfig()

        # Verify default LLM pricing
        assert "amazon.nova-pro-v1:0" in config.llm_models
        assert config.llm_models["amazon.nova-pro-v1:0"]["input_price_per_1k"] == 0.0008
        assert config.llm_models["amazon.nova-pro-v1:0"]["output_price_per_1k"] == 0.0032

        # Verify default embedding pricing
        assert "amazon.titan-embed-text-v2:0" in config.embedding_models
        assert config.embedding_models["amazon.titan-embed-text-v2:0"] == 0.00002

    def test_custom_pricing(self):
        """Test creating config with custom pricing."""
        config = BedrockPricingConfig(
            llm_models={"custom-model": {"input_price_per_1k": 0.001, "output_price_per_1k": 0.002}},
            embedding_models={"custom-embedding": 0.0001},
        )

        assert "custom-model" in config.llm_models
        assert config.llm_models["custom-model"]["input_price_per_1k"] == 0.001
        assert config.embedding_models["custom-embedding"] == 0.0001

    def test_negative_pricing_validation(self):
        """Test that negative pricing values are rejected."""
        # Test negative LLM input price
        with pytest.raises(ValueError, match="negative input_price_per_1k"):
            BedrockPricingConfig(
                llm_models={"test-model": {"input_price_per_1k": -0.001, "output_price_per_1k": 0.002}}
            )

        # Test negative LLM output price
        with pytest.raises(ValueError, match="negative output_price_per_1k"):
            BedrockPricingConfig(
                llm_models={"test-model": {"input_price_per_1k": 0.001, "output_price_per_1k": -0.002}}
            )

        # Test negative embedding price
        with pytest.raises(ValueError, match="negative price"):
            BedrockPricingConfig(embedding_models={"test-embedding": -0.0001})

    def test_from_yaml(self):
        """Test loading pricing config from YAML file."""
        yaml_content = {
            "llm_models": {"test-llm": {"input_price_per_1k": 0.005, "output_price_per_1k": 0.010}},
            "embedding_models": {"test-embed": 0.0002},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)

        try:
            config = BedrockPricingConfig.from_yaml(temp_path)

            assert "test-llm" in config.llm_models
            assert config.llm_models["test-llm"]["input_price_per_1k"] == 0.005
            assert config.llm_models["test-llm"]["output_price_per_1k"] == 0.010
            assert config.embedding_models["test-embed"] == 0.0002
        finally:
            temp_path.unlink()

    def test_from_yaml_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError, match="Pricing configuration file not found"):
            BedrockPricingConfig.from_yaml(Path("/nonexistent/path.yaml"))

    def test_from_yaml_invalid_syntax(self):
        """Test that ValueError is raised for invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid YAML syntax"):
                BedrockPricingConfig.from_yaml(temp_path)
        finally:
            temp_path.unlink()


class TestEvaluationConfigWithPricing:
    """Test EvaluationConfig integration with BedrockPricingConfig."""

    def test_evaluation_config_default_pricing(self):
        """Test that EvaluationConfig includes default pricing."""
        config = EvaluationConfig.from_defaults()

        assert config.bedrock_pricing is not None
        assert isinstance(config.bedrock_pricing, BedrockPricingConfig)
        assert "amazon.nova-pro-v1:0" in config.bedrock_pricing.llm_models

    def test_evaluation_config_from_yaml_with_pricing(self):
        """Test loading EvaluationConfig with pricing from YAML."""
        yaml_content = {
            "processor_config_path": "test_config.yaml",
            "data_directory": "test_data",
            "schema_program_id": "test_program",
            "schema_core_id": "test_core",
            "bedrock_pricing": {
                "llm_models": {"custom-llm": {"input_price_per_1k": 0.003, "output_price_per_1k": 0.006}},
                "embedding_models": {"custom-embed": 0.0003},
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)

        # Create dummy files for validation
        processor_config = temp_path.parent / "test_config.yaml"
        data_dir = temp_path.parent / "test_data"

        try:
            processor_config.touch()
            data_dir.mkdir(exist_ok=True)

            config = EvaluationConfig.from_yaml(temp_path)

            assert config.bedrock_pricing is not None
            assert "custom-llm" in config.bedrock_pricing.llm_models
            assert config.bedrock_pricing.llm_models["custom-llm"]["input_price_per_1k"] == 0.003
            assert config.bedrock_pricing.embedding_models["custom-embed"] == 0.0003
        finally:
            temp_path.unlink()
            if processor_config.exists():
                processor_config.unlink()
            if data_dir.exists():
                data_dir.rmdir()

    def test_evaluation_config_from_yaml_without_pricing(self):
        """Test that EvaluationConfig uses default pricing when not specified in YAML."""
        yaml_content = {
            "processor_config_path": "test_config.yaml",
            "data_directory": "test_data",
            "schema_program_id": "test_program",
            "schema_core_id": "test_core",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)

        # Create dummy files for validation
        processor_config = temp_path.parent / "test_config.yaml"
        data_dir = temp_path.parent / "test_data"

        try:
            processor_config.touch()
            data_dir.mkdir(exist_ok=True)

            config = EvaluationConfig.from_yaml(temp_path)

            # Should have default pricing
            assert config.bedrock_pricing is not None
            assert "amazon.nova-pro-v1:0" in config.bedrock_pricing.llm_models
            assert "amazon.titan-embed-text-v2:0" in config.bedrock_pricing.embedding_models
        finally:
            temp_path.unlink()
            if processor_config.exists():
                processor_config.unlink()
            if data_dir.exists():
                data_dir.rmdir()
