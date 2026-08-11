# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
LLM resolution node for enum value correction.

This node corrects INVALID_OPTION validation errors using LLM-based reasoning
via AWS Strands Agent framework with structured output.
"""

import asyncio
import logging
from typing import Any, Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel, Field
from strands import Agent
from strands.agent.agent_result import AgentResult
from strands.models.bedrock import BedrockModel
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import Message

from ..config import LLMResolutionConfig
from ..models.state import NodeTokenUsage, ProcessorState
from ..models.validation import (
    CorrectionNodeType,
    ValidationErrorDetail,
    ValidationErrorType,
)
from ..utils.confidence_utils import calculate_prediction_confidence
from ..utils.prompt_utils import FENCING_INSTRUCTION, fence

# Suppress verbose Strands logging at module level
logging.getLogger("strands").setLevel(logging.WARNING)


class EnumCorrectionResponse(BaseModel):
    """Structured output model for a single enum correction."""

    error_index: int = Field(description="Index of the error in the batch (0-based)")
    recommended_value: str = Field(
        description="MUST be exactly one of the provided valid options, no other values allowed"
    )
    confidence_level: Literal["low", "medium", "high"] = Field(
        description="Confidence level: must be exactly 'low', 'medium', or 'high'"
    )
    reasoning: str = Field(description="Brief explanation for the recommendation")


class BatchEnumCorrectionResponse(BaseModel):
    """Structured output model for batch enum correction response."""

    corrections: List[EnumCorrectionResponse] = Field(
        description="List of corrections, one for each error in the batch"
    )


class LLMResolutionNode(MultiAgentBase):
    """
    MultiAgentBase node for LLM-based resolution of INVALID_OPTION errors.

    This node uses AWS Strands Agent with structured output to resolve complex
    or ambiguous enum value corrections that simpler methods couldn't handle.
    """

    def __init__(self, config: LLMResolutionConfig):
        """
        Initialize the LLM resolution node.

        Args:
            config: Configuration for LLM resolution
        """
        super().__init__()
        self.config = config
        self._agent: Optional[Agent] = None
        self._semaphore: asyncio.Semaphore = None
        self._processed_count: int = 0
        self._total_count: int = 0

        logger.info(
            f"Initialized LLMResolutionNode: "
            f"model={config.model_id}, "
            f"min_confidence={config.min_confidence_level}, "
            f"max_concurrent={config.max_concurrent_predictions}"
        )

    def _create_fresh_agent(self) -> Agent:
        """
        Create a fresh Strands Agent instance with no history.

        This ensures each batch starts with a clean slate and avoids
        context accumulation that can cause token limit issues.

        Returns:
            New Agent instance
        """
        # Create a Bedrock model instance
        bedrock_model = BedrockModel(
            model_id=self.config.model_id,
            region_name=self.config.aws_region,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # Create an agent with null callback handler to suppress verbose output
        # Setting callback_handler=None uses null_callback_handler instead of PrintingCallbackHandler
        return Agent(
            model=bedrock_model,
            callback_handler=None,  # Suppress <thinking> tags and tool output
        )

    async def invoke_async(
        self, task: str | list, invocation_state: dict[str, Any] | None = None, **kwargs
    ) -> MultiAgentResult:
        """
        Process LLM resolution using MultiAgentBase framework.

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
                results={"llm_resolution": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        state = invocation_state["processor_state"]

        # Validate that we have validation results
        if not state.has_validation_results():
            error_msg = "ProcessorState must contain validation_results"
            logger.error(error_msg)
            return MultiAgentResult(
                status=Status.FAILED,
                results={"llm_resolution": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        try:
            # Filter for INVALID_OPTION errors without recommendations
            invalid_option_errors = [
                error
                for error in state.combined_results.validation_results.validation_results
                if error.error_type == ValidationErrorType.INVALID_OPTION and not error.recommended_value
            ]

            logger.info("=" * 80)
            logger.info("   STARTING LLM RESOLUTION NODE")
            logger.info(f"   Input: {len(invalid_option_errors)} unresolved INVALID_OPTION errors")
            logger.info(f"   Min Confidence: {self.config.min_confidence_level}")
            logger.info("=" * 80)

            if not invalid_option_errors:
                logger.info("No unresolved INVALID_OPTION errors for LLM resolution")

                success_message: Message = {"content": [{"text": "No unresolved INVALID_OPTION errors to process"}]}
                agent_result = AgentResult(
                    stop_reason="end_turn",
                    message=success_message,
                    metrics=EventLoopMetrics(),
                    state={"processed": 0, "total": 0},
                )

                return MultiAgentResult(
                    status=Status.COMPLETED,
                    results={"llm_resolution": NodeResult(result=agent_result, status=Status.COMPLETED)},
                )

            logger.info(
                f"Processing {len(invalid_option_errors)} unresolved INVALID_OPTION errors "
                f"with LLM resolution (batch processing)"
            )

            # Group errors into batches (prioritize same-row errors)
            # Use smaller batch size (5) to avoid token limit issues
            error_batches = self._group_errors_into_batches(invalid_option_errors, batch_size=5)
            logger.info(f"Created {len(error_batches)} batches for processing")

            # Initialize semaphore for concurrency control
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_predictions)
            self._processed_count = 0
            self._total_count = len(error_batches)

            # Process batches concurrently with semaphore control
            tasks = [self._process_batch_with_semaphore(batch, state) for batch in error_batches]

            await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful corrections
            corrections_made = sum(
                1
                for error in invalid_option_errors
                if error.recommended_value and error.correction_node == CorrectionNodeType.LLM_RESOLUTION
            )

            logger.info("=" * 80)
            logger.info("   FINISHED LLM RESOLUTION NODE")
            logger.info(f"   Output: {corrections_made}/{len(invalid_option_errors)} corrections made")
            logger.info(f"   Success Rate: {(corrections_made/len(invalid_option_errors)*100):.1f}%")
            logger.info("=" * 80)

            # Create success result
            success_message: Message = {
                "content": [
                    {
                        "text": f"LLM resolution completed. Made {corrections_made} corrections "
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
                results={"llm_resolution": NodeResult(result=agent_result, status=Status.COMPLETED)},
            )

        except Exception as e:
            error_msg = f"LLM resolution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return MultiAgentResult(
                status=Status.FAILED,
                results={"llm_resolution": NodeResult(result=e, status=Status.FAILED)},
            )

    def _group_errors_into_batches(
        self, errors: List[ValidationErrorDetail], batch_size: int = 10
    ) -> List[List[ValidationErrorDetail]]:
        """
        Group errors into batches, prioritizing same-row errors.

        Strategy:
        1. Group errors by row number
        2. Create batches from same-row groups
        3. Fill remaining slots with errors from different rows

        Args:
            errors: List of validation errors to batch
            batch_size: Maximum errors per batch

        Returns:
            List of error batches
        """
        from collections import defaultdict

        # Group errors by row
        errors_by_row: Dict[int, List[ValidationErrorDetail]] = defaultdict(list)
        for error in errors:
            errors_by_row[error.row].append(error)

        batches = []
        current_batch = []

        # First, create batches from same-row groups
        for row, row_errors in sorted(errors_by_row.items()):
            for error in row_errors:
                current_batch.append(error)

                # If batch is full, start new one
                if len(current_batch) >= batch_size:
                    batches.append(current_batch)
                    current_batch = []

        # Add any remaining errors
        if current_batch:
            batches.append(current_batch)

        logger.debug(f"Grouped {len(errors)} errors into {len(batches)} batches")
        return batches

    async def _process_batch_with_semaphore(self, batch: List[ValidationErrorDetail], state: ProcessorState) -> None:
        """
        Process a batch of errors with semaphore control.

        Args:
            batch: List of errors to process
            state: ProcessorState for row context
        """
        async with self._semaphore:
            await self._process_batch(batch, state)
            self._processed_count += 1

            # Log progress every 5 batches
            if self._processed_count % 5 == 0 or self._processed_count == self._total_count:
                # Count corrections made so far
                corrections_so_far = sum(
                    1
                    for error in state.combined_results.validation_results.validation_results
                    if error.correction_node == CorrectionNodeType.LLM_RESOLUTION
                )

                progress_pct = (self._processed_count / self._total_count * 100) if self._total_count > 0 else 0

                logger.info(
                    f"LLM Resolution Progress: {self._processed_count}/{self._total_count} batches "
                    f"({progress_pct:.0f}%) | {corrections_so_far} corrections made"
                )

    async def _process_batch(self, batch: List[ValidationErrorDetail], state: ProcessorState) -> None:
        """
        Process a batch of errors with LLM resolution.

        Args:
            batch: List of errors to process (modified in place)
            state: ProcessorState for accessing row context
        """
        try:
            # Skip errors that already have recommendations
            unprocessed_errors = [e for e in batch if not e.recommended_value]
            if not unprocessed_errors:
                return

            # Build batch prompt
            prompt = self._build_batch_prompt(unprocessed_errors, state)

            # Log the first batch prompt for debugging
            if self._processed_count == 0:
                logger.info(f"Sample batch prompt (first 1500 chars):\n{prompt[:1500]}...")

            # Call LLM with batch structured output
            batch_response = await self._call_batch_llm_with_retries(prompt, len(unprocessed_errors), state)

            if not batch_response or not batch_response.corrections:
                logger.warning(f"No batch response for {len(unprocessed_errors)} errors")
                return

            # Apply corrections
            threshold = self.config.get_threshold()
            corrections_applied = 0

            for correction in batch_response.corrections:
                # Validate error_index
                if correction.error_index < 0 or correction.error_index >= len(unprocessed_errors):
                    logger.warning(f"Invalid error_index {correction.error_index} in batch response")
                    continue

                error = unprocessed_errors[correction.error_index]

                # Validate recommendation is in valid options
                if correction.recommended_value not in error.valid_options:
                    logger.warning(
                        f"LLM recommended invalid value '{correction.recommended_value}' "
                        f"for column {error.column}. Valid options: {error.valid_options}"
                    )
                    continue

                # Check confidence threshold
                confidence_level_score = self.config._confidence_level_thresholds.get(
                    correction.confidence_level.lower(), 0.5
                )

                if confidence_level_score >= threshold:
                    # Calculate confidence score
                    confidence_score, confidence_level = calculate_prediction_confidence(
                        error.error_type,
                        confidence_level_score,
                        self.config.__dict__.get("_confidence_config"),
                    )

                    # Set recommendation with node attribution
                    error.recommended_value = correction.recommended_value
                    error.correction_node = CorrectionNodeType.LLM_RESOLUTION
                    error.confidence_score = confidence_score
                    error.confidence_level = confidence_level
                    corrections_applied += 1

                    logger.debug(
                        f"Batch LLM resolution for row {error.row}, '{error.column}': "
                        f"'{correction.recommended_value}' (confidence: {confidence_level})"
                    )
                else:
                    logger.debug(
                        f"LLM confidence {correction.confidence_level} ({confidence_level_score:.2f}) "
                        f"below threshold {threshold:.2f} for row {error.row}, column {error.column}"
                    )

            logger.debug(f"Batch processing: Applied {corrections_applied}/{len(unprocessed_errors)} corrections")

        except Exception as e:
            logger.warning(f"Failed to process batch of {len(batch)} errors: {e}")

    def _build_batch_prompt(self, errors: List[ValidationErrorDetail], state: ProcessorState) -> str:
        """
        Build batch prompt for multiple errors.

        Args:
            errors: List of errors to include in batch
            state: ProcessorState for row context

        Returns:
            Formatted batch prompt string
        """
        prompt_parts = [
            "You are helping correct multiple invalid enum values in a metadata dataset.",
            "For each error below, select the most appropriate valid option.",
            f"{FENCING_INSTRUCTION}\n",
        ]

        for idx, error in enumerate(errors):
            # Get row context
            row_idx = error.row - 1
            if row_idx < 0 or row_idx >= len(state.aligned_df):
                continue

            row_data = state.aligned_df.iloc[row_idx].to_dict()

            # Format valid options
            options_str = ", ".join(f'"{opt}"' for opt in error.valid_options)

            # Format row context (exclude the error column). Column names and cell
            # values come from the user's CSV, so both are fenced as untrusted data.
            context_items = [
                f"    {fence('field', k)}: {fence('value', v)}"
                for k, v in row_data.items()
                if k != error.column and v is not None
            ]
            context_str = "\n".join(context_items[:5])  # Limit to 5 fields per error

            prompt_parts.append(
                f"""Error {idx}:
  - Row: {error.row}
  - Column: {fence('column', error.column)}
  - Invalid value: {fence('invalid_value', error.current_value)}
  - Valid options: [{options_str}]
  - Row context:
{context_str}
"""
            )

        prompt_parts.append(
            """
Task: For EACH error above, you must provide a correction by selecting ONLY from that specific error's valid options list.

CRITICAL RULES:
1. Each error has its OWN list of valid options - they are NOT interchangeable
2. For error N, you MUST select recommended_value from ONLY the valid options listed under "Error N"
3. DO NOT use values from one error's valid options for a different error
4. DO NOT use the current invalid value shown
5. You MUST choose exactly ONE value from that error's specific valid options list

For each error provide:
- error_index: The error number (0-based, e.g., 0, 1, 2, 3...)
- recommended_value: EXACTLY one value from THAT ERROR'S valid options list (not from any other error's list)
- confidence_level: Your confidence ('low', 'medium', or 'high')
- reasoning: Brief explanation for why you selected this specific valid option from that error's list

EXAMPLE:
If Error 0 has valid options ["A", "B"] and Error 1 has valid options ["X", "Y", "Z"]:
- For Error 0, you can ONLY choose "A" or "B" (NOT "X", "Y", or "Z")
- For Error 1, you can ONLY choose "X", "Y", or "Z" (NOT "A" or "B")

Consider semantic similarity between the invalid value and the valid options when making your choice."""
        )

        return "\n".join(prompt_parts)

    def _track_token_usage(self, result: AgentResult, state: ProcessorState) -> None:
        """
        Extract and track token usage from Strands Agent result.

        Args:
            result: AgentResult from Strands Agent call
            state: ProcessorState to accumulate token usage
        """
        try:
            # Get or create token usage entry for this node
            node_name = "llm_resolution"
            if node_name not in state.token_usage:
                state.token_usage[node_name] = NodeTokenUsage(node_name=node_name, llm_model_id=self.config.model_id)

            node_usage = state.token_usage[node_name]

            # Extract token usage from agent result metrics
            if hasattr(result, "metrics") and hasattr(result.metrics, "accumulated_usage"):
                accumulated_usage = result.metrics.accumulated_usage

                # Extract input and output tokens from accumulated_usage dictionary
                input_tokens = accumulated_usage.get("inputTokens", 0)
                output_tokens = accumulated_usage.get("outputTokens", 0)

                # Accumulate token counts
                node_usage.llm_calls += 1
                node_usage.llm_input_tokens += input_tokens
                node_usage.llm_output_tokens += output_tokens

                logger.debug(
                    f"Token usage tracked: +{input_tokens} input, +{output_tokens} output "
                    f"(total: {node_usage.llm_input_tokens} input, {node_usage.llm_output_tokens} output, "
                    f"{node_usage.llm_calls} calls)"
                )
            else:
                logger.warning("Agent result does not contain token usage metrics")

        except Exception as e:
            logger.warning(f"Failed to track token usage: {e}")

    async def _call_batch_llm_with_retries(
        self, prompt: str, expected_corrections: int, state: ProcessorState
    ) -> Optional[BatchEnumCorrectionResponse]:
        """
        Call LLM with batch structured output and retry logic.
        Creates a fresh agent for each batch to avoid message history accumulation.

        Args:
            prompt: Batch prompt to send to LLM
            expected_corrections: Expected number of corrections
            state: ProcessorState for tracking token usage

        Returns:
            BatchEnumCorrectionResponse or None if failed
        """
        for attempt in range(self.config.max_retries):
            try:
                # Create fresh agent with no history for this batch
                agent = self._create_fresh_agent()

                # Call Strands Agent with batch structured output
                result = agent(prompt, structured_output_model=BatchEnumCorrectionResponse)

                # Extract token usage from agent result
                self._track_token_usage(result, state)

                # Access the structured output
                # Check if structured_output was populated
                if not hasattr(result, "structured_output") or result.structured_output is None:
                    logger.warning("LLM result did not contain structured_output")
                    return None

                response: BatchEnumCorrectionResponse = result.structured_output

                if response and response.corrections:
                    if len(response.corrections) != expected_corrections:
                        logger.warning(f"Expected {expected_corrections} corrections, got {len(response.corrections)}")
                    return response

            except Exception as e:
                logger.warning(f"Batch LLM call attempt {attempt + 1}/{self.config.max_retries} " f"failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        return None

    async def _process_single_error(self, error: ValidationErrorDetail, state: ProcessorState) -> None:
        """
        Process a single INVALID_OPTION error with LLM resolution.

        Args:
            error: ValidationErrorDetail to process (modified in place)
            state: ProcessorState for accessing row context
        """
        try:
            # Skip if already has a recommendation
            if error.recommended_value:
                return

            # Skip if no valid options
            if not error.valid_options:
                logger.debug(f"No valid options for error at row {error.row}, " f"column {error.column}")
                return

            # Get row context
            row_idx = error.row - 1
            if row_idx < 0 or row_idx >= len(state.aligned_df):
                logger.warning(f"Invalid row index {row_idx}")
                return

            row_data = state.aligned_df.iloc[row_idx].to_dict()

            # Build prompt
            prompt = self._build_prompt(
                invalid_value=error.current_value,
                valid_options=error.valid_options,
                column_name=error.column,
                row_context=row_data,
            )

            # Call LLM with retries using Strands structured output
            response = await self._call_llm_with_retries(prompt, state)

            if response:
                # Validate recommendation
                if response.recommended_value in error.valid_options:
                    # Map confidence level to threshold
                    threshold = self.config.get_threshold()
                    confidence_level_score = self.config._confidence_level_thresholds.get(
                        response.confidence_level.lower(), 0.5
                    )

                    # Check if meets minimum confidence
                    if confidence_level_score >= threshold:
                        # Calculate confidence score
                        confidence_score, confidence_level = calculate_prediction_confidence(
                            error.error_type,
                            confidence_level_score,
                            self.config.__dict__.get("_confidence_config"),
                        )

                        # Set recommendation with node attribution
                        error.recommended_value = response.recommended_value
                        error.correction_node = CorrectionNodeType.LLM_RESOLUTION
                        error.confidence_score = confidence_score
                        error.confidence_level = confidence_level

                        logger.debug(
                            f"LLM resolution for row {error.row}, '{error.column}': "
                            f"'{response.recommended_value}' (confidence: {confidence_level}, "
                            f"reasoning: {response.reasoning[:50]}...)"
                        )
                    else:
                        logger.debug(
                            f"LLM confidence {response.confidence_level} ({confidence_level_score:.2f}) "
                            f"below threshold {threshold:.2f}"
                        )
                else:
                    logger.warning(
                        f"LLM recommended invalid value '{response.recommended_value}' " f"for column {error.column}"
                    )

        except Exception as e:
            logger.warning(f"Failed to process error for row {error.row}, " f"column {error.column}: {e}")

    def _build_prompt(
        self,
        invalid_value: str,
        valid_options: List[str],
        column_name: str,
        row_context: Dict[str, Any],
    ) -> str:
        """
        Build structured prompt for LLM.

        Args:
            invalid_value: Invalid enum value
            valid_options: List of valid options
            column_name: Column name
            row_context: Dictionary of row data

        Returns:
            Formatted prompt string
        """
        # Format valid options
        options_str = ", ".join(f'"{opt}"' for opt in valid_options)

        # Format row context (exclude the error column). Column names and cell values
        # come from the user's CSV, so both are fenced as untrusted data.
        context_items = [
            f"  {fence('field', k)}: {fence('value', v)}"
            for k, v in row_context.items()
            if k != column_name and v is not None
        ]
        context_str = "\n".join(context_items[:10])  # Limit to 10 fields

        prompt = f"""You are helping correct invalid enum values in a metadata dataset.
{FENCING_INSTRUCTION}

Current invalid value: {fence('invalid_value', invalid_value)}
Column name: {fence('column', column_name)}
Valid options: {options_str}

Row context:
{context_str}

Task: Select the most appropriate valid option based on the context and explain your confidence level.

Consider:
- Semantic similarity between the invalid value and valid options
- Contextual clues from other fields in the row
- Common patterns or conventions in the data

Provide:
- recommended_value: The selected option from the valid options list
- confidence_level: Your confidence ('low', 'medium', or 'high')
- reasoning: Brief explanation for your choice"""

        return prompt

    async def _call_llm_with_retries(self, prompt: str, state: ProcessorState) -> Optional[EnumCorrectionResponse]:
        """
        Call LLM with retry logic using Strands structured output.

        Args:
            prompt: Prompt to send to LLM
            state: ProcessorState for tracking token usage

        Returns:
            EnumCorrectionResponse or None if failed
        """
        for attempt in range(self.config.max_retries):
            try:
                # Call Strands Agent with structured output
                result = self._agent(prompt, structured_output_model=EnumCorrectionResponse)

                # Extract token usage from agent result
                self._track_token_usage(result, state)

                # Access the structured output
                # Check if structured_output was populated
                if not hasattr(result, "structured_output") or result.structured_output is None:
                    logger.warning("LLM result did not contain structured_output")
                    continue

                response: EnumCorrectionResponse = result.structured_output

                if response:
                    return response

            except Exception as e:
                logger.warning(f"LLM call attempt {attempt + 1}/{self.config.max_retries} " f"failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        return None
