# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for confidence configuration.

This module tests the ConfidenceConfig class and its integration
with the main ProcessorConfig.
"""


import pytest
from pydantic import ValidationError

from metadata_harmonization_processor.config import (
    ConfidenceConfig,
    ProcessorConfig,
    load_processor_settings,
)


class TestConfidenceConfig:
    """Test suite for ConfidenceConfig class."""

    def test_default_confidence_config(self):
        """Test default confidence configuration values."""
        config = ConfidenceConfig()

        assert config.enabled is True
        assert config.confidence_level_mapping == {
            "High": 0.9,
            "Medium": 0.65,
            "Low": 0.3,
        }
        assert config.semantic_high_threshold == 0.8
        assert config.semantic_medium_threshold == 0.5
        assert config.pattern_high_threshold == 0.7
        assert config.pattern_medium_threshold == 0.4
        assert config.schema_confidence_enabled is True
        assert config.llm_confidence_weight == 0.7
        assert config.similarity_weight == 0.3
        assert config.prediction_confidence_enabled is True

    def test_custom_confidence_config(self):
        """Test custom confidence configuration values."""
        config = ConfidenceConfig(
            enabled=False,
            confidence_level_mapping={"High": 0.95, "Medium": 0.7, "Low": 0.2},
            semantic_high_threshold=0.85,
            semantic_medium_threshold=0.6,
            pattern_high_threshold=0.75,
            pattern_medium_threshold=0.45,
            llm_confidence_weight=0.8,
            similarity_weight=0.2,
        )

        assert config.enabled is False
        assert config.confidence_level_mapping["High"] == 0.95
        assert config.semantic_high_threshold == 0.85
        assert config.semantic_medium_threshold == 0.6
        assert config.pattern_high_threshold == 0.75
        assert config.pattern_medium_threshold == 0.45
        assert config.llm_confidence_weight == 0.8
        assert config.similarity_weight == 0.2

    def test_confidence_level_mapping_validation(self):
        """Test validation of confidence level mapping."""
        # Missing required levels
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceConfig(confidence_level_mapping={"High": 0.9})
        assert "missing required levels" in str(exc_info.value)

        # Invalid score range
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceConfig(
                confidence_level_mapping={
                    "High": 1.5,  # Invalid: > 1.0
                    "Medium": 0.65,
                    "Low": 0.3,
                }
            )
        assert "must be between 0.0 and 1.0" in str(exc_info.value)

        # Invalid score type
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceConfig(
                confidence_level_mapping={
                    "High": "high",  # Invalid: not a number
                    "Medium": 0.65,
                    "Low": 0.3,
                }
            )
        assert "Input should be a valid number" in str(exc_info.value)

    def test_threshold_validation(self):
        """Test validation of threshold ordering."""
        # Semantic thresholds out of order
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceConfig(
                semantic_high_threshold=0.5,
                semantic_medium_threshold=0.8,  # Invalid: medium > high
            )
        assert "must be less than semantic_high_threshold" in str(exc_info.value)

        # Pattern thresholds out of order
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceConfig(
                pattern_high_threshold=0.4,
                pattern_medium_threshold=0.7,  # Invalid: medium > high
            )
        assert "must be less than pattern_high_threshold" in str(exc_info.value)

    def test_weight_validation(self):
        """Test validation of weight sum."""
        # Weights don't sum to 1.0
        with pytest.raises(ValidationError) as exc_info:
            ConfidenceConfig(
                llm_confidence_weight=0.8,
                similarity_weight=0.3,  # Invalid: 0.8 + 0.3 = 1.1
            )
        assert "must equal 1.0" in str(exc_info.value)

    def test_threshold_ranges(self):
        """Test threshold value ranges."""
        # Valid ranges
        config = ConfidenceConfig(
            semantic_high_threshold=1.0,
            semantic_medium_threshold=0.0,
            pattern_high_threshold=1.0,
            pattern_medium_threshold=0.0,
        )
        assert config.semantic_high_threshold == 1.0
        assert config.semantic_medium_threshold == 0.0

        # Invalid ranges
        with pytest.raises(ValidationError):
            ConfidenceConfig(semantic_high_threshold=1.5)  # > 1.0

        with pytest.raises(ValidationError):
            ConfidenceConfig(semantic_medium_threshold=-0.1)  # < 0.0


class TestProcessorConfigWithConfidence:
    """Test suite for ProcessorConfig with confidence integration."""

    def test_default_processor_config_includes_confidence(self):
        """Test that default ProcessorConfig includes confidence configuration."""
        config = ProcessorConfig(
            schema_directory="./test",
            session_saver_type="file",
            file_session_directory="./sessions",
            job_status_saver_type="local",
            job_status_storage_dir="./job_status",
            result_saver_type="local",
            results_local_dir="./results",
            enable_redis_cache=False,
        )

        assert hasattr(config, "confidence")
        assert isinstance(config.confidence, ConfidenceConfig)
        assert config.confidence.enabled is True

    def test_confidence_config_validation_in_processor(self):
        """Test confidence configuration validation in ProcessorConfig."""
        # Valid configuration should pass
        config = ProcessorConfig(
            schema_directory="./test",
            session_saver_type="file",
            file_session_directory="./sessions",
            job_status_saver_type="local",
            job_status_storage_dir="./job_status",
            result_saver_type="local",
            results_local_dir="./results",
            enable_redis_cache=False,
            confidence={
                "enabled": True,
                "semantic_high_threshold": 0.8,
                "semantic_medium_threshold": 0.5,
                "llm_confidence_weight": 0.7,
                "similarity_weight": 0.3,
            },
        )
        assert config.confidence.enabled is True

        # Invalid configuration should fail
        with pytest.raises(ValidationError) as exc_info:
            ProcessorConfig(
                schema_directory="./test",
                session_saver_type="file",
                file_session_directory="./sessions",
                job_status_saver_type="local",
                job_status_storage_dir="./job_status",
                result_saver_type="local",
                results_local_dir="./results",
                enable_redis_cache=False,
                confidence={
                    "enabled": True,
                    "semantic_high_threshold": 0.5,
                    "semantic_medium_threshold": 0.8,  # Invalid: medium > high
                    "llm_confidence_weight": 0.7,
                    "similarity_weight": 0.3,
                },
            )
        assert "semantic_medium_threshold" in str(exc_info.value)

    def test_confidence_disabled_validation_skipped(self):
        """Test that validation is skipped when confidence is disabled."""
        # This should not raise an error even with invalid thresholds
        # because confidence is disabled
        config = ProcessorConfig(
            schema_directory="./test",
            session_saver_type="file",
            file_session_directory="./sessions",
            job_status_saver_type="local",
            job_status_storage_dir="./job_status",
            result_saver_type="local",
            results_local_dir="./results",
            enable_redis_cache=False,
            confidence={
                "enabled": False,
                "semantic_high_threshold": 0.5,
                "semantic_medium_threshold": 0.8,  # Would be invalid if enabled
                "llm_confidence_weight": 0.7,
                "similarity_weight": 0.3,
            },
        )
        assert config.confidence.enabled is False

    def test_confidence_level_mapping_ordering_validation(self):
        """Test validation of confidence level mapping score ordering."""
        # Valid ordering: High > Medium > Low
        config = ProcessorConfig(
            schema_directory="./test",
            session_saver_type="file",
            file_session_directory="./sessions",
            job_status_saver_type="local",
            job_status_storage_dir="./job_status",
            result_saver_type="local",
            results_local_dir="./results",
            enable_redis_cache=False,
            confidence={"confidence_level_mapping": {"High": 0.9, "Medium": 0.6, "Low": 0.3}},
        )
        assert config.confidence.confidence_level_mapping["High"] == 0.9

        # Invalid ordering: High < Medium
        with pytest.raises(ValueError) as exc_info:
            ProcessorConfig(
                schema_directory="./test",
                session_saver_type="file",
                file_session_directory="./sessions",
                job_status_saver_type="local",
                job_status_storage_dir="./job_status",
                result_saver_type="local",
                results_local_dir="./results",
                enable_redis_cache=False,
                confidence={
                    "confidence_level_mapping": {
                        "High": 0.5,  # Invalid: High < Medium
                        "Medium": 0.6,
                        "Low": 0.3,
                    }
                },
            )
        assert "must be ordered: High > Medium > Low" in str(exc_info.value)


class TestConfidenceConfigLoading:
    """Test suite for loading confidence configuration from files."""

    def test_load_confidence_config_from_yaml(self, tmp_path):
        """Test loading confidence configuration from YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_content = """
schema_directory: "./test"
session_saver_type: "file"
file_session_directory: "./sessions"
job_status_saver_type: "local"
job_status_storage_dir: "./job_status"
result_saver_type: "local"
results_local_dir: "./results"
enable_redis_cache: false

confidence:
  enabled: true
  confidence_level_mapping:
    High: 0.95
    Medium: 0.7
    Low: 0.2
  semantic_high_threshold: 0.85
  semantic_medium_threshold: 0.6
  pattern_high_threshold: 0.75
  pattern_medium_threshold: 0.45
  llm_confidence_weight: 0.8
  similarity_weight: 0.2
"""
        config_file.write_text(config_content)

        config = load_processor_settings(config_file)

        assert config.confidence.enabled is True
        assert config.confidence.confidence_level_mapping["High"] == 0.95
        assert config.confidence.semantic_high_threshold == 0.85
        assert config.confidence.llm_confidence_weight == 0.8
        assert config.confidence.similarity_weight == 0.2

    def test_load_partial_confidence_config(self, tmp_path):
        """Test loading partial confidence configuration with defaults."""
        config_file = tmp_path / "test_config.yaml"
        config_content = """
schema_directory: "./test"
session_saver_type: "file"
file_session_directory: "./sessions"
job_status_saver_type: "local"
job_status_storage_dir: "./job_status"
result_saver_type: "local"
results_local_dir: "./results"
enable_redis_cache: false

confidence:
  enabled: false
  semantic_high_threshold: 0.9
"""
        config_file.write_text(config_content)

        config = load_processor_settings(config_file)

        assert config.confidence.enabled is False
        assert config.confidence.semantic_high_threshold == 0.9
        # Should use defaults for other values
        assert config.confidence.semantic_medium_threshold == 0.5
        assert config.confidence.confidence_level_mapping["High"] == 0.9

    def test_load_invalid_confidence_config(self, tmp_path):
        """Test loading invalid confidence configuration raises error."""
        config_file = tmp_path / "test_config.yaml"
        config_content = """
schema_directory: "./test"
session_saver_type: "file"
file_session_directory: "./sessions"
job_status_saver_type: "local"
job_status_storage_dir: "./job_status"
result_saver_type: "local"
results_local_dir: "./results"
enable_redis_cache: false

confidence:
  enabled: true
  semantic_high_threshold: 0.5
  semantic_medium_threshold: 0.8  # Invalid: medium > high
"""
        config_file.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            load_processor_settings(config_file)
        assert "semantic_medium_threshold" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])
