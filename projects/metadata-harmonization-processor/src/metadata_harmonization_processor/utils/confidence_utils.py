# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Confidence scoring utilities for metadata harmonization processing.

This module provides functions for calculating and managing confidence scores
for both schema alignment recommendations and validation error predictions.
"""

from typing import TYPE_CHECKING, Optional, Tuple

from loguru import logger

from ..models.validation import ValidationErrorType

if TYPE_CHECKING:
    from ..config import ConfidenceConfig


def validate_confidence_level(level: str) -> str:
    """Validate and normalize confidence level from LLM output.

    This function takes a confidence level string (potentially with inconsistent
    casing or invalid values) and returns a normalized, valid confidence level.

    Args:
        level: Confidence level string from LLM (e.g., "high", "HIGH", "Medium", etc.)

    Returns:
        Normalized confidence level: "High", "Medium", or "Low"

    Examples:
        >>> validate_confidence_level("high")
        "High"
        >>> validate_confidence_level("MEDIUM")
        "Medium"
        >>> validate_confidence_level("invalid")
        "Low"
    """
    if not isinstance(level, str):
        logger.warning(f"Invalid confidence level type '{type(level)}', defaulting to Low")
        return "Low"

    valid_levels = ["High", "Medium", "Low"]

    # Check if already properly formatted
    if level in valid_levels:
        return level

    # Try case-insensitive matching
    level_lower = level.lower().strip()
    for valid_level in valid_levels:
        if valid_level.lower() == level_lower:
            return valid_level

    # Handle common variations
    if level_lower in ["hi", "good", "strong", "confident"]:
        return "High"
    elif level_lower in ["med", "moderate", "ok", "okay", "average"]:
        return "Medium"
    elif level_lower in ["lo", "poor", "weak", "uncertain", "bad"]:
        return "Low"

    # Default to Low for invalid levels
    logger.warning(f"Invalid confidence level '{level}', defaulting to Low")
    return "Low"


def confidence_level_to_score(level: str, config: Optional["ConfidenceConfig"] = None) -> float:
    """Convert confidence level to numerical score.

    This function converts a human-readable confidence level to a numerical
    score between 0.0 and 1.0 using the provided configuration mapping.

    Args:
        level: Confidence level ("High", "Medium", or "Low")
        config: Optional confidence configuration with custom mapping

    Returns:
        Numerical confidence score between 0.0 and 1.0

    Examples:
        >>> confidence_level_to_score("High")
        0.9
        >>> confidence_level_to_score("Medium")
        0.65
        >>> confidence_level_to_score("Low")
        0.3
    """
    if config and config.confidence_level_mapping:
        score = config.confidence_level_mapping.get(level, 0.3)
    else:
        # Default mapping
        level_mapping = {"High": 0.9, "Medium": 0.65, "Low": 0.3}
        score = level_mapping.get(level, 0.3)

    # Ensure score is within valid range
    return max(0.0, min(1.0, score))


def calculate_prediction_confidence(
    error_type: ValidationErrorType,
    similarity_score: float,
    config: Optional["ConfidenceConfig"] = None,
    pattern_strength: Optional[float] = None,
) -> Tuple[float, str]:
    """Calculate confidence for validation error predictions.

    This function calculates both numerical confidence scores and human-readable
    confidence levels for validation error predictions based on the error type
    and similarity metrics.

    Args:
        error_type: Type of validation error (INVALID_OPTION, INVALID_PATTERN, etc.)
        similarity_score: Similarity score between 0.0 and 1.0
        config: Optional confidence configuration with custom thresholds
        pattern_strength: Optional pattern matching strength (for INVALID_PATTERN errors)

    Returns:
        Tuple of (confidence_score, confidence_level)

    Examples:
        >>> calculate_prediction_confidence(ValidationErrorType.INVALID_OPTION, 0.95)
        (0.9, "High")
        >>> calculate_prediction_confidence(ValidationErrorType.INVALID_PATTERN, 0.4)
        (0.3, "Low")
    """
    if config is None:
        # Import here to avoid circular imports
        from ..config import ConfidenceConfig

        config = ConfidenceConfig()

    # Ensure similarity_score is within valid range
    similarity_score = max(0.0, min(1.0, similarity_score))

    if error_type == ValidationErrorType.INVALID_OPTION:
        # Use semantic similarity for confidence
        if similarity_score >= config.semantic_high_threshold:
            confidence_level = "High"
        elif similarity_score >= config.semantic_medium_threshold:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

    elif error_type == ValidationErrorType.INVALID_PATTERN:
        # Use pattern strength for confidence, fallback to similarity_score
        pattern_score = pattern_strength if pattern_strength is not None else similarity_score
        pattern_score = max(0.0, min(1.0, pattern_score))

        if pattern_score >= config.pattern_high_threshold:
            confidence_level = "High"
        elif pattern_score >= config.pattern_medium_threshold:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

    elif error_type == ValidationErrorType.REQUIRED_VALUE:
        # For required values, use similarity score with pattern thresholds
        if similarity_score >= config.pattern_high_threshold:
            confidence_level = "High"
        elif similarity_score >= config.pattern_medium_threshold:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

    else:
        # Default for unknown error types
        logger.warning(f"Unknown error type '{error_type}', using Low confidence")
        confidence_level = "Low"

    # Convert level to numerical score
    confidence_score = confidence_level_to_score(confidence_level, config)

    logger.debug(
        f"Calculated confidence for {error_type}: "
        f"similarity={similarity_score:.3f}, "
        f"pattern_strength={pattern_strength}, "
        f"level={confidence_level}, "
        f"score={confidence_score:.3f}"
    )

    return confidence_score, confidence_level


def map_score_to_level(score: float, config: Optional["ConfidenceConfig"] = None) -> str:
    """Map a numerical confidence score back to a confidence level.

    This utility function converts a numerical confidence score to the
    corresponding human-readable confidence level.

    Args:
        score: Numerical confidence score between 0.0 and 1.0
        config: Optional confidence configuration with custom thresholds

    Returns:
        Confidence level: "High", "Medium", or "Low"

    Examples:
        >>> map_score_to_level(0.95)
        "High"
        >>> map_score_to_level(0.6)
        "Medium"
        >>> map_score_to_level(0.2)
        "Low"
    """
    if config is None:
        # Import here to avoid circular imports
        from ..config import ConfidenceConfig

        config = ConfidenceConfig()

    # Ensure score is within valid range
    score = max(0.0, min(1.0, score))

    # Use semantic thresholds as the default mapping
    if score >= config.semantic_high_threshold:
        return "High"
    elif score >= config.semantic_medium_threshold:
        return "Medium"
    else:
        return "Low"
