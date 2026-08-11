# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Pattern-based prediction node for metadata harmonization processing.

This module implements pattern matching and heuristic-based recommendations
for INVALID_PATTERN and REQUIRED_VALUE validation errors. It inherits from
MultiAgentBase for AWS Strands integration with proper session management.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import ContentBlock, Message

from ..config import ConfidenceConfig
from ..models.state import ProcessorState
from ..models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
)
from ..utils.confidence_utils import calculate_prediction_confidence


class PatternBasedPredictionNode(MultiAgentBase):
    """
    MultiAgentBase node for pattern-based predictions on INVALID_PATTERN and REQUIRED_VALUE errors.

    This node applies pattern matching algorithms and heuristics to suggest
    corrections for validation errors that don't require semantic understanding.
    It inherits from MultiAgentBase for AWS Strands session management and
    standardized result handling.
    """

    def __init__(self):
        """Initialize the pattern-based prediction node."""
        self._common_patterns = self._initialize_common_patterns()
        self._date_patterns = self._initialize_date_patterns()
        self._numeric_patterns = self._initialize_numeric_patterns()

        # Initialize confidence configuration
        self._confidence_config = ConfidenceConfig()

    async def invoke_async(
        self,
        task: str | list[ContentBlock],
        invocation_state: dict[str, Any] | None = None,
        **kwargs,
    ) -> MultiAgentResult:
        """
        Process pattern predictions using MultiAgentBase framework.

        Args:
            task: Task content (string or ContentBlock list)
            invocation_state: State dictionary containing ProcessorState with validation results
            **kwargs: Additional keyword arguments (unused)

        Returns:
            MultiAgentResult with AgentResult containing processing outcome
        """
        try:
            # Get ProcessorState from invocation_state
            if not invocation_state or "processor_state" not in invocation_state:
                error_msg = "ProcessorState must be provided in invocation_state"
                logger.error(error_msg)
                return MultiAgentResult(
                    status=Status.FAILED,
                    results={"pattern_prediction": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
                )

            state = invocation_state["processor_state"]

            if not state.has_validation_results():
                error_msg = "ProcessorState must contain validation_results"
                logger.error(error_msg)
                return MultiAgentResult(
                    status=Status.FAILED,
                    results={"pattern_prediction": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
                )

            state.set_current_stage("pattern_prediction")
            logger.info("Starting pattern-based prediction")

            # Save initial state to session
            await self._save_state_to_session("pattern_prediction_start", state)

            # Filter errors that can be handled by pattern-based prediction
            pattern_errors = self._filter_pattern_errors(state.combined_results.validation_results.validation_results)

            if not pattern_errors:
                logger.info("No pattern-based errors found to process")
                await self._save_state_to_session("pattern_prediction_skipped", state)

                # Create success AgentResult
                success_message: Message = {"content": [{"text": "No pattern-based errors found to process"}]}
                agent_result = AgentResult(
                    stop_reason="end_turn",
                    message=success_message,
                    metrics=EventLoopMetrics(),
                    state={"processed_errors": 0, "total_errors": 0},
                )

                return MultiAgentResult(
                    status=Status.COMPLETED,
                    results={"pattern_prediction": NodeResult(result=agent_result, status=Status.COMPLETED)},
                )

            logger.info(f"Processing {len(pattern_errors)} pattern-based errors")

            # Process each error and add recommendations with confidence
            processed_count = 0
            for error in pattern_errors:
                try:
                    recommendation, pattern_strength = await self._generate_recommendation_with_confidence(error)
                    if recommendation:
                        error.recommended_value = recommendation

                        # Calculate and set confidence scores
                        confidence_score, confidence_level = calculate_prediction_confidence(
                            error.error_type,
                            pattern_strength,
                            self._confidence_config,
                            pattern_strength,
                        )
                        error.confidence_score = confidence_score
                        error.confidence_level = confidence_level

                        logger.debug(
                            f"Generated recommendation '{recommendation}' for error in row {error.row}, column {error.column} "
                            f"with confidence {confidence_level} ({confidence_score:.3f})"
                        )
                    processed_count += 1

                    # Save progress periodically
                    if processed_count % 10 == 0:
                        await self._save_progress_to_session(processed_count, len(pattern_errors))

                except Exception as e:
                    logger.warning(
                        f"Failed to generate recommendation for error in row {error.row}, column {error.column}: {e}"
                    )
                    # Continue processing other errors even if one fails
                    continue

            # Save final state to session
            await self._save_state_to_session("pattern_prediction_complete", state)

            logger.info("Pattern-based prediction processing completed")

            # Create success AgentResult with processing summary
            success_message: Message = {
                "content": [
                    {
                        "text": f"Pattern-based prediction completed. Processed {processed_count} errors, generated {len([e for e in pattern_errors if e.recommended_value])} recommendations."
                    }
                ]
            }
            agent_result = AgentResult(
                stop_reason="end_turn",
                message=success_message,
                metrics=EventLoopMetrics(),
                state={
                    "processed_errors": processed_count,
                    "total_errors": len(pattern_errors),
                },
            )

            return MultiAgentResult(
                status=Status.COMPLETED,
                results={"pattern_prediction": NodeResult(result=agent_result, status=Status.COMPLETED)},
            )

        except Exception as e:
            job_id = (
                getattr(state, "job_id", "unknown") if "state" in locals() and hasattr(state, "job_id") else "unknown"
            )
            error_msg = f"Pattern-based prediction failed for job {job_id}: {e}"
            logger.error(error_msg)

            return MultiAgentResult(
                status=Status.FAILED,
                results={"pattern_prediction": NodeResult(result=e, status=Status.FAILED)},
            )

    def _filter_pattern_errors(self, errors: List[ValidationErrorDetail]) -> List[ValidationErrorDetail]:
        """
        Filter errors that can be handled by pattern-based prediction.

        Args:
            errors: List of all validation errors

        Returns:
            List of errors that are INVALID_PATTERN or REQUIRED_VALUE types
        """
        return [
            error
            for error in errors
            if error.error_type in [ValidationErrorType.INVALID_PATTERN, ValidationErrorType.REQUIRED_VALUE]
        ]

    async def _generate_recommendation_with_confidence(
        self, error: ValidationErrorDetail
    ) -> Tuple[Optional[str], float]:
        """
        Generate a recommendation for a specific validation error with confidence score.

        Args:
            error: ValidationErrorDetail to generate recommendation for

        Returns:
            Tuple of (recommended value string or None, pattern strength score)
        """
        if error.error_type == ValidationErrorType.INVALID_PATTERN:
            return self._handle_invalid_pattern_with_confidence(error)
        elif error.error_type == ValidationErrorType.REQUIRED_VALUE:
            return self._handle_required_value_with_confidence(error)
        else:
            return None, 0.0

    def _handle_invalid_pattern_with_confidence(self, error: ValidationErrorDetail) -> Tuple[Optional[str], float]:
        """
        Handle INVALID_PATTERN errors by attempting to fix common pattern issues.

        Args:
            error: ValidationErrorDetail with INVALID_PATTERN type

        Returns:
            Tuple of (corrected value or None, pattern strength score)
        """
        current_value = error.current_value.strip()

        if not current_value:
            return None, 0.0

        # Try date pattern corrections
        date_correction, date_strength = self._try_date_correction_with_confidence(current_value)
        if date_correction:
            return date_correction, date_strength

        # Try numeric pattern corrections
        numeric_correction, numeric_strength = self._try_numeric_correction_with_confidence(current_value)
        if numeric_correction:
            return numeric_correction, numeric_strength

        # Try common format corrections
        format_correction, format_strength = self._try_format_correction_with_confidence(current_value)
        if format_correction:
            return format_correction, format_strength

        # Try case corrections
        case_correction, case_strength = self._try_case_correction_with_confidence(current_value)
        if case_correction:
            return case_correction, case_strength

        return None, 0.0

    def _handle_required_value_with_confidence(self, error: ValidationErrorDetail) -> Tuple[Optional[str], float]:
        """
        Handle REQUIRED_VALUE errors by suggesting default values based on column context.

        Args:
            error: ValidationErrorDetail with REQUIRED_VALUE type

        Returns:
            Tuple of (suggested default value or None, confidence strength)
        """
        # CRITICAL: If the field has valid options (enum constraints),
        # only recommend values from that list
        if error.valid_options:
            # For fields with enum constraints, recommend the first valid option as default
            # This is safer than guessing arbitrary values
            default_option = error.valid_options[0]
            logger.debug(
                f"Field '{error.column}' has enum constraints, recommending first valid option: '{default_option}'"
            )
            return default_option, 0.9  # High confidence for enum defaults

        # Only provide heuristic defaults for fields WITHOUT enum constraints
        column_name = error.column.lower()

        # Date-related fields
        if any(date_keyword in column_name for date_keyword in ["date", "time", "created", "updated", "modified"]):
            if "created" in column_name or "start" in column_name:
                return (
                    datetime.now().strftime("%Y-%m-%d"),
                    0.7,
                )  # Medium-high confidence
            elif "updated" in column_name or "modified" in column_name:
                return (
                    datetime.now().strftime("%Y-%m-%d"),
                    0.7,
                )  # Medium-high confidence
            else:
                return datetime.now().strftime("%Y-%m-%d"), 0.6  # Medium confidence

        # Status fields (only if no enum constraints)
        if "status" in column_name:
            return "active", 0.6  # Medium confidence

        # Boolean-like fields (only if no enum constraints)
        if any(bool_keyword in column_name for bool_keyword in ["active", "enabled", "valid", "confirmed"]):
            return "true", 0.6  # Medium confidence

        # Count/number fields
        if any(num_keyword in column_name for num_keyword in ["count", "number", "num", "quantity", "amount"]):
            return "0", 0.8  # High confidence for numeric defaults

        # For other fields without enum constraints, don't guess - let user decide
        logger.debug(f"No specific pattern match for field '{error.column}', no recommendation provided")
        return None, 0.0

    # Backward compatibility methods for existing tests
    async def _generate_recommendation(self, error: ValidationErrorDetail) -> Optional[str]:
        """Backward compatibility method for existing tests."""
        recommendation, _ = await self._generate_recommendation_with_confidence(error)
        return recommendation

    def _handle_invalid_pattern(self, error: ValidationErrorDetail) -> Optional[str]:
        """Backward compatibility method for existing tests."""
        recommendation, _ = self._handle_invalid_pattern_with_confidence(error)
        return recommendation

    def _handle_required_value(self, error: ValidationErrorDetail) -> Optional[str]:
        """Backward compatibility method for existing tests."""
        recommendation, _ = self._handle_required_value_with_confidence(error)
        return recommendation

    def _try_date_correction(self, value: str) -> Optional[str]:
        """Backward compatibility method for existing tests."""
        recommendation, _ = self._try_date_correction_with_confidence(value)
        return recommendation

    def _try_numeric_correction(self, value: str) -> Optional[str]:
        """Backward compatibility method for existing tests."""
        recommendation, _ = self._try_numeric_correction_with_confidence(value)
        return recommendation

    def _try_format_correction(self, value: str) -> Optional[str]:
        """Backward compatibility method for existing tests."""
        recommendation, _ = self._try_format_correction_with_confidence(value)
        return recommendation

    def _try_case_correction(self, value: str) -> Optional[str]:
        """Backward compatibility method for existing tests."""
        recommendation, _ = self._try_case_correction_with_confidence(value)
        return recommendation

    def _try_date_correction_with_confidence(self, value: str) -> Tuple[Optional[str], float]:
        """
        Attempt to correct common date format issues.

        Args:
            value: Input value to correct

        Returns:
            Tuple of (corrected date string or None, confidence score)
        """
        # Remove extra whitespace and common separators
        cleaned = re.sub(r"\s+", " ", value.strip())

        # Try to match and convert common date patterns
        for i, pattern_info in enumerate(self._date_patterns):
            match = pattern_info["regex"].match(cleaned)
            if match:
                try:
                    result = pattern_info["converter"](match)
                    # Validate the date by attempting to parse it
                    from datetime import datetime

                    datetime.strptime(result, "%Y-%m-%d")

                    # Higher confidence for more specific patterns (earlier in list)
                    confidence = 0.9 - (i * 0.1)  # 0.9, 0.8, 0.7, etc.
                    return result, max(0.5, confidence)
                except (ValueError, IndexError):
                    continue

        return None, 0.0

    def _try_numeric_correction_with_confidence(self, value: str) -> Tuple[Optional[str], float]:
        """
        Attempt to correct common numeric format issues.

        Args:
            value: Input value to correct

        Returns:
            Tuple of (corrected numeric string or None, confidence score)
        """
        # Only process values that look like they could be numbers
        # Must contain at least one digit and mostly numeric characters
        if not re.search(r"\d", value):
            return None, 0.0

        # Check if the value looks like it could be a number (more than 50% numeric chars)
        numeric_chars = len(re.findall(r"[\d\.\-\$,\(\)]", value))
        numeric_ratio = numeric_chars / len(value) if len(value) > 0 else 0

        if numeric_ratio <= 0.5:
            return None, 0.0

        # Remove common non-numeric characters but preserve decimal points and negative signs
        cleaned = re.sub(r"[^\d\.\-]", "", value)

        if not cleaned:
            return None, 0.0

        # Try to parse as number
        try:
            # Handle multiple decimal points
            if cleaned.count(".") > 1:
                # Keep only the first decimal point
                parts = cleaned.split(".")
                cleaned = parts[0] + "." + "".join(parts[1:])

            # Validate the number
            float(cleaned)

            # Confidence based on how "numeric" the original value looked
            confidence = min(0.9, numeric_ratio + 0.2)  # Cap at 0.9, boost by 0.2
            return cleaned, confidence
        except ValueError:
            return None, 0.0

    def _try_format_correction_with_confidence(self, value: str) -> Tuple[Optional[str], float]:
        """
        Attempt to correct common formatting issues.

        Args:
            value: Input value to correct

        Returns:
            Tuple of (corrected format string or None, confidence score)
        """
        # Email format correction
        if "@" in value and "." in value:
            # Basic email cleanup
            cleaned = re.sub(r"\s+", "", value.lower())
            if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", cleaned):
                return cleaned, 0.8  # High confidence for valid email patterns

        # Phone number format correction
        digits_only = re.sub(r"[^\d]", "", value)
        if len(digits_only) == 10:
            return (
                f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}",
                0.9,
            )  # Very high confidence
        elif len(digits_only) == 11 and digits_only.startswith("1"):
            return (
                f"1-({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}",
                0.9,
            )  # Very high confidence

        # URL format correction
        if any(protocol in value.lower() for protocol in ["http", "www", ".com", ".org", ".net"]):
            cleaned = value.strip().lower()
            if not cleaned.startswith(("http://", "https://")):
                if cleaned.startswith("www."):
                    cleaned = "https://" + cleaned
                elif "." in cleaned:
                    cleaned = "https://www." + cleaned
            return cleaned, 0.7  # Medium-high confidence for URL corrections

        return None, 0.0

    def _try_case_correction_with_confidence(self, value: str) -> Tuple[Optional[str], float]:
        """
        Attempt to correct common case issues.

        Args:
            value: Input value to correct

        Returns:
            Tuple of (corrected case string or None, confidence score)
        """
        # If value is all uppercase or all lowercase, try title case for names
        if value.isupper() or value.islower():
            # Check if it looks like a name (contains letters and possibly spaces/hyphens)
            if re.match(r"^[a-zA-Z\s\-\'\.]+$", value):
                return value.title(), 0.6  # Medium confidence for case corrections

        return None, 0.0

    def _initialize_common_patterns(self) -> Dict[str, Any]:
        """Initialize common pattern matching rules."""
        return {
            "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
            "phone": re.compile(r"^\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$"),
            "url": re.compile(r"^https?://[^\s/$.?#].[^\s]*$"),
            "uuid": re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                re.IGNORECASE,
            ),
        }

    def _initialize_date_patterns(self) -> List[Dict[str, Any]]:
        """Initialize date pattern matching and conversion rules."""
        return [
            {
                "regex": re.compile(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$"),
                "converter": lambda m: f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}",
            },
            {
                "regex": re.compile(r"^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$"),
                "converter": lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}",
            },
            {
                "regex": re.compile(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2})$"),
                "converter": lambda m: f"20{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}",
            },
        ]

    def _initialize_numeric_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize numeric pattern matching rules."""
        return {
            "integer": re.compile(r"^-?\d+$"),
            "decimal": re.compile(r"^-?\d+\.\d+$"),
            "percentage": re.compile(r"^-?\d+(\.\d+)?%$"),
            "currency": re.compile(r"^\$?-?\d+(\.\d{2})?$"),
        }

    async def _save_state_to_session(self, checkpoint: str, state: ProcessorState) -> None:
        """
        Save processing state to session manager.

        Args:
            checkpoint: Checkpoint name for this state save
            state: ProcessorState to save
        """
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Create serializable state data
                state_data = {
                    "job_id": state.job_id,
                    "current_stage": state.current_stage,
                    "program_id": state.program_id,
                    "core_id": state.core_id,
                    "processing_start_time": (
                        state.processing_start_time.isoformat() if state.processing_start_time else None
                    ),
                    "validation_error_count": (
                        len(state.combined_results.validation_results.validation_results)
                        if state.has_validation_results()
                        else None
                    ),
                    "pattern_predictions_count": (
                        len(
                            [
                                e
                                for e in state.combined_results.validation_results.validation_results
                                if e.error_type
                                in [
                                    ValidationErrorType.INVALID_PATTERN,
                                    ValidationErrorType.REQUIRED_VALUE,
                                ]
                                and e.recommended_value
                            ]
                        )
                        if state.has_validation_results()
                        else 0
                    ),
                }

                # Check if session manager supports the expected methods
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data(f"pattern_prediction_{checkpoint}", state_data)
                    logger.debug(f"Saved state to session at checkpoint: {checkpoint}")
                else:
                    logger.debug(
                        f"Session manager {type(self.session_manager).__name__} does not support generic data saving - skipping checkpoint save"
                    )
        except Exception as e:
            logger.warning(f"Failed to save state to session at {checkpoint}: {e}")

    async def _save_progress_to_session(self, processed: int, total: int) -> None:
        """
        Save processing progress to session manager.

        Args:
            processed: Number of errors processed so far
            total: Total number of errors to process
        """
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                progress_data = {
                    "processed": processed,
                    "total": total,
                    "percentage": (processed / total) * 100 if total > 0 else 0,
                    "timestamp": datetime.now().isoformat(),
                }

                # Check if session manager supports the expected methods
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data("pattern_prediction_progress", progress_data)
                    logger.debug(f"Saved progress to session: {processed}/{total} ({progress_data['percentage']:.1f}%)")
                else:
                    logger.debug(
                        f"Session manager {type(self.session_manager).__name__} does not support generic data saving - skipping progress save"
                    )
        except Exception as e:
            logger.debug(f"Failed to save progress to session: {e}")

    async def cleanup_session_data(self) -> None:
        """
        Clean up session data for this node.
        """
        try:
            if hasattr(self, "session_manager") and self.session_manager:
                # Clean up pattern prediction specific session data
                keys_to_clean = [
                    "pattern_prediction_start",
                    "pattern_prediction_complete",
                    "pattern_prediction_skipped",
                    "pattern_prediction_progress",
                ]

                for key in keys_to_clean:
                    try:
                        await self.session_manager.delete_data(key)
                    except Exception as e:
                        logger.debug(f"Failed to clean session key {key}: {e}")

                logger.debug("Pattern prediction session data cleaned up")
        except Exception as e:
            logger.warning(f"Error during pattern prediction session cleanup: {e}")
