# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for confidence scoring utilities.

This module tests the confidence scoring functions and configuration
for both schema alignment recommendations and validation error predictions.
"""

import pytest

from metadata_harmonization_processor.config import ConfidenceConfig
from metadata_harmonization_processor.models.validation import ValidationErrorType
from metadata_harmonization_processor.utils.confidence_utils import (
    calculate_prediction_confidence,
    confidence_level_to_score,
    map_score_to_level,
    validate_confidence_level,
)


class TestConfidenceConfig:
    """Test ConfidenceConfig class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = ConfidenceConfig()

        assert config.confidence_level_mapping == {
            "High": 0.9,
            "Medium": 0.65,
            "Low": 0.3,
        }
        assert config.semantic_high_threshold == 0.8
        assert config.semantic_medium_threshold == 0.5
        assert config.pattern_high_threshold == 0.7
        assert config.pattern_medium_threshold == 0.4

    def test_custom_configuration(self):
        """Test custom configuration values."""
        custom_mapping = {"High": 0.95, "Medium": 0.7, "Low": 0.2}
        config = ConfidenceConfig(
            confidence_level_mapping=custom_mapping,
            semantic_high_threshold=0.85,
            semantic_medium_threshold=0.6,
            pattern_high_threshold=0.75,
            pattern_medium_threshold=0.45,
        )

        assert config.confidence_level_mapping == custom_mapping
        assert config.semantic_high_threshold == 0.85
        assert config.semantic_medium_threshold == 0.6
        assert config.pattern_high_threshold == 0.75
        assert config.pattern_medium_threshold == 0.45


class TestValidateConfidenceLevel:
    """Test validate_confidence_level function."""

    def test_valid_levels(self):
        """Test validation of valid confidence levels."""
        assert validate_confidence_level("High") == "High"
        assert validate_confidence_level("Medium") == "Medium"
        assert validate_confidence_level("Low") == "Low"

    def test_case_insensitive_matching(self):
        """Test case-insensitive confidence level matching."""
        assert validate_confidence_level("high") == "High"
        assert validate_confidence_level("HIGH") == "High"
        assert validate_confidence_level("medium") == "Medium"
        assert validate_confidence_level("MEDIUM") == "Medium"
        assert validate_confidence_level("low") == "Low"
        assert validate_confidence_level("LOW") == "Low"

    def test_common_variations(self):
        """Test common confidence level variations."""
        # High variations
        assert validate_confidence_level("hi") == "High"
        assert validate_confidence_level("good") == "High"
        assert validate_confidence_level("strong") == "High"
        assert validate_confidence_level("confident") == "High"

        # Medium variations
        assert validate_confidence_level("med") == "Medium"
        assert validate_confidence_level("moderate") == "Medium"
        assert validate_confidence_level("ok") == "Medium"
        assert validate_confidence_level("okay") == "Medium"
        assert validate_confidence_level("average") == "Medium"

        # Low variations
        assert validate_confidence_level("lo") == "Low"
        assert validate_confidence_level("poor") == "Low"
        assert validate_confidence_level("weak") == "Low"
        assert validate_confidence_level("uncertain") == "Low"
        assert validate_confidence_level("bad") == "Low"

    def test_invalid_inputs(self):
        """Test handling of invalid confidence level inputs."""
        assert validate_confidence_level("invalid") == "Low"
        assert validate_confidence_level("") == "Low"
        assert validate_confidence_level("xyz") == "Low"

    def test_non_string_inputs(self):
        """Test handling of non-string inputs."""
        assert validate_confidence_level(None) == "Low"
        assert validate_confidence_level(123) == "Low"
        assert validate_confidence_level([]) == "Low"


class TestConfidenceLevelToScore:
    """Test confidence_level_to_score function."""

    def test_default_mapping(self):
        """Test default confidence level to score mapping."""
        assert confidence_level_to_score("High") == 0.9
        assert confidence_level_to_score("Medium") == 0.65
        assert confidence_level_to_score("Low") == 0.3

    def test_custom_config_mapping(self):
        """Test confidence level to score mapping with custom config."""
        custom_mapping = {"High": 0.95, "Medium": 0.7, "Low": 0.2}
        config = ConfidenceConfig(confidence_level_mapping=custom_mapping)

        assert confidence_level_to_score("High", config) == 0.95
        assert confidence_level_to_score("Medium", config) == 0.7
        assert confidence_level_to_score("Low", config) == 0.2

    def test_invalid_level(self):
        """Test handling of invalid confidence levels."""
        assert confidence_level_to_score("Invalid") == 0.3
        assert confidence_level_to_score("") == 0.3

    def test_score_bounds(self):
        """Test that scores are within valid bounds."""
        # Test that invalid mappings are rejected by validation
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            ConfidenceConfig(
                confidence_level_mapping={
                    "High": 1.5,  # Above 1.0 - should fail validation
                    "Medium": 0.5,
                    "Low": 0.2,
                }
            )

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            ConfidenceConfig(
                confidence_level_mapping={
                    "High": 0.9,
                    "Medium": -0.5,  # Below 0.0 - should fail validation
                    "Low": 0.2,
                }
            )


class TestCalculatePredictionConfidence:
    """Test calculate_prediction_confidence function."""

    def test_invalid_option_confidence(self):
        """Test confidence calculation for INVALID_OPTION errors."""
        config = ConfidenceConfig()

        # High confidence
        score, level = calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, 0.9, config)
        assert score == 0.9
        assert level == "High"

        # Medium confidence
        score, level = calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, 0.6, config)
        assert score == 0.65
        assert level == "Medium"

        # Low confidence
        score, level = calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, 0.3, config)
        assert score == 0.3
        assert level == "Low"

    def test_invalid_pattern_confidence(self):
        """Test confidence calculation for INVALID_PATTERN errors."""
        config = ConfidenceConfig()

        # High confidence with pattern strength
        score, level = calculate_prediction_confidence(
            ValidationErrorType.INVALID_PATTERN, 0.5, config, pattern_strength=0.8
        )
        assert score == 0.9
        assert level == "High"

        # Medium confidence with pattern strength
        score, level = calculate_prediction_confidence(
            ValidationErrorType.INVALID_PATTERN, 0.5, config, pattern_strength=0.6
        )
        assert score == 0.65
        assert level == "Medium"

        # Low confidence with pattern strength
        score, level = calculate_prediction_confidence(
            ValidationErrorType.INVALID_PATTERN, 0.5, config, pattern_strength=0.3
        )
        assert score == 0.3
        assert level == "Low"

        # Fallback to similarity score when pattern_strength is None
        score, level = calculate_prediction_confidence(ValidationErrorType.INVALID_PATTERN, 0.8, config)
        assert score == 0.9
        assert level == "High"

    def test_required_value_confidence(self):
        """Test confidence calculation for REQUIRED_VALUE errors."""
        config = ConfidenceConfig()

        # High confidence
        score, level = calculate_prediction_confidence(ValidationErrorType.REQUIRED_VALUE, 0.8, config)
        assert score == 0.9
        assert level == "High"

        # Medium confidence
        score, level = calculate_prediction_confidence(ValidationErrorType.REQUIRED_VALUE, 0.5, config)
        assert score == 0.65
        assert level == "Medium"

        # Low confidence
        score, level = calculate_prediction_confidence(ValidationErrorType.REQUIRED_VALUE, 0.3, config)
        assert score == 0.3
        assert level == "Low"

    def test_unknown_error_type(self):
        """Test confidence calculation for unknown error types."""
        config = ConfidenceConfig()

        # Should default to Low confidence for unknown error types
        score, level = calculate_prediction_confidence("UNKNOWN_ERROR_TYPE", 0.9, config)
        assert score == 0.3
        assert level == "Low"

    def test_similarity_score_bounds(self):
        """Test that similarity scores are properly bounded."""
        config = ConfidenceConfig()

        # Test score above 1.0
        score, level = calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, 1.5, config)
        assert score <= 1.0

        # Test score below 0.0
        score, level = calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, -0.5, config)
        assert score >= 0.0

    def test_default_config(self):
        """Test confidence calculation with default config."""
        # Should work without providing config
        score, level = calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, 0.85)
        assert score == 0.9
        assert level == "High"


class TestMapScoreToLevel:
    """Test map_score_to_level function."""

    def test_default_mapping(self):
        """Test default score to level mapping."""
        assert map_score_to_level(0.9) == "High"
        assert map_score_to_level(0.8) == "High"
        assert map_score_to_level(0.7) == "Medium"
        assert map_score_to_level(0.5) == "Medium"
        assert map_score_to_level(0.4) == "Low"
        assert map_score_to_level(0.1) == "Low"

    def test_custom_config_mapping(self):
        """Test score to level mapping with custom config."""
        config = ConfidenceConfig(semantic_high_threshold=0.9, semantic_medium_threshold=0.6)

        assert map_score_to_level(0.95, config) == "High"
        assert map_score_to_level(0.9, config) == "High"
        assert map_score_to_level(0.8, config) == "Medium"
        assert map_score_to_level(0.6, config) == "Medium"
        assert map_score_to_level(0.5, config) == "Low"

    def test_boundary_values(self):
        """Test boundary values for score to level mapping."""
        config = ConfidenceConfig()

        # Test exact threshold values
        assert map_score_to_level(0.8, config) == "High"  # Exactly at high threshold
        assert map_score_to_level(0.5, config) == "Medium"  # Exactly at medium threshold

        # Test just below thresholds
        assert map_score_to_level(0.79, config) == "Medium"
        assert map_score_to_level(0.49, config) == "Low"

    def test_score_bounds(self):
        """Test that scores are properly bounded."""
        config = ConfidenceConfig()

        # Test score above 1.0
        assert map_score_to_level(1.5, config) == "High"

        # Test score below 0.0
        assert map_score_to_level(-0.5, config) == "Low"

        # Test exact bounds
        assert map_score_to_level(1.0, config) == "High"
        assert map_score_to_level(0.0, config) == "Low"


class TestIntegration:
    """Integration tests for confidence utilities."""

    def test_round_trip_conversion(self):
        """Test round-trip conversion between levels and scores."""
        config = ConfidenceConfig()

        # Test level -> score -> level
        for level in ["High", "Medium", "Low"]:
            score = confidence_level_to_score(level, config)
            mapped_level = map_score_to_level(score, config)
            assert mapped_level == level

    def test_confidence_workflow(self):
        """Test complete confidence scoring workflow."""
        config = ConfidenceConfig()

        # Simulate LLM confidence extraction and validation
        llm_output = "high"
        validated_level = validate_confidence_level(llm_output)
        assert validated_level == "High"

        # Convert to numerical score
        confidence_score = confidence_level_to_score(validated_level, config)
        assert confidence_score == 0.9

        # Calculate prediction confidence
        pred_score, pred_level = calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, 0.85, config)
        assert pred_score == 0.9
        assert pred_level == "High"

        # Map score back to level
        mapped_level = map_score_to_level(pred_score, config)
        assert mapped_level == "High"
