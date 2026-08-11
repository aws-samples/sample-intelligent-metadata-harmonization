# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for the SemanticSearchPredictionNode.

This module contains comprehensive unit tests for the semantic search prediction
functionality, including mocked AI services, Redis, in-memory caching, and
Strands Agent compatibility.
"""

import json
from collections import OrderedDict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from strands.multiagent.base import Status

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_processor.models.combined_results import CombinedResults
from metadata_harmonization_processor.models.state import ProcessorState
from metadata_harmonization_processor.models.validation import (
    ValidationErrorDetail,
    ValidationErrorType,
    ValidationResults,
    ValidationResultsSummary,
)
from metadata_harmonization_processor.nodes.semantic_prediction import (
    SemanticSearchPredictionNode,
)


# Mock Strands Message for testing
class MockMessage:
    def __init__(self, content, sender="test", recipient="test", message_type="test"):
        self.content = content
        self.sender = sender
        self.recipient = recipient
        self.message_type = message_type


@pytest.fixture
def base_config():
    """Base configuration for testing."""
    return ProcessorConfig(
        schema_directory="/tmp/test",
        aws_region="us-east-1",
        embedding_provider="bedrock",
        bedrock_model_id="amazon.titan-embed-text-v1",
        session_saver_type="file",
        file_session_directory="/tmp/test_sessions",
        session_s3_bucket="test-session-bucket",
        results_s3_bucket="test-results-bucket",
        enable_redis_cache=False,
        enable_memory_cache=True,
        memory_cache_max_size=100,
        cosine_similarity_threshold=0.8,
        max_retries=3,
        result_saver_type="local",
        results_local_dir="/tmp/test_results",
    )


@pytest.fixture
def redis_config():
    """Configuration with Redis enabled."""
    return ProcessorConfig(
        schema_directory="/tmp/test",
        aws_region="us-east-1",
        embedding_provider="bedrock",
        session_saver_type="file",
        file_session_directory="/tmp/test_sessions",
        session_s3_bucket="test-session-bucket",
        results_s3_bucket="test-results-bucket",
        enable_redis_cache=True,
        redis_endpoint="localhost",
        redis_port=6379,
        enable_memory_cache=False,
        cosine_similarity_threshold=0.8,
        max_retries=3,
        result_saver_type="local",
        results_local_dir="/tmp/test_results",
    )


@pytest.fixture
def sagemaker_config():
    """Configuration with SageMaker provider."""
    return ProcessorConfig(
        schema_directory="/tmp/test",
        aws_region="us-east-1",
        embedding_provider="sagemaker",
        sagemaker_endpoint_name="test-endpoint",
        session_saver_type="file",
        file_session_directory="/tmp/test_sessions",
        session_s3_bucket="test-session-bucket",
        results_s3_bucket="test-results-bucket",
        enable_redis_cache=False,
        enable_memory_cache=True,
        memory_cache_max_size=100,
        cosine_similarity_threshold=0.8,
        max_retries=3,
        result_saver_type="local",
        results_local_dir="/tmp/test_results",
    )


@pytest.fixture
def sample_validation_results():
    """Sample validation results with INVALID_OPTION errors."""
    errors = [
        ValidationErrorDetail(
            row=1,
            column="status",
            current_value="activ",
            valid_options=["active", "inactive", "pending"],
            error_type=ValidationErrorType.INVALID_OPTION,
        ),
        ValidationErrorDetail(
            row=2,
            column="category",
            current_value="typ1",
            valid_options=["type1", "type2", "type3"],
            error_type=ValidationErrorType.INVALID_OPTION,
        ),
        ValidationErrorDetail(
            row=3,
            column="required_field",
            current_value="",
            error_type=ValidationErrorType.REQUIRED_VALUE,
        ),
    ]

    summary = ValidationResultsSummary(
        total_rows=3,
        total_errors=3,
        error_types={
            ValidationErrorType.INVALID_OPTION: 2,
            ValidationErrorType.REQUIRED_VALUE: 1,
        },
        columns_validated=3,
    )

    return ValidationResults(validation_results=errors, summary=summary)


@pytest.fixture
def processor_state_with_validation(sample_validation_results):
    """ProcessorState with validation results."""
    combined_results = CombinedResults(validation_results=sample_validation_results)
    return ProcessorState(
        job_id="test-job-123",
        combined_results=combined_results,
    )


class TestSemanticSearchPredictionNode:
    """Test cases for SemanticSearchPredictionNode."""

    def test_init_with_memory_cache(self, base_config):
        """Test initialization with memory cache enabled."""
        node = SemanticSearchPredictionNode(base_config)

        assert node.config == base_config
        assert node._memory_cache is not None
        assert isinstance(node._memory_cache, OrderedDict)
        assert node._redis_client is None

    def test_init_with_redis_cache(self, redis_config):
        """Test initialization with Redis cache enabled."""
        node = SemanticSearchPredictionNode(redis_config)

        assert node.config == redis_config
        assert node._memory_cache is None
        assert node._redis_client is None  # Not initialized until first use

    def test_init_no_caching(self):
        """Test initialization with no caching."""
        config = ProcessorConfig(
            schema_directory="/tmp/test",
            session_saver_type="file",
            file_session_directory="/tmp/test_sessions",
            session_s3_bucket="test-session-bucket",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=False,
            enable_memory_cache=False,
            result_saver_type="local",
            results_local_dir="/tmp/test_results",
        )
        node = SemanticSearchPredictionNode(config)

        assert node._memory_cache is None
        assert node._redis_client is None

    @pytest.mark.asyncio
    async def test_invoke_async_missing_validation_results(self, base_config):
        """Test invoke_async with missing validation results."""
        node = SemanticSearchPredictionNode(base_config)
        state = ProcessorState(job_id="test-job")

        result = await node.invoke_async(
            task="process",
            invocation_state={"processor_state": state},
        )

        # Should return failed MultiAgentResult instead of raising
        assert hasattr(result, "status") or "status" in result
        if hasattr(result, "status"):
            assert result.status == Status.FAILED
        else:
            assert result["status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_invoke_async_no_invalid_option_errors(self, base_config):
        """Test invoke_async with no INVALID_OPTION errors."""
        node = SemanticSearchPredictionNode(base_config)

        # Create validation results with only REQUIRED_VALUE errors
        errors = [
            ValidationErrorDetail(
                row=1,
                column="field",
                current_value="",
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )
        ]
        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            error_types={ValidationErrorType.REQUIRED_VALUE: 1},
            columns_validated=1,
        )
        validation_results = ValidationResults(validation_results=errors, summary=summary)

        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        result = await node.invoke_async(task="process", invocation_state={"processor_state": state})

        # Should return successful MultiAgentResult
        assert result.status == Status.COMPLETED
        assert "semantic_prediction" in result.results
        node_result = result.results["semantic_prediction"]
        assert node_result.status == Status.COMPLETED

    @pytest.mark.asyncio
    async def test_invoke_async_with_invalid_option_errors(self, base_config, processor_state_with_validation):
        """Test invoke_async with INVALID_OPTION errors."""
        node = SemanticSearchPredictionNode(base_config)

        # Mock the embedding generation and recommendation logic
        with patch.object(
            node,
            "_get_semantic_recommendation_with_confidence",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_rec.side_effect = [
                ("active", 0.95),
                ("type1", 0.90),
            ]

            result = await node.invoke_async(
                task="process",
                invocation_state={"processor_state": processor_state_with_validation},
            )

            # Should return successful MultiAgentResult
            assert result.status == Status.COMPLETED
            assert "semantic_prediction" in result.results

            # Check that recommendations were added to the state in-place
            invalid_option_errors = [
                error
                for error in processor_state_with_validation.combined_results.validation_results.validation_results
                if error.error_type == ValidationErrorType.INVALID_OPTION
            ]

            assert len(invalid_option_errors) == 2
            assert invalid_option_errors[0].recommended_value == "active"
            assert invalid_option_errors[1].recommended_value == "type1"

            # Verify the method was called correctly
            assert mock_rec.call_count == 2

    @pytest.mark.asyncio
    async def test_get_semantic_recommendation_no_valid_options(self, base_config):
        """Test _get_semantic_recommendation_with_confidence with no valid options."""
        node = SemanticSearchPredictionNode(base_config)

        result, confidence = await node._get_semantic_recommendation_with_confidence("test", [], None)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_semantic_recommendation_single_valid_option(self, base_config):
        """Test _get_semantic_recommendation_with_confidence with single valid option - should always recommend it."""
        node = SemanticSearchPredictionNode(base_config)

        # Test with completely unrelated strings - should still recommend the single option
        result, _ = await node._get_semantic_recommendation_with_confidence("asdf", ["Cyclospora spp"], None)

        assert result == "Cyclospora spp"

        # Test with somewhat related strings - should still recommend the single option
        result, _ = await node._get_semantic_recommendation_with_confidence("activ", ["active"], None)

        assert result == "active"

        # Test with empty string - should still recommend the single option
        result, _ = await node._get_semantic_recommendation_with_confidence("", ["required_value"], None)

        assert result == "required_value"

    @pytest.mark.asyncio
    async def test_get_semantic_recommendation_unknown_values_no_assumption(self, base_config):
        """Test _get_semantic_recommendation_with_confidence with unknown-type values - should not make assumptions."""
        node = SemanticSearchPredictionNode(base_config)

        # Test with "unknown" and binary choice - should NOT recommend without semantic similarity
        with patch.object(node, "_get_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.side_effect = [
                [1.0, 0.0, 0.0],  # "unknown"
                [0.0, 1.0, 0.0],  # "Single" - low similarity
                [0.0, 0.0, 1.0],  # "Paired" - low similarity
            ]

            result, _ = await node._get_semantic_recommendation_with_confidence("unknown", ["Single", "Paired"], None)
            assert result is None  # Should return None - let user decide

        # Test with "n/a" and binary choice - should NOT recommend without semantic similarity
        with patch.object(node, "_get_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.side_effect = [
                [1.0, 0.0, 0.0],  # "n/a"
                [0.0, 1.0, 0.0],  # "Yes" - low similarity
                [0.0, 0.0, 1.0],  # "No" - low similarity
            ]

            result, _ = await node._get_semantic_recommendation_with_confidence("n/a", ["Yes", "No"], None)
            assert result is None  # Should return None - let user decide

    @pytest.mark.asyncio
    async def test_get_semantic_recommendation_success(self, base_config):
        """Test successful semantic recommendation with confidence."""
        node = SemanticSearchPredictionNode(base_config)

        # Mock embedding generation
        with patch.object(node, "_get_embedding", new_callable=AsyncMock) as mock_embed:
            # Return similar embeddings for "activ" and "active"
            mock_embed.side_effect = [
                [0.1, 0.9, 0.1],  # "activ"
                [0.1, 0.95, 0.05],  # "active" - very similar
                [0.9, 0.1, 0.1],  # "inactive" - different
                [0.5, 0.5, 0.1],  # "pending" - somewhat different
            ]

            result, confidence = await node._get_semantic_recommendation_with_confidence(
                "activ", ["active", "inactive", "pending"], None
            )

            assert result == "active"
            assert confidence > 0.8
            assert mock_embed.call_count == 4

    @pytest.mark.asyncio
    async def test_get_semantic_recommendation_below_threshold(self, base_config):
        """Test semantic recommendation below similarity threshold."""
        node = SemanticSearchPredictionNode(base_config)

        # Mock embedding generation with low similarity
        with patch.object(node, "_get_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.side_effect = [
                [1.0, 0.0, 0.0],  # "test"
                [0.0, 1.0, 0.0],  # "option1" - orthogonal (similarity = 0)
                [0.0, 0.0, 1.0],  # "option2" - orthogonal (similarity = 0)
            ]

            result, _ = await node._get_semantic_recommendation_with_confidence("test", ["option1", "option2"], None)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_embedding_memory_cache_hit(self, base_config):
        """Test embedding retrieval with memory cache hit."""
        node = SemanticSearchPredictionNode(base_config)

        # Pre-populate cache
        cache_key = "test_key"
        embedding = [0.1, 0.2, 0.3]
        node._memory_cache[cache_key] = embedding

        with patch("hashlib.sha256") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = cache_key

            result = await node._get_embedding("test")

            assert result == embedding
            # Verify LRU behavior - item should be moved to end
            assert list(node._memory_cache.keys())[-1] == cache_key

    @pytest.mark.asyncio
    async def test_get_embedding_memory_cache_miss(self, base_config):
        """Test embedding retrieval with memory cache miss."""
        node = SemanticSearchPredictionNode(base_config)

        with patch.object(node, "_generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = [0.1, 0.2, 0.3]

            result = await node._get_embedding("test")

            assert result == [0.1, 0.2, 0.3]
            mock_gen.assert_called_once()

            # Verify embedding was cached
            assert len(node._memory_cache) == 1

    @pytest.mark.asyncio
    async def test_memory_cache_lru_eviction(self, base_config):
        """Test LRU eviction in memory cache."""
        # Set small cache size for testing
        base_config.memory_cache_max_size = 2
        node = SemanticSearchPredictionNode(base_config)

        with patch.object(node, "_generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = [[0.1], [0.2], [0.3]]

            # Add items to fill cache
            await node._get_embedding("item1")
            await node._get_embedding("item2")

            assert len(node._memory_cache) == 2

            # Add third item, should evict first
            await node._get_embedding("item3")

            assert len(node._memory_cache) == 2
            # First item should be evicted
            cache_keys = list(node._memory_cache.keys())
            assert "item1" not in [key for key in cache_keys]

    @pytest.mark.asyncio
    async def test_redis_cache_operations(self, redis_config):
        """Test Redis cache operations."""
        node = SemanticSearchPredictionNode(redis_config)

        # Mock Redis client
        mock_redis = AsyncMock()

        with patch("redis.asyncio.Redis", return_value=mock_redis):
            # Test cache miss
            mock_redis.get.return_value = None

            with patch.object(node, "_generate_embedding", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = [0.1, 0.2, 0.3]

                result = await node._get_embedding("test")

                assert result == [0.1, 0.2, 0.3]
                mock_redis.get.assert_called_once()
                mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_cache_hit(self, redis_config):
        """Test Redis cache hit."""
        node = SemanticSearchPredictionNode(redis_config)

        # Mock Redis client
        mock_redis = AsyncMock()
        cached_embedding = [0.1, 0.2, 0.3]
        mock_redis.get.return_value = json.dumps(cached_embedding).encode("utf-8")

        with patch("redis.asyncio.Redis", return_value=mock_redis):
            result = await node._get_embedding("test")

            assert result == cached_embedding
            mock_redis.get.assert_called_once()
            mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_bedrock_embedding_titan(self, base_config):
        """Test Bedrock embedding generation with Titan model."""
        node = SemanticSearchPredictionNode(base_config)

        # Mock Bedrock client
        mock_client = Mock()
        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode("utf-8")
        mock_client.invoke_model.return_value = mock_response

        with patch("boto3.client", return_value=mock_client):
            result = await node._generate_bedrock_embedding("test text")

            assert result == [0.1, 0.2, 0.3]
            mock_client.invoke_model.assert_called_once()

            # Verify request format
            call_args = mock_client.invoke_model.call_args
            assert call_args[1]["modelId"] == base_config.bedrock_model_id
            body = json.loads(call_args[1]["body"])
            assert body["inputText"] == "test text"

    @pytest.mark.asyncio
    async def test_generate_bedrock_embedding_other_model(self, base_config):
        """Test Bedrock embedding generation with non-Titan model."""
        base_config.bedrock_model_id = "cohere.embed-english-v3"
        node = SemanticSearchPredictionNode(base_config)

        # Mock Bedrock client
        mock_client = Mock()
        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps({"embeddings": [[0.1, 0.2, 0.3]]}).encode("utf-8")
        mock_client.invoke_model.return_value = mock_response

        with patch("boto3.client", return_value=mock_client):
            result = await node._generate_bedrock_embedding("test text")

            assert result == [0.1, 0.2, 0.3]

            # Verify request format for non-Titan model
            call_args = mock_client.invoke_model.call_args
            body = json.loads(call_args[1]["body"])
            assert body["texts"] == ["test text"]
            assert body["input_type"] == "search_query"

    @pytest.mark.asyncio
    async def test_generate_sagemaker_embedding(self, sagemaker_config):
        """Test SageMaker embedding generation."""
        node = SemanticSearchPredictionNode(sagemaker_config)

        # Mock SageMaker client
        mock_client = Mock()
        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = json.dumps([0.1, 0.2, 0.3]).encode("utf-8")
        mock_client.invoke_endpoint.return_value = mock_response

        with patch("boto3.client", return_value=mock_client):
            result = await node._generate_sagemaker_embedding("test text")

            assert result == [0.1, 0.2, 0.3]
            mock_client.invoke_endpoint.assert_called_once()

            # Verify request format
            call_args = mock_client.invoke_endpoint.call_args
            assert call_args[1]["EndpointName"] == sagemaker_config.sagemaker_endpoint_name
            body = json.loads(call_args[1]["Body"])
            assert body["inputs"] == "test text"

    @pytest.mark.asyncio
    async def test_generate_embedding_with_retries(self, base_config):
        """Test embedding generation with retries on failure."""
        node = SemanticSearchPredictionNode(base_config)

        with patch.object(node, "_generate_bedrock_embedding", new_callable=AsyncMock) as mock_bedrock:
            # Fail twice, then succeed
            mock_bedrock.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                [0.1, 0.2, 0.3],
            ]

            result = await node._generate_embedding("test")

            assert result == [0.1, 0.2, 0.3]
            assert mock_bedrock.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_embedding_max_retries_exceeded(self, base_config):
        """Test embedding generation when max retries exceeded."""
        node = SemanticSearchPredictionNode(base_config)

        with patch.object(node, "_generate_bedrock_embedding", new_callable=AsyncMock) as mock_bedrock:
            mock_bedrock.side_effect = Exception("Persistent error")

            with pytest.raises(Exception, match="Persistent error"):
                await node._generate_embedding("test")

            assert mock_bedrock.call_count == base_config.max_retries

    def test_calculate_cosine_similarity(self, base_config):
        """Test cosine similarity calculation."""
        node = SemanticSearchPredictionNode(base_config)

        # Test identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = node._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-6

        # Test orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = node._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 1e-6

        # Test opposite vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = node._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 1e-6

    def test_calculate_cosine_similarity_zero_vectors(self, base_config):
        """Test cosine similarity with zero vectors."""
        node = SemanticSearchPredictionNode(base_config)

        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = node._calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    @pytest.mark.asyncio
    async def test_close_cleanup(self, redis_config):
        """Test resource cleanup on close."""
        node = SemanticSearchPredictionNode(redis_config)

        # Mock Redis client
        mock_redis = AsyncMock()
        node._redis_client = mock_redis

        await node.close()

        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_recommendation(self, base_config, processor_state_with_validation):
        """Test error handling during recommendation generation."""
        node = SemanticSearchPredictionNode(base_config)

        # Mock to raise exception for first error, succeed for second
        with patch.object(node, "_get_semantic_recommendation_with_confidence", new_callable=AsyncMock) as mock_rec:
            mock_rec.side_effect = [Exception("AI service error"), ("type1", 0.90)]

            # Should not raise exception, but continue processing
            result = await node.invoke_async(
                task="process",
                invocation_state={"processor_state": processor_state_with_validation},
            )

            # Should return successful MultiAgentResult
            assert result.status == Status.COMPLETED

            # First error should have no recommendation (exception), second should have one
            invalid_option_errors = [
                error
                for error in processor_state_with_validation.combined_results.validation_results.validation_results
                if error.error_type == ValidationErrorType.INVALID_OPTION
            ]

            assert invalid_option_errors[0].recommended_value is None
            assert invalid_option_errors[1].recommended_value == "type1"

    @pytest.mark.asyncio
    async def test_unsupported_embedding_provider(self):
        """Test error with unsupported embedding provider."""
        # This should raise a validation error during config creation
        with pytest.raises(Exception):  # Pydantic validation error
            ProcessorConfig(
                schema_directory="/tmp/test",
                session_saver_type="file",
                file_session_directory="/tmp/test_sessions",
                session_s3_bucket="test-session-bucket",
                results_s3_bucket="test-results-bucket",
                embedding_provider="invalid_provider",
                enable_redis_cache=False,
                enable_memory_cache=False,
                result_saver_type="local",
                results_local_dir="/tmp/test_results",
            )


class TestSemanticPredictionIntegration:
    """Integration-style tests for semantic prediction."""

    @pytest.mark.asyncio
    async def test_end_to_end_prediction_flow(self, base_config):
        """Test complete end-to-end prediction flow."""
        node = SemanticSearchPredictionNode(base_config)

        # Create test data
        errors = [
            ValidationErrorDetail(
                row=1,
                column="status",
                current_value="activ",
                valid_options=["active", "inactive"],
                error_type=ValidationErrorType.INVALID_OPTION,
            )
        ]

        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            error_types={ValidationErrorType.INVALID_OPTION: 1},
            columns_validated=1,
        )

        validation_results = ValidationResults(validation_results=errors, summary=summary)
        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        # Mock the entire embedding pipeline
        with patch.object(node, "_generate_embedding", new_callable=AsyncMock) as mock_gen:
            # Return embeddings that make "active" more similar to "activ"
            mock_gen.side_effect = [
                [0.9, 0.1, 0.0],  # "activ"
                [0.95, 0.05, 0.0],  # "active" - very similar
                [0.1, 0.9, 0.0],  # "inactive" - different
            ]

            result = await node.invoke_async(
                task="process",
                invocation_state={"processor_state": state},
            )

            # Should return successful MultiAgentResult
            assert result.status == Status.COMPLETED

            # Verify recommendation was added to the state in-place
            error = state.combined_results.validation_results.validation_results[0]
            assert error.recommended_value == "active"

    @pytest.mark.asyncio
    async def test_cache_behavior_across_multiple_calls(self, base_config):
        """Test caching behavior across multiple prediction calls."""
        node = SemanticSearchPredictionNode(base_config)

        with patch.object(node, "_generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = [0.1, 0.2, 0.3]

            # First call should generate embedding
            result1 = await node._get_embedding("test")
            assert mock_gen.call_count == 1

            # Second call should use cache
            result2 = await node._get_embedding("test")
            assert mock_gen.call_count == 1  # No additional calls
            assert result1 == result2

    # MultiAgentBase Compatibility Tests

    @pytest.mark.asyncio
    async def test_multiagent_result_structure(self, base_config, sample_validation_results):
        """Test MultiAgentResult structure compliance."""
        node = SemanticSearchPredictionNode(base_config)
        combined_results = CombinedResults(validation_results=sample_validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        with patch.object(node, "_get_semantic_recommendation_with_confidence", new_callable=AsyncMock) as mock_rec:
            mock_rec.return_value = ("active", 0.95)

            result = await node.invoke_async(task="process", invocation_state={"processor_state": state})

            # Verify MultiAgentResult structure
            assert hasattr(result, "status") or "status" in result
            assert hasattr(result, "results") or "results" in result

            if hasattr(result, "results"):
                assert "semantic_prediction" in result.results
                node_result = result.results["semantic_prediction"]
                assert hasattr(node_result, "result") or "result" in node_result
                assert hasattr(node_result, "status") or "status" in node_result
            else:
                assert "semantic_prediction" in result["results"]
                node_result = result["results"]["semantic_prediction"]
                assert "result" in node_result
                assert "status" in node_result

    @pytest.mark.asyncio
    async def test_multiagent_error_handling(self, base_config):
        """Test MultiAgentBase error handling with failed status."""
        node = SemanticSearchPredictionNode(base_config)

        # Create state without validation results to trigger error
        state = ProcessorState(job_id="test-job")

        result = await node.invoke_async(task="process", invocation_state={"processor_state": state})

        # Verify error result structure
        assert hasattr(result, "status") or "status" in result
        if hasattr(result, "status"):
            assert result.status == (Status.FAILED if hasattr(Status, "FAILED") else "FAILED")
            assert "semantic_prediction" in result.results
            node_result = result.results["semantic_prediction"]
            assert hasattr(node_result, "status") or "status" in node_result
            if hasattr(node_result, "status"):
                assert node_result.status == (Status.FAILED if hasattr(Status, "FAILED") else "FAILED")
        else:
            assert result["status"] == "FAILED"
            assert "semantic_prediction" in result["results"]
            node_result = result["results"]["semantic_prediction"]
            assert node_result["status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_multiagent_successful_processing(self, base_config):
        """Test MultiAgentBase successful processing with completed status."""
        node = SemanticSearchPredictionNode(base_config)

        # Create validation results with no INVALID_OPTION errors
        errors = [
            ValidationErrorDetail(
                row=1,
                column="name",
                current_value="",
                error_type=ValidationErrorType.REQUIRED_VALUE,
            )
        ]
        summary = ValidationResultsSummary(
            total_rows=1,
            total_errors=1,
            error_types={
                ValidationErrorType.REQUIRED_VALUE: 1,
                ValidationErrorType.INVALID_OPTION: 0,
                ValidationErrorType.INVALID_PATTERN: 0,
            },
            columns_validated=1,
        )
        validation_results = ValidationResults(validation_results=errors, summary=summary)
        combined_results = CombinedResults(validation_results=validation_results)
        state = ProcessorState(job_id="test-job", combined_results=combined_results)

        result = await node.invoke_async(
            task="process",
            invocation_state={"processor_state": state},
        )

        # Verify successful result structure
        assert result.status == Status.COMPLETED
        assert "semantic_prediction" in result.results
        node_result = result.results["semantic_prediction"]
        assert node_result.status == Status.COMPLETED

    @pytest.mark.asyncio
    async def test_invalid_input_type_handling(self, base_config):
        """Test handling of invalid input types in MultiAgentBase context."""
        node = SemanticSearchPredictionNode(base_config)

        # Test with invalid input type - should return failed MultiAgentResult
        result = await node.invoke_async(task="process", invocation_state=None)

        # Should return failed MultiAgentResult instead of raising
        assert hasattr(result, "status") or "status" in result
        if hasattr(result, "status"):
            assert result.status == (Status.FAILED if hasattr(Status, "FAILED") else "FAILED")
        else:
            assert result["status"] == "FAILED"
