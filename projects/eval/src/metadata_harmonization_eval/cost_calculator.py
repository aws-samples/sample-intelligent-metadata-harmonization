# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Cost calculation module for AWS Bedrock API usage.

This module provides utilities for calculating costs from token usage
based on configurable pricing for LLM and embedding models.
"""

from typing import Dict, Tuple

from loguru import logger

from .models import BedrockPricingConfig


class CostCalculator:
    """
    Calculate AWS Bedrock costs from token usage.

    This class handles cost calculations for both LLM (Large Language Model)
    and embedding model API calls, using configurable pricing information.

    Attributes:
        pricing: BedrockPricingConfig instance with model pricing information

    Examples:
        >>> pricing = BedrockPricingConfig()
        >>> calculator = CostCalculator(pricing)
        >>> input_cost, output_cost, total = calculator.calculate_llm_cost(
        ...     "amazon.nova-pro-v1:0", 1000, 500
        ... )
        >>> print(f"Total LLM cost: ${total:.4f}")
    """

    def __init__(self, pricing_config: BedrockPricingConfig):
        """
        Initialize the cost calculator with pricing configuration.

        Args:
            pricing_config: BedrockPricingConfig instance with model pricing
        """
        self.pricing = pricing_config

    def calculate_llm_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> Tuple[float, float, float]:
        """
        Calculate LLM cost based on input and output tokens.

        Calculates costs separately for input and output tokens, as they
        typically have different pricing. If the model ID is not found in
        the pricing configuration, logs a warning and returns zero costs.

        Args:
            model_id: Bedrock model identifier (e.g., "amazon.nova-pro-v1:0")
            input_tokens: Number of input tokens (prompt)
            output_tokens: Number of output tokens (response)

        Returns:
            Tuple of (input_cost, output_cost, total_cost) in USD

        Examples:
            >>> calculator = CostCalculator(BedrockPricingConfig())
            >>> input_cost, output_cost, total = calculator.calculate_llm_cost(
            ...     "amazon.nova-pro-v1:0", 50000, 15000
            ... )
            >>> print(f"Input: ${input_cost:.4f}, Output: ${output_cost:.4f}")
        """
        pricing = self.pricing.llm_models.get(model_id)

        if not pricing:
            logger.warning(f"No pricing configured for LLM model '{model_id}', setting cost to $0.00")
            pricing = {"input_price_per_1k": 0.0, "output_price_per_1k": 0.0}

        # Calculate costs per 1000 tokens
        input_cost = (input_tokens / 1000.0) * pricing["input_price_per_1k"]
        output_cost = (output_tokens / 1000.0) * pricing["output_price_per_1k"]
        total_cost = input_cost + output_cost

        return input_cost, output_cost, total_cost

    def calculate_embedding_cost(self, model_id: str, tokens: int) -> float:
        """
        Calculate embedding cost based on token count.

        Embedding models typically have a single price per token, unlike
        LLM models which have separate input/output pricing. If the model
        ID is not found in the pricing configuration, logs a warning and
        returns zero cost.

        Args:
            model_id: Bedrock embedding model identifier
                     (e.g., "amazon.titan-embed-text-v2:0")
            tokens: Number of tokens processed

        Returns:
            Cost in USD

        Examples:
            >>> calculator = CostCalculator(BedrockPricingConfig())
            >>> cost = calculator.calculate_embedding_cost(
            ...     "amazon.titan-embed-text-v2:0", 1170000
            ... )
            >>> print(f"Embedding cost: ${cost:.4f}")
        """
        price_per_1k = self.pricing.embedding_models.get(model_id)

        if price_per_1k is None:
            logger.warning(f"No pricing configured for embedding model '{model_id}', setting cost to $0.00")
            price_per_1k = 0.0

        # Calculate cost per 1000 tokens
        cost = (tokens / 1000.0) * price_per_1k

        return cost

    def calculate_node_costs(
        self,
        llm_input_tokens: int,
        llm_output_tokens: int,
        embedding_tokens: int,
        llm_model_id: str,
        embedding_model_id: str,
    ) -> Dict[str, float]:
        """
        Calculate costs for a single correction node.

        This method aggregates both LLM and embedding costs for a node,
        providing a complete cost breakdown.

        Args:
            llm_input_tokens: Number of LLM input tokens
            llm_output_tokens: Number of LLM output tokens
            embedding_tokens: Number of embedding tokens
            llm_model_id: Bedrock LLM model identifier
            embedding_model_id: Bedrock embedding model identifier

        Returns:
            Dictionary with cost breakdown:
                - llm_input_cost: Cost for LLM input tokens
                - llm_output_cost: Cost for LLM output tokens
                - llm_total_cost: Total LLM cost
                - embedding_cost: Cost for embedding tokens
                - total_cost: Combined LLM and embedding cost

        Examples:
            >>> calculator = CostCalculator(BedrockPricingConfig())
            >>> costs = calculator.calculate_node_costs(
            ...     llm_input_tokens=50000,
            ...     llm_output_tokens=15000,
            ...     embedding_tokens=1170000,
            ...     llm_model_id="amazon.nova-pro-v1:0",
            ...     embedding_model_id="amazon.titan-embed-text-v2:0"
            ... )
            >>> print(f"Total node cost: ${costs['total_cost']:.4f}")
        """
        # Calculate LLM costs
        llm_input_cost, llm_output_cost, llm_total = self.calculate_llm_cost(
            llm_model_id, llm_input_tokens, llm_output_tokens
        )

        # Calculate embedding costs
        embedding_cost = self.calculate_embedding_cost(embedding_model_id, embedding_tokens)

        return {
            "llm_input_cost": llm_input_cost,
            "llm_output_cost": llm_output_cost,
            "llm_total_cost": llm_total,
            "embedding_cost": embedding_cost,
            "total_cost": llm_total + embedding_cost,
        }
