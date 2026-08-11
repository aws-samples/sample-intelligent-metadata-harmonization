# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Fuzzy matching node for enum value correction.

This node corrects INVALID_OPTION validation errors using fuzzy string matching
with Levenshtein distance via the rapidfuzz library.
"""

import asyncio
from typing import Any

from loguru import logger
from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import Message

from ..config import FuzzyMatchingConfig
from ..models.validation import (
    CorrectionNodeType,
    ValidationErrorDetail,
    ValidationErrorType,
)
from ..utils.fuzzy_utils import find_best_match


class FuzzyMatchingNode(MultiAgentBase):
    """
    MultiAgentBase node for fuzzy matching correction of INVALID_OPTION errors.

    This node uses Levenshtein distance to detect and correct typographical errors
    in enum values. It processes only errors without existing recommendations.
    """

    def __init__(self, config: FuzzyMatchingConfig):
        """
        Initialize the fuzzy matching node.

        Args:
            config: Configuration for fuzzy matching
        """
        super().__init__()
        self.config = config
        self._semaphore: asyncio.Semaphore = None
        self._processed_count: int = 0
        self._total_count: int = 0

        logger.info(
            f"Initialized FuzzyMatchingNode: "
            f"threshold={config.min_similarity_threshold:.2f}, "
            f"max_concurrent={config.max_concurrent_predictions}"
        )

    async def invoke_async(
        self, task: str | list, invocation_state: dict[str, Any] | None = None, **kwargs
    ) -> MultiAgentResult:
        """
        Process fuzzy matching using MultiAgentBase framework.

        Args:
            task: Task content
            invocation_state: Dictionary containing ProcessorState
            **kwargs: Additional keyword arguments

        Returns:
            MultiAgentResult with updated validation errors
        """
        # Validate invocation state
        if not invocation_state or "processor_state" not in invocation_state:
            error_msg = "ProcessorState must be provided in invocation_state"
            logger.error(error_msg)
            return MultiAgentResult(
                status=Status.FAILED,
                results={"fuzzy_matching": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        state = invocation_state["processor_state"]

        # Validate that we have validation results
        if not state.has_validation_results():
            error_msg = "ProcessorState must contain validation_results"
            logger.error(error_msg)
            return MultiAgentResult(
                status=Status.FAILED,
                results={"fuzzy_matching": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        try:
            # Filter for INVALID_OPTION errors without recommendations
            invalid_option_errors = [
                error
                for error in state.combined_results.validation_results.validation_results
                if error.error_type == ValidationErrorType.INVALID_OPTION and not error.recommended_value
            ]

            logger.info("=" * 80)
            logger.info("   STARTING FUZZY MATCHING NODE")
            logger.info(f"   Input: {len(invalid_option_errors)} unresolved INVALID_OPTION errors")
            logger.info(f"   Threshold: {self.config.min_similarity_threshold:.2f}")
            logger.info("=" * 80)

            if not invalid_option_errors:
                logger.info("No unresolved INVALID_OPTION errors for fuzzy matching")

                success_message: Message = {"content": [{"text": "No unresolved INVALID_OPTION errors to process"}]}
                agent_result = AgentResult(
                    stop_reason="end_turn",
                    message=success_message,
                    metrics=EventLoopMetrics(),
                    state={"processed": 0, "total": 0},
                )

                return MultiAgentResult(
                    status=Status.COMPLETED,
                    results={"fuzzy_matching": NodeResult(result=agent_result, status=Status.COMPLETED)},
                )

            logger.info(
                f"Processing {len(invalid_option_errors)} unresolved INVALID_OPTION errors " f"with fuzzy matching"
            )

            # Initialize semaphore for concurrency control
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_predictions)
            self._processed_count = 0
            self._total_count = len(invalid_option_errors)

            # Process errors concurrently with semaphore control
            tasks = [self._process_single_error_with_semaphore(error) for error in invalid_option_errors]

            await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful corrections
            corrections_made = sum(
                1
                for error in invalid_option_errors
                if error.recommended_value and error.correction_node == CorrectionNodeType.FUZZY_MATCHING
            )

            logger.info("=" * 80)
            logger.info("   FINISHED FUZZY MATCHING NODE")
            logger.info(f"   Output: {corrections_made}/{len(invalid_option_errors)} corrections made")
            logger.info(f"   Success Rate: {(corrections_made/len(invalid_option_errors)*100):.1f}%")
            logger.info("=" * 80)

            # Create success result
            success_message: Message = {
                "content": [
                    {
                        "text": f"Fuzzy matching completed. Made {corrections_made} corrections "
                        f"out of {len(invalid_option_errors)} errors."
                    }
                ]
            }
            agent_result = AgentResult(
                stop_reason="end_turn",
                message=success_message,
                metrics=EventLoopMetrics(),
                state={
                    "processed": self._processed_count,
                    "corrections": corrections_made,
                    "total": len(invalid_option_errors),
                },
            )

            return MultiAgentResult(
                status=Status.COMPLETED,
                results={"fuzzy_matching": NodeResult(result=agent_result, status=Status.COMPLETED)},
            )

        except Exception as e:
            error_msg = f"Fuzzy matching failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return MultiAgentResult(
                status=Status.FAILED,
                results={"fuzzy_matching": NodeResult(result=e, status=Status.FAILED)},
            )

    async def _process_single_error_with_semaphore(self, error: ValidationErrorDetail) -> None:
        """
        Process a single error with semaphore control.

        Args:
            error: ValidationErrorDetail to process
        """
        async with self._semaphore:
            await self._process_single_error(error)
            self._processed_count += 1

    async def _process_single_error(self, error: ValidationErrorDetail) -> None:
        """
        Process a single INVALID_OPTION error with fuzzy matching.

        Args:
            error: ValidationErrorDetail to process (modified in place)
        """
        try:
            # Skip if already has a recommendation
            if error.recommended_value:
                return

            # Skip if no valid options
            if not error.valid_options:
                logger.debug(f"No valid options for error at row {error.row}, " f"column {error.column}")
                return

            # Find best fuzzy match
            result = find_best_match(
                query=error.current_value,
                candidates=error.valid_options,
                min_threshold=self.config.min_similarity_threshold,
            )

            if result:
                best_match, similarity = result

                # Use raw similarity score for granular confidence
                # Only LLM node should use enum-based bucketing
                confidence_level = "High" if similarity >= 0.9 else "Medium" if similarity >= 0.7 else "Low"

                # Set recommendation with node attribution
                error.recommended_value = best_match
                error.correction_node = CorrectionNodeType.FUZZY_MATCHING
                error.confidence_score = similarity  # Use raw similarity, not bucketed
                error.confidence_level = confidence_level

                logger.debug(
                    f"Fuzzy match for '{error.current_value}': '{best_match}' "
                    f"(similarity: {similarity:.3f}, confidence: {confidence_level})"
                )

        except Exception as e:
            logger.warning(f"Failed to process error for row {error.row}, " f"column {error.column}: {e}")
