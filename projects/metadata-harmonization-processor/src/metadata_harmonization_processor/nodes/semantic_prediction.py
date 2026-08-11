# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Semantic search prediction node for metadata harmonization processing.

This module implements the SemanticSearchPredictionNode class that handles
INVALID_OPTION validation errors by using AI-powered semantic search with
embeddings to find the most similar valid options. It inherits from
MultiAgentBase for AWS Strands integration with proper session management.
"""

import asyncio
import hashlib
import json
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import boto3
import numpy as np
import redis.asyncio as redis
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import ContentBlock, Message

from ..config import ConfidenceConfig, ProcessorConfig
from ..models.state import NodeTokenUsage, ProcessorState
from ..models.validation import (
    CorrectionNodeType,
    ValidationErrorDetail,
    ValidationErrorType,
)


class SemanticSearchPredictionNode(MultiAgentBase):
    """
    MultiAgentBase node for semantic search predictions on INVALID_OPTION errors.

    This node processes validation errors of type INVALID_OPTION by generating
    embeddings for invalid values and finding the most similar valid options
    using cosine similarity. It implements a hierarchical caching strategy:
    Redis → In-memory → No caching. It inherits from MultiAgentBase
    for AWS Strands session management and standardized result handling.
    """

    def __init__(self, config: ProcessorConfig):
        """
        Initialize the semantic search prediction node.

        Args:
            config: Processor configuration containing AI and caching settings
        """
        self.config = config
        self._redis_client: Optional[redis.Redis] = None
        self._memory_cache: Optional[OrderedDict[str, List[float]]] = None
        self._bedrock_client: Optional[Any] = None
        self._sagemaker_client: Optional[Any] = None
        self._cache_lock: asyncio.Lock = asyncio.Lock()

        # Initialize semaphore for concurrency control
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._processed_count: int = 0
        self._total_count: int = 0
        self._progress_lock: asyncio.Lock = asyncio.Lock()

        # Store state for token usage tracking
        self._current_state: Optional[ProcessorState] = None

        # Cache metrics tracking
        self._cache_stats = {
            "redis_hits": 0,
            "redis_misses": 0,
            "memory_hits": 0,
            "memory_misses": 0,
            "cache_misses": 0,  # Complete cache misses requiring new embedding generation
            "embeddings_generated": 0,
        }

        # Initialize confidence configuration
        self._confidence_config = ConfidenceConfig()

        # Initialize in-memory cache if enabled and Redis is disabled
        if not config.enable_redis_cache and config.enable_memory_cache:
            self._memory_cache = OrderedDict()

        logger.info(f"Initialized SemanticSearchPredictionNode with provider: {config.embedding_provider}")
        logger.info(f"Cache configuration - Redis: {config.enable_redis_cache}, Memory: {config.enable_memory_cache}")
        logger.info(f"Memory cache size limit: {config.memory_cache_max_size} embeddings")
        logger.info(
            f"Concurrency limit: {config.semantic_prediction.max_concurrent_predictions} concurrent predictions"
        )

    async def invoke_async(
        self,
        task: str | list[ContentBlock],
        invocation_state: dict[str, Any] | None = None,
        **kwargs,
    ) -> MultiAgentResult:
        """
        Process semantic predictions using MultiAgentBase framework.

        Args:
            task: Task content (string or ContentBlock list)
            invocation_state: Optional invocation state dictionary containing ProcessorState
            **kwargs: Additional keyword arguments (unused)

        Returns:
            MultiAgentResult with enhanced validation_results containing semantic predictions
        """
        try:
            # Get ProcessorState from invocation_state
            if not invocation_state or "processor_state" not in invocation_state:
                error_msg = "ProcessorState must be provided in invocation_state"
                logger.error(error_msg)
                return MultiAgentResult(
                    status=Status.FAILED,
                    results={"semantic_prediction": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
                )

            state = invocation_state["processor_state"]

            if not state.has_validation_results():
                error_msg = "ProcessorState must contain validation_results"
                logger.error(error_msg)
                return MultiAgentResult(
                    status=Status.FAILED,
                    results={"semantic_prediction": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
                )

            # Store state for token usage tracking
            self._current_state = state

            state.set_current_stage("semantic_prediction")

            # Get session ID for logging context
            session_id = (
                getattr(self.session_manager, "session_id", "unknown")
                if hasattr(self, "session_manager") and self.session_manager
                else "unknown"
            )

            logger.info("Starting semantic search prediction")

            # Save initial state to session
            await self._save_state_to_session("semantic_prediction_start", state)

            # Filter for INVALID_OPTION errors without recommendations
            invalid_option_errors = [
                error
                for error in state.combined_results.validation_results.validation_results
                if error.error_type == ValidationErrorType.INVALID_OPTION and not error.recommended_value
            ]

            if not invalid_option_errors:
                logger.info("No INVALID_OPTION errors found, skipping semantic prediction")
                await self._save_state_to_session("semantic_prediction_skipped", state)

                # Create success AgentResult
                success_message: Message = {
                    "content": [{"text": "No INVALID_OPTION errors found, skipping semantic prediction"}]
                }
                agent_result = AgentResult(
                    stop_reason="end_turn",
                    message=success_message,
                    metrics=EventLoopMetrics(),
                    state={"processed_errors": 0, "total_errors": 0},
                )

                return MultiAgentResult(
                    status=Status.COMPLETED,
                    results={"semantic_prediction": NodeResult(result=agent_result, status=Status.COMPLETED)},
                )

            # Initialize semaphore for concurrency control
            max_concurrent = self.config.semantic_prediction.max_concurrent_predictions
            self._semaphore = asyncio.Semaphore(max_concurrent)
            self._processed_count = 0
            self._total_count = len(invalid_option_errors)

            logger.info("=" * 80)
            logger.info("   STARTING SEMANTIC PREDICTION NODE")
            logger.info(f"   Input: {len(invalid_option_errors)} unresolved INVALID_OPTION errors")
            logger.info(f"   Threshold: {self.config.cosine_similarity_threshold:.2f}")
            logger.info("=" * 80)

            logger.info(
                f"Processing {len(invalid_option_errors)} unresolved INVALID_OPTION errors " f"with semantic prediction"
            )

            # Create all tasks at once - semaphore controls concurrency
            tasks = [self._process_single_error_with_semaphore(error) for error in invalid_option_errors]

            # Process all tasks concurrently with semaphore control
            await asyncio.gather(*tasks, return_exceptions=True)

            # Save final state to session
            await self._save_state_to_session("semantic_prediction_complete", state)

            # Count corrections made
            corrections_made = len([e for e in invalid_option_errors if e.recommended_value])

            logger.info("=" * 80)
            logger.info("   FINISHED SEMANTIC PREDICTION NODE")
            logger.info(f"   Output: {corrections_made}/{len(invalid_option_errors)} corrections made")
            logger.info(f"   Success Rate: {(corrections_made/len(invalid_option_errors)*100):.1f}%")
            logger.info("=" * 80)

            # Log final cache statistics
            self._log_final_cache_statistics()

            logger.info("Completed semantic search prediction")

            # Create success AgentResult with processing summary
            success_message: Message = {
                "content": [
                    {
                        "text": f"Semantic search prediction completed. Processed {self._processed_count} errors, generated {len([e for e in invalid_option_errors if e.recommended_value])} recommendations."
                    }
                ]
            }
            agent_result = AgentResult(
                stop_reason="end_turn",
                message=success_message,
                metrics=EventLoopMetrics(),
                state={
                    "processed_errors": self._processed_count,
                    "total_errors": len(invalid_option_errors),
                },
            )

            return MultiAgentResult(
                status=Status.COMPLETED,
                results={"semantic_prediction": NodeResult(result=agent_result, status=Status.COMPLETED)},
            )

        except Exception as e:
            job_id = (
                getattr(state, "job_id", "unknown") if "state" in locals() and hasattr(state, "job_id") else "unknown"
            )
            error_msg = f"Semantic prediction failed for job {job_id}: {e}"
            logger.error(error_msg)

            return MultiAgentResult(
                status=Status.FAILED,
                results={"semantic_prediction": NodeResult(result=e, status=Status.FAILED)},
            )

    async def _get_semantic_recommendation_with_confidence(
        self,
        invalid_value: str,
        valid_options: List[str],
        state: Optional[ProcessorState] = None,
    ) -> Tuple[Optional[str], float]:
        """
        Get semantic recommendation for an invalid value with confidence score.

        Args:
            invalid_value: The invalid value that needs a recommendation
            valid_options: List of valid options to match against
            state: Optional ProcessorState for token usage tracking

        Returns:
            Tuple of (best matching valid option or None, similarity score)
        """
        if not valid_options:
            logger.debug(f"No valid options provided for '{invalid_value}'")
            return None, 0.0

        # Edge case: If there's only one valid option, always recommend it with high confidence
        if len(valid_options) == 1:
            recommendation = valid_options[0]
            logger.debug(f"Single valid option available, recommending '{recommendation}' for '{invalid_value}'")
            return recommendation, 1.0

        try:
            # Get embedding for the invalid value
            invalid_embedding = await self._get_embedding(invalid_value, state)

            # Get embeddings for all valid options in parallel for better performance
            valid_embedding_tasks = [self._get_embedding(option, state) for option in valid_options]
            valid_embeddings = await asyncio.gather(*valid_embedding_tasks)

            # Use vectorized batch cosine similarity calculation
            similarities = self._calculate_batch_cosine_similarities(invalid_embedding, valid_embeddings)

            # Find the best match above threshold with early termination for perfect matches
            max_similarity = max(similarities)
            best_match_index = similarities.index(max_similarity)

            # Early termination: if we have a near-perfect match (>0.99), return immediately
            if max_similarity > 0.99:
                best_match = valid_options[best_match_index]
                logger.debug(
                    f"Near-perfect match '{best_match}' for '{invalid_value}' with similarity {max_similarity:.3f}"
                )
                return best_match, max_similarity

            if max_similarity >= self.config.cosine_similarity_threshold:
                best_match = valid_options[best_match_index]
                logger.debug(f"Found match '{best_match}' for '{invalid_value}' with similarity {max_similarity:.3f}")
                return best_match, max_similarity
            else:
                logger.debug(
                    f"No match above threshold {self.config.cosine_similarity_threshold} for '{invalid_value}' (max: {max_similarity:.3f})"
                )
                return None, max_similarity

        except Exception as e:
            logger.error(f"Error getting semantic recommendation for '{invalid_value}': {e}")
            return None, 0.0

    async def _process_single_error_with_semaphore(self, error: ValidationErrorDetail) -> None:
        """
        Process a single validation error with semaphore control and progress tracking.

        This method wraps _process_single_error with semaphore control to limit
        concurrency and track progress for logging.

        Args:
            error: ValidationErrorDetail to process
        """
        async with self._semaphore:
            # Process the error
            await self._process_single_error(error)

            # Update progress with thread-safe increment
            async with self._progress_lock:
                self._processed_count += 1
                current_count = self._processed_count

            # Log progress periodically (every 50 errors)
            if current_count % 50 == 0 or current_count >= self._total_count:
                await self._save_progress_to_session(current_count, self._total_count)
                self._log_cache_statistics(current_count, self._total_count)

    async def _process_single_error(self, error: ValidationErrorDetail) -> None:
        """
        Process a single validation error and add recommendation with confidence.

        This method is used for batch processing of errors concurrently.

        Args:
            error: ValidationErrorDetail to process
        """
        try:
            recommendation, similarity_score = await self._get_semantic_recommendation_with_confidence(
                error.current_value, error.valid_options or [], self._current_state
            )
            if recommendation:
                error.recommended_value = recommendation
                error.correction_node = CorrectionNodeType.SEMANTIC_PREDICTION  # Set node attribution

                # Use raw similarity score for granular confidence
                # Only LLM node should use enum-based bucketing
                confidence_level = "High" if similarity_score >= 0.9 else "Medium" if similarity_score >= 0.7 else "Low"
                error.confidence_score = similarity_score  # Use raw similarity, not bucketed
                error.confidence_level = confidence_level

                logger.debug(
                    f"Added recommendation '{recommendation}' for value '{error.current_value}' "
                    f"with confidence {confidence_level} ({similarity_score:.3f})"
                )
        except Exception as e:
            logger.warning(f"Failed to get recommendation for '{error.current_value}': {e}")
            # Exception is logged but not raised to allow other errors in batch to continue

    async def _get_embedding(self, text: str, state: Optional[ProcessorState] = None) -> List[float]:
        """
        Get embedding with cache hierarchy fallback and comprehensive metrics tracking.

        Args:
            text: Text to get embedding for
            state: Optional ProcessorState for token usage tracking

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails after retries
        """
        cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        text_preview = text[:50] + "..." if len(text) > 50 else text

        # Try Redis cache first (if enabled)
        if self.config.enable_redis_cache:
            try:
                cached = await self._get_from_redis_cache(cache_key)
                if cached:
                    self._cache_stats["redis_hits"] += 1
                    logger.debug(f"[OK] Redis cache HIT for: '{text_preview}' (key: {cache_key[:12]}...)")
                    return cached
                else:
                    self._cache_stats["redis_misses"] += 1
                    logger.debug(f"[FAIL] Redis cache MISS for: '{text_preview}' (key: {cache_key[:12]}...)")
            except Exception as e:
                self._cache_stats["redis_misses"] += 1
                logger.warning(f"[FAIL] Redis cache lookup failed for '{text_preview}': {e}")

        # Try in-memory cache (if enabled and Redis disabled)
        if self._memory_cache is not None:
            # Check cache (read-only, fast check without lock)
            if cache_key in self._memory_cache:
                # Use lock for LRU update to prevent race conditions
                async with self._cache_lock:
                    # Double-check after acquiring lock
                    if cache_key in self._memory_cache:
                        embedding = self._memory_cache.pop(cache_key)
                        self._memory_cache[cache_key] = embedding
                        self._cache_stats["memory_hits"] += 1
                        logger.debug(f"[OK] Memory cache HIT for: '{text_preview}' (key: {cache_key[:12]}...)")
                        return embedding

            self._cache_stats["memory_misses"] += 1
            logger.debug(f"[FAIL] Memory cache MISS for: '{text_preview}' (key: {cache_key[:12]}...)")

        # Complete cache miss - generate new embedding
        self._cache_stats["cache_misses"] += 1
        self._cache_stats["embeddings_generated"] += 1
        logger.debug(f"CACHE MISS - Generating new embedding for: '{text_preview}' (key: {cache_key[:12]}...)")
        embedding = await self._generate_embedding(text, state)

        # Store in appropriate cache
        await self._store_embedding(cache_key, embedding)

        return embedding

    async def _get_from_redis_cache(self, cache_key: str) -> Optional[List[float]]:
        """
        Retrieve embedding from Redis cache.

        Args:
            cache_key: Cache key for the embedding

        Returns:
            Cached embedding or None if not found
        """
        try:
            if self._redis_client is None:
                self._redis_client = redis.Redis(
                    host=self.config.redis_endpoint,
                    port=self.config.redis_port,
                    decode_responses=False,
                )

            cached_data = await self._redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data.decode("utf-8"))
            return None

        except Exception as e:
            logger.warning(f"Redis cache retrieval failed: {e}")
            return None

    async def _store_embedding(self, cache_key: str, embedding: List[float]) -> None:
        """
        Store embedding in appropriate cache with detailed logging.

        Args:
            cache_key: Cache key for the embedding
            embedding: Embedding vector to store
        """
        if self.config.enable_redis_cache:
            try:
                await self._store_in_redis_cache(cache_key, embedding)
                logger.debug(f"Stored embedding in Redis cache (key: {cache_key[:12]}...)")
            except Exception as e:
                logger.warning(f"[FAIL] Redis cache storage failed for key {cache_key[:12]}...: {e}")
        elif self._memory_cache is not None:
            # Use lock for thread-safe cache modifications
            async with self._cache_lock:
                # LRU eviction if at max size
                evicted_key = None
                if len(self._memory_cache) >= self.config.memory_cache_max_size:
                    evicted_key, _ = self._memory_cache.popitem(last=False)  # Remove oldest
                    logger.debug(f"Memory cache evicted oldest entry (key: {evicted_key[:12]}...)")

                self._memory_cache[cache_key] = embedding
                cache_size = len(self._memory_cache)
                logger.debug(
                    f"Stored embedding in memory cache (key: {cache_key[:12]}..., size: {cache_size}/{self.config.memory_cache_max_size})"
                )

                # Log when cache is getting full
                if cache_size > self.config.memory_cache_max_size * 0.9:
                    logger.info(
                        f"[WARN] Memory cache is {(cache_size/self.config.memory_cache_max_size)*100:.1f}% full ({cache_size}/{self.config.memory_cache_max_size})"
                    )

    async def _store_in_redis_cache(self, cache_key: str, embedding: List[float]) -> None:
        """
        Store embedding in Redis cache.

        Args:
            cache_key: Cache key for the embedding
            embedding: Embedding vector to store
        """
        try:
            if self._redis_client is None:
                self._redis_client = redis.Redis(
                    host=self.config.redis_endpoint,
                    port=self.config.redis_port,
                    decode_responses=False,
                )

            # Store with 24 hour TTL
            await self._redis_client.setex(
                cache_key,
                86400,
                json.dumps(embedding).encode("utf-8"),  # 24 hours
            )
            logger.debug("Stored embedding in Redis cache")

        except Exception as e:
            logger.warning(f"Redis cache storage failed: {e}")
            raise

    async def _generate_embedding(self, text: str, state: Optional[ProcessorState] = None) -> List[float]:
        """
        Generate embedding using configured AI service.

        Args:
            text: Text to generate embedding for
            state: Optional ProcessorState for token usage tracking

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails after retries
        """
        for attempt in range(self.config.max_retries):
            try:
                if self.config.embedding_provider == "bedrock":
                    return await self._generate_bedrock_embedding(text, state)
                elif self.config.embedding_provider == "sagemaker":
                    return await self._generate_sagemaker_embedding(text)
                else:
                    raise ValueError(f"Unsupported embedding provider: {self.config.embedding_provider}")

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    logger.error(f"Failed to generate embedding after {self.config.max_retries} attempts: {e}")
                    raise
                else:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(f"Embedding generation attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)

    async def _generate_bedrock_embedding(self, text: str, state: Optional[ProcessorState] = None) -> List[float]:
        """
        Generate embedding using Amazon Bedrock.

        Args:
            text: Text to generate embedding for
            state: Optional ProcessorState for token usage tracking

        Returns:
            Embedding vector as list of floats
        """
        try:
            if self._bedrock_client is None:
                self._bedrock_client = boto3.client("bedrock-runtime", region_name=self.config.aws_region)

            # Prepare request body based on model
            if "titan" in self.config.bedrock_model_id.lower():
                body = json.dumps({"inputText": text})
            else:
                # Generic format for other models
                body = json.dumps({"texts": [text], "input_type": "search_query"})

            response = self._bedrock_client.invoke_model(
                modelId=self.config.bedrock_model_id,
                body=body,
                contentType="application/json",
            )

            response_body = json.loads(response["body"].read())

            # Track token usage if state is provided
            if state is not None:
                self._track_embedding_token_usage(response_body, state)

            # Extract embedding based on model response format
            if "titan" in self.config.bedrock_model_id.lower():
                embedding = response_body["embedding"]
            else:
                # Generic format for other models
                embedding = response_body["embeddings"][0]

            return embedding

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Bedrock API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Bedrock embedding generation failed: {e}")
            raise

    def _track_embedding_token_usage(self, response_body: Dict[str, Any], state: ProcessorState) -> None:
        """
        Extract and track token usage from Bedrock embedding API response.

        Args:
            response_body: Response body from Bedrock embedding API
            state: ProcessorState to accumulate token usage
        """
        try:
            # Get or create token usage entry for this node
            node_name = "semantic_prediction"
            if node_name not in state.token_usage:
                state.token_usage[node_name] = NodeTokenUsage(
                    node_name=node_name, embedding_model_id=self.config.bedrock_model_id
                )

            node_usage = state.token_usage[node_name]

            # Extract token count from response body
            # For Titan embedding models, the response includes inputTextTokenCount
            token_count = 0
            if "inputTextTokenCount" in response_body:
                token_count = response_body["inputTextTokenCount"]
            elif "input_tokens" in response_body:
                # Generic format for other models
                token_count = response_body["input_tokens"]

            # Accumulate token counts
            node_usage.embedding_calls += 1
            node_usage.embedding_tokens += token_count

            logger.debug(
                f"Token usage tracked: +{token_count} tokens "
                f"(total: {node_usage.embedding_tokens} tokens, {node_usage.embedding_calls} calls)"
            )

        except Exception as e:
            logger.warning(f"Failed to track embedding token usage: {e}")

    async def _generate_sagemaker_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using SageMaker endpoint.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector as list of floats
        """
        try:
            if self._sagemaker_client is None:
                self._sagemaker_client = boto3.client("sagemaker-runtime", region_name=self.config.aws_region)

            # Prepare request payload
            payload = json.dumps({"inputs": text})

            response = self._sagemaker_client.invoke_endpoint(
                EndpointName=self.config.sagemaker_endpoint_name,
                ContentType="application/json",
                Body=payload,
            )

            response_body = json.loads(response["Body"].read())

            # Extract embedding from response
            # This may need adjustment based on your specific SageMaker endpoint format
            if isinstance(response_body, list):
                embedding = response_body
            elif isinstance(response_body, dict):
                embedding = response_body.get("embeddings", response_body.get("vectors", []))
            else:
                embedding = response_body

            return embedding

        except (BotoCoreError, ClientError) as e:
            logger.error(f"SageMaker API error: {e}")
            raise
        except Exception as e:
            logger.error(f"SageMaker embedding generation failed: {e}")
            raise

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        try:
            # Convert to numpy arrays for efficient computation
            a = np.array(vec1)
            b = np.array(vec2)

            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def _calculate_batch_cosine_similarities(
        self, query_vec: List[float], candidate_vecs: List[List[float]]
    ) -> List[float]:
        """
        Calculate cosine similarities between one query vector and multiple candidate vectors using vectorized operations.

        This is significantly faster than individual calculations for multiple comparisons.

        Args:
            query_vec: Single query vector
            candidate_vecs: List of candidate vectors to compare against

        Returns:
            List of cosine similarity scores
        """
        try:
            if not candidate_vecs:
                return []

            # Convert to numpy arrays
            query = np.array(query_vec)
            candidates = np.array(candidate_vecs)  # Shape: (n_candidates, embedding_dim)

            # Normalize query vector
            query_norm = np.linalg.norm(query)
            if query_norm == 0:
                return [0.0] * len(candidate_vecs)
            query_normalized = query / query_norm

            # Normalize candidate vectors
            candidate_norms = np.linalg.norm(candidates, axis=1)
            # Handle zero vectors
            nonzero_mask = candidate_norms != 0
            similarities = np.zeros(len(candidate_vecs))

            if np.any(nonzero_mask):
                candidates_normalized = candidates[nonzero_mask] / candidate_norms[nonzero_mask, np.newaxis]

                # Vectorized dot product: query_normalized @ candidates_normalized.T
                similarities[nonzero_mask] = np.dot(candidates_normalized, query_normalized)

            return similarities.tolist()

        except Exception as e:
            logger.error(f"Error in batch cosine similarity calculation: {e}")
            # Fallback to individual calculations
            return [self._calculate_cosine_similarity(query_vec, vec) for vec in candidate_vecs]

    def _get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get current cache statistics.

        Returns:
            Dictionary with cache statistics and hit ratios
        """
        stats = self._cache_stats.copy()

        # Calculate hit ratios
        total_redis_requests = stats["redis_hits"] + stats["redis_misses"]
        total_memory_requests = stats["memory_hits"] + stats["memory_misses"]
        total_requests = total_redis_requests + total_memory_requests

        stats["redis_hit_ratio"] = stats["redis_hits"] / total_redis_requests if total_redis_requests > 0 else 0.0
        stats["memory_hit_ratio"] = stats["memory_hits"] / total_memory_requests if total_memory_requests > 0 else 0.0
        stats["overall_hit_ratio"] = (
            (stats["redis_hits"] + stats["memory_hits"]) / total_requests if total_requests > 0 else 0.0
        )

        # Add cache sizes
        stats["memory_cache_size"] = len(self._memory_cache) if self._memory_cache is not None else 0
        stats["memory_cache_max_size"] = self.config.memory_cache_max_size

        return stats

    def _log_cache_statistics(self, processed: int, total: int) -> None:
        """
        Log cache statistics during processing.

        Args:
            processed: Number of errors processed so far
            total: Total number of errors to process
        """
        stats = self._get_cache_statistics()
        logger.info(
            f"Cache Stats ({processed}/{total}): "
            f"Hits: {stats['redis_hits'] + stats['memory_hits']}, "
            f"Misses: {stats['cache_misses']}, "
            f"Hit Ratio: {stats['overall_hit_ratio']:.1%}, "
            f"Generated: {stats['embeddings_generated']}"
        )

    def _log_final_cache_statistics(self) -> None:
        """
        Log comprehensive final cache statistics.
        """
        stats = self._get_cache_statistics()

        logger.info("=" * 50)
        logger.info(" FINAL CACHE STATISTICS")
        logger.info("=" * 50)

        # Redis cache stats
        if self.config.enable_redis_cache:
            logger.info(
                f"Redis Cache: {stats['redis_hits']} hits, {stats['redis_misses']} misses ({stats['redis_hit_ratio']:.1%} hit ratio)"
            )
        else:
            logger.info("Redis Cache: Disabled")

        # Memory cache stats
        if self._memory_cache is not None:
            logger.info(
                f"Memory Cache: {stats['memory_hits']} hits, {stats['memory_misses']} misses ({stats['memory_hit_ratio']:.1%} hit ratio)"
            )
            logger.info(
                f"Memory Cache Size: {stats['memory_cache_size']}/{stats['memory_cache_max_size']} ({stats['memory_cache_size']/stats['memory_cache_max_size']:.1%} full)"
            )
        else:
            logger.info("Memory Cache: Disabled")

        # Overall stats
        logger.info(f"Overall Hit Ratio: {stats['overall_hit_ratio']:.1%}")
        logger.info(f"Cache Misses (new embeddings): {stats['cache_misses']}")
        logger.info(f"Total Embeddings Generated: {stats['embeddings_generated']}")
        logger.info("=" * 50)

    async def close(self) -> None:
        """
        Clean up resources.
        """
        if self._redis_client:
            try:
                await self._redis_client.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")

        logger.info("SemanticSearchPredictionNode resources cleaned up")

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
                    "semantic_predictions_count": (
                        len(
                            [
                                e
                                for e in state.combined_results.validation_results.validation_results
                                if e.error_type == ValidationErrorType.INVALID_OPTION and e.recommended_value
                            ]
                        )
                        if state.has_validation_results()
                        else 0
                    ),
                }

                # Check if session manager supports the expected methods
                if hasattr(self.session_manager, "save_data"):
                    await self.session_manager.save_data(f"semantic_prediction_{checkpoint}", state_data)
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
                    await self.session_manager.save_data("semantic_prediction_progress", progress_data)
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
                # Only attempt cleanup if session manager supports it
                if hasattr(self.session_manager, "delete_data"):
                    # Clean up semantic prediction specific session data
                    keys_to_clean = [
                        "semantic_prediction_start",
                        "semantic_prediction_complete",
                        "semantic_prediction_skipped",
                        "semantic_prediction_progress",
                    ]

                    for key in keys_to_clean:
                        try:
                            await self.session_manager.delete_data(key)
                        except Exception as e:
                            logger.debug(f"Failed to clean session key {key}: {e}")
                else:
                    logger.debug("Session manager does not support data cleanup - skipping")

                logger.debug("Semantic prediction session data cleaned up")
        except Exception as e:
            logger.warning(f"Error during semantic prediction session cleanup: {e}")
