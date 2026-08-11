# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Contextual inference node for enum value correction.

This node corrects INVALID_OPTION validation errors using k-Nearest Neighbors
with TF-IDF vectorization and co-occurrence analysis.
"""

import asyncio
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger
from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics
from strands.types.content import Message

from ..config import ContextualInferenceConfig
from ..models.validation import (
    CorrectionNodeType,
    ValidationErrorDetail,
    ValidationErrorType,
)
from ..utils.confidence_utils import calculate_prediction_confidence
from ..utils.tfidf_utils import (
    CooccurrenceAnalyzer,
    FeatureVectorizer,
    KNearestNeighbors,
    SchemaColumnDetector,
)


class ContextualInferenceNode(MultiAgentBase):
    """
    MultiAgentBase node for contextual inference correction of INVALID_OPTION errors.

    This node uses k-Nearest Neighbors with TF-IDF vectorization and co-occurrence
    analysis to infer correct enum values based on dataset patterns.
    """

    def __init__(self, config: ContextualInferenceConfig):
        """
        Initialize the contextual inference node.

        Args:
            config: Configuration for contextual inference
        """
        super().__init__()
        self.config = config

        # Will be set from ProcessorState in invoke_async
        self.dataset: Optional[pd.DataFrame] = None
        self.schema: Optional[Dict[str, Any]] = None

        self._semaphore: asyncio.Semaphore = None
        self._processed_count: int = 0
        self._total_count: int = 0

        # Will be initialized during first invoke_async call
        self._initialized: bool = False
        self._feature_vectorizer: Optional[FeatureVectorizer] = None
        self._feature_matrix: Optional[Any] = None
        self._cooccurrence_analyzers: Dict[str, CooccurrenceAnalyzer] = {}

        logger.info(
            f"Initialized ContextualInferenceNode: "
            f"k={config.k_neighbors}, "
            f"similarity_weight={config.similarity_weight:.2f}, "
            f"cooccurrence_weight={config.cooccurrence_weight:.2f}, "
            f"threshold={config.min_confidence_threshold:.2f}"
        )

    async def invoke_async(
        self, task: str | list, invocation_state: dict[str, Any] | None = None, **kwargs
    ) -> MultiAgentResult:
        """
        Process contextual inference using MultiAgentBase framework.

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
                results={"contextual_inference": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        state = invocation_state["processor_state"]

        # Validate that we have validation results
        if not state.has_validation_results():
            error_msg = "ProcessorState must contain validation_results"
            logger.error(error_msg)
            return MultiAgentResult(
                status=Status.FAILED,
                results={"contextual_inference": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
            )

        # Initialize dataset and schema from state on first call
        if not self._initialized:
            if not state.has_aligned_data():
                error_msg = "ProcessorState must contain aligned_df for contextual inference"
                logger.error(error_msg)
                return MultiAgentResult(
                    status=Status.FAILED,
                    results={"contextual_inference": NodeResult(result=Exception(error_msg), status=Status.FAILED)},
                )

            self.dataset = state.aligned_df
            self.schema = state.schema_definition
            self._initialized = True

            logger.info(
                f"Initialized contextual inference with dataset: {self.dataset.shape}, "
                f"schema fields: {len(self.schema) if self.schema else 0}"
            )

        try:
            # Filter for INVALID_OPTION errors without recommendations
            invalid_option_errors = [
                error
                for error in state.combined_results.validation_results.validation_results
                if error.error_type == ValidationErrorType.INVALID_OPTION and not error.recommended_value
            ]

            logger.info("=" * 80)
            logger.info("   STARTING CONTEXTUAL INFERENCE NODE")
            logger.info(f"   Input: {len(invalid_option_errors)} unresolved INVALID_OPTION errors")
            logger.info(
                f"   k-Neighbors: {self.config.k_neighbors}, Threshold: {self.config.min_confidence_threshold:.2f}"
            )
            logger.info("=" * 80)

            if not invalid_option_errors:
                logger.info("No unresolved INVALID_OPTION errors for contextual inference")

                success_message: Message = {"content": [{"text": "No unresolved INVALID_OPTION errors to process"}]}
                agent_result = AgentResult(
                    stop_reason="end_turn",
                    message=success_message,
                    metrics=EventLoopMetrics(),
                    state={"processed": 0, "total": 0},
                )

                return MultiAgentResult(
                    status=Status.COMPLETED,
                    results={"contextual_inference": NodeResult(result=agent_result, status=Status.COMPLETED)},
                )

            logger.info(
                f"Processing {len(invalid_option_errors)} unresolved INVALID_OPTION errors "
                f"with contextual inference"
            )

            # Initialize feature extraction
            await self._initialize_features()

            # Initialize co-occurrence analyzers for each error column
            error_columns = set(error.column for error in invalid_option_errors)
            for column in error_columns:
                if column not in self._cooccurrence_analyzers:
                    await self._initialize_cooccurrence_analyzer(column)

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
                if error.recommended_value and error.correction_node == CorrectionNodeType.CONTEXTUAL_INFERENCE
            )

            logger.info("=" * 80)
            logger.info("   FINISHED CONTEXTUAL INFERENCE NODE")
            logger.info(f"   Output: {corrections_made}/{len(invalid_option_errors)} corrections made")
            logger.info(f"   Success Rate: {(corrections_made/len(invalid_option_errors)*100):.1f}%")
            logger.info("=" * 80)

            # Create success result
            success_message: Message = {
                "content": [
                    {
                        "text": f"Contextual inference completed. Made {corrections_made} corrections "
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
                results={"contextual_inference": NodeResult(result=agent_result, status=Status.COMPLETED)},
            )

        except Exception as e:
            error_msg = f"Contextual inference failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return MultiAgentResult(
                status=Status.FAILED,
                results={"contextual_inference": NodeResult(result=e, status=Status.FAILED)},
            )

    async def _initialize_features(self) -> None:
        """Initialize feature extraction for the dataset."""
        if self._feature_vectorizer is not None:
            return  # Already initialized

        logger.info("Initializing feature extraction...")

        # Detect column types from schema
        column_types = SchemaColumnDetector.detect_column_types(self.schema, self.dataset)

        # Apply regex filtering if patterns are configured
        if self.config.exclude_column_patterns:
            logger.info(f"Applying column exclusion patterns: {self.config.exclude_column_patterns}")
            column_types = SchemaColumnDetector.filter_columns_by_regex(
                column_types, self.config.exclude_column_patterns
            )

        # Create feature vectorizer
        self._feature_vectorizer = FeatureVectorizer(
            text_columns=column_types["text"],
            categorical_columns=column_types["categorical"],
            numeric_columns=column_types["numeric"],
        )

        # Fit and transform the dataset
        self._feature_matrix = self._feature_vectorizer.fit_transform(self.dataset)

        logger.info(
            f"Feature extraction complete: {self._feature_matrix.shape[0]} samples, "
            f"{self._feature_matrix.shape[1]} features"
        )

    async def _initialize_cooccurrence_analyzer(self, column: str) -> None:
        """
        Initialize co-occurrence analyzer for a specific column.

        Args:
            column: Column name to analyze
        """
        logger.debug(f"Initializing co-occurrence analyzer for column: {column}")

        # Get all feature columns (exclude the error column itself)
        all_columns = list(self.dataset.columns)
        feature_columns = [col for col in all_columns if col != column]

        # Create and fit analyzer
        analyzer = CooccurrenceAnalyzer()
        analyzer.fit(df=self.dataset, enum_column=column, feature_columns=feature_columns)

        self._cooccurrence_analyzers[column] = analyzer

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
        Process a single INVALID_OPTION error with contextual inference.

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

            # Get the row index (error.row is 1-indexed, we need 0-indexed)
            row_idx = error.row - 1

            if row_idx < 0 or row_idx >= len(self.dataset):
                logger.warning(f"Invalid row index {row_idx} for error at row {error.row}")
                return

            # Get the row data
            row = self.dataset.iloc[row_idx]

            # Get row's feature vector
            row_vector = self._feature_matrix[row_idx]

            # Find k-nearest neighbors
            neighbors = KNearestNeighbors.find_k_nearest(
                query_vector=row_vector,
                reference_vectors=self._feature_matrix,
                k=self.config.k_neighbors,
            )

            # Calculate similarity-based scores
            similarity_scores = self._calculate_similarity_scores(
                neighbors=neighbors,
                column=error.column,
                valid_options=error.valid_options,
            )

            # Calculate co-occurrence-based scores
            cooccurrence_scores = {}
            if error.column in self._cooccurrence_analyzers:
                analyzer = self._cooccurrence_analyzers[error.column]
                feature_columns = [col for col in self.dataset.columns if col != error.column]
                cooccurrence_scores = analyzer.get_cooccurrence_scores(
                    row=row,
                    enum_options=error.valid_options,
                    feature_columns=feature_columns,
                )

            # Combine scores
            combined_scores = self._combine_scores(
                similarity_scores=similarity_scores,
                cooccurrence_scores=cooccurrence_scores,
                valid_options=error.valid_options,
            )

            # Find best recommendation
            if combined_scores:
                best_option = max(combined_scores.items(), key=lambda x: x[1])
                best_value, best_score = best_option

                if best_score >= self.config.min_confidence_threshold:
                    # Calculate confidence score
                    confidence_score, confidence_level = calculate_prediction_confidence(
                        error.error_type,
                        best_score,
                        self.config.__dict__.get("_confidence_config"),
                    )

                    # Set recommendation with node attribution
                    error.recommended_value = best_value
                    error.correction_node = CorrectionNodeType.CONTEXTUAL_INFERENCE
                    error.confidence_score = confidence_score
                    error.confidence_level = confidence_level

                    logger.debug(
                        f"Contextual inference for row {error.row}, '{error.column}': "
                        f"'{best_value}' (score: {best_score:.3f}, "
                        f"confidence: {confidence_level})"
                    )

        except Exception as e:
            logger.warning(f"Failed to process error for row {error.row}, " f"column {error.column}: {e}")

    def _calculate_similarity_scores(
        self, neighbors: List[tuple], column: str, valid_options: List[str]
    ) -> Dict[str, float]:
        """
        Calculate scores based on k-nearest neighbors.

        Args:
            neighbors: List of (index, similarity) tuples from k-NN
            column: Column name
            valid_options: List of valid enum options

        Returns:
            Dictionary mapping option -> similarity score
        """
        scores = {option: 0.0 for option in valid_options}
        total_weight = 0.0

        for idx, similarity in neighbors:
            # Get the value for this column in the neighbor row
            neighbor_value = str(self.dataset.iloc[idx][column])

            if neighbor_value in valid_options:
                scores[neighbor_value] += similarity
                total_weight += similarity

        # Normalize scores
        if total_weight > 0:
            scores = {k: v / total_weight for k, v in scores.items()}

        return scores

    def _combine_scores(
        self,
        similarity_scores: Dict[str, float],
        cooccurrence_scores: Dict[str, float],
        valid_options: List[str],
    ) -> Dict[str, float]:
        """
        Combine similarity and co-occurrence scores.

        Args:
            similarity_scores: Scores from k-NN similarity
            cooccurrence_scores: Scores from co-occurrence analysis
            valid_options: List of valid enum options

        Returns:
            Dictionary mapping option -> combined score
        """
        combined = {}

        for option in valid_options:
            sim_score = similarity_scores.get(option, 0.0)
            cooc_score = cooccurrence_scores.get(option, 0.0)

            # Weighted combination
            combined[option] = self.config.similarity_weight * sim_score + self.config.cooccurrence_weight * cooc_score

        return combined
