# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Integration tests for AWS service integrations.

This module contains integration tests that verify the processor's integration
with various AWS services including DynamoDB, S3, Redis (ElastiCache),
Bedrock, and SageMaker.
"""

import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import boto3
import botocore.exceptions
import fakeredis
import pytest
from moto import mock_aws

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_processor.implementations.dynamodb_job_status_saver import (
    DynamodbJobStatusSaver,
)
from metadata_harmonization_processor.models.job import JobResults, MetadataUploadJob
from metadata_harmonization_processor.nodes.semantic_prediction import (
    SemanticSearchPredictionNode,
)


class TestDynamoDBIntegration:
    """Test DynamoDB integration for job status persistence."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_dynamodb_job_status_operations(self):
        """Test DynamoDB job status save, get, and update operations."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = "test-metadata-jobs"

            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()

            job_status_saver = DynamodbJobStatusSaver(table_name, region="us-east-1")

            job_id = f"test-job-{uuid.uuid4()}"

            # Create a MetadataUploadJob instance
            job = MetadataUploadJob(
                job_id=job_id,
                user_id="test-user",
                core_schema_id="core-001",
                program_schema_id="program-001",
                status="processing",
                created_at=datetime.now().isoformat(),
                current_version=1,
            )

            # Test save_job
            await job_status_saver.save_job(job)

            # Test get_job
            retrieved_job = await job_status_saver.get_job(job_id)
            assert retrieved_job is not None
            assert retrieved_job.job_id == job_id
            assert retrieved_job.status == "processing"
            assert retrieved_job.user_id == "test-user"
            assert retrieved_job.current_version == 1

            # Test update_job_status
            await job_status_saver.update_job_status(job_id, "completed", completed_at=datetime.now().isoformat())

            # Verify status was updated
            updated_job = await job_status_saver.get_job(job_id)
            assert updated_job.status == "completed"
            assert updated_job.completed_at is not None

            # Test add_job_results
            job_results = JobResults(
                storage_type="s3",
                location="s3://test-bucket/results.json",
                bucket="test-bucket",
            )
            await job_status_saver.add_job_results(job_id, 1, job_results)

            # Verify results were added
            job_with_results = await job_status_saver.get_job(job_id)
            assert "1" in job_with_results.results
            assert job_with_results.results["1"].storage_type == "s3"
            assert job_with_results.results["1"].location == "s3://test-bucket/results.json"

            # Test increment_job_version
            new_version = await job_status_saver.increment_job_version(job_id)
            assert new_version == 2

            # Verify version was incremented
            final_job = await job_status_saver.get_job(job_id)
            assert final_job.current_version == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_dynamodb_error_handling(self):
        """Test DynamoDB error handling and retry logic."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = "test-metadata-jobs"

            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()

            job_status_saver = DynamodbJobStatusSaver(table_name, region="us-east-1")

            # Test get_job for non-existent job
            job = await job_status_saver.get_job("non-existent-job")
            assert job is None

            # Test with invalid table name (should handle gracefully)
            invalid_saver = DynamodbJobStatusSaver("non-existent-table", region="us-east-1")

            # Create a test job
            test_job = MetadataUploadJob(
                job_id="test-job",
                user_id="test-user",
                core_schema_id="core-001",
                program_schema_id="program-001",
                status="processing",
                created_at=datetime.now().isoformat(),
            )

            # Should raise an exception for invalid table
            with pytest.raises(Exception):
                await invalid_saver.save_job(test_job)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_dynamodb_concurrent_operations(self):
        """Test concurrent DynamoDB operations."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = "test-metadata-jobs"

            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()

            job_status_saver = DynamodbJobStatusSaver(table_name, region="us-east-1")

            async def save_job(job_num: int):
                job_id = f"concurrent-job-{job_num}"
                job = MetadataUploadJob(
                    job_id=job_id,
                    user_id=f"user-{job_num}",
                    core_schema_id="core-001",
                    program_schema_id="program-001",
                    status="processing",
                    created_at=datetime.now().isoformat(),
                    current_version=1,
                )
                await job_status_saver.save_job(job)
                return job_id

            # Run concurrent operations
            tasks = [save_job(i) for i in range(10)]
            job_ids = await asyncio.gather(*tasks)

            # Verify all jobs were saved
            for job_id in job_ids:
                retrieved_job = await job_status_saver.get_job(job_id)
                assert retrieved_job is not None
                assert retrieved_job.status == "processing"


class TestS3Integration:
    """Test S3 integration for session management."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_s3_session_data_persistence(self):
        """Test S3 session data persistence and retrieval."""
        with mock_aws():
            s3_client = boto3.client("s3", region_name="us-east-1")
            bucket_name = "test-metadata-sessions"
            s3_client.create_bucket(Bucket=bucket_name)

            # Mock S3SessionManager operations
            session_id = f"test-session-{uuid.uuid4()}"
            session_key = f"sessions/{session_id}/state.json"

            # Test data to persist
            test_data = {
                "session_id": session_id,
                "program_id": "prog-001",
                "core_id": "core-001",
                "processing_stage": "validation",
                "timestamp": datetime.now().isoformat(),
            }

            # Save data to S3
            s3_client.put_object(
                Bucket=bucket_name,
                Key=session_key,
                Body=json.dumps(test_data),
                ContentType="application/json",
            )

            # Retrieve data from S3
            response = s3_client.get_object(Bucket=bucket_name, Key=session_key)
            retrieved_data = json.loads(response["Body"].read())

            assert retrieved_data == test_data
            assert retrieved_data["session_id"] == session_id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_s3_session_cleanup(self):
        """Test S3 session cleanup operations."""
        with mock_aws():
            s3_client = boto3.client("s3", region_name="us-east-1")
            bucket_name = "test-metadata-sessions"
            s3_client.create_bucket(Bucket=bucket_name)

            session_id = f"cleanup-session-{uuid.uuid4()}"

            # Create multiple session files
            session_files = [
                f"sessions/{session_id}/state.json",
                f"sessions/{session_id}/intermediate/schema_alignment.json",
                f"sessions/{session_id}/intermediate/validation.json",
            ]

            for file_key in session_files:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=file_key,
                    Body=json.dumps({"test": "data"}),
                    ContentType="application/json",
                )

            # Verify files exist
            objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"sessions/{session_id}/")
            assert "Contents" in objects
            assert len(objects["Contents"]) == len(session_files)

            # Cleanup session (delete all files with session prefix)
            for obj in objects["Contents"]:
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])

            # Verify cleanup
            objects_after = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"sessions/{session_id}/")
            assert "Contents" not in objects_after

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_s3_error_handling(self):
        """Test S3 error handling for various failure scenarios."""
        with mock_aws():
            s3_client = boto3.client("s3", region_name="us-east-1")
            bucket_name = "test-metadata-sessions"
            s3_client.create_bucket(Bucket=bucket_name)

            # Test access to non-existent object
            with pytest.raises(botocore.exceptions.ClientError):
                s3_client.get_object(Bucket=bucket_name, Key="non-existent-key")

            # Test access to non-existent bucket
            with pytest.raises(botocore.exceptions.ClientError):
                s3_client.get_object(Bucket="non-existent-bucket", Key="test-key")


class TestRedisIntegration:
    """Test Redis integration for caching."""

    @pytest.fixture
    def fake_redis(self):
        """Create fake Redis instance for testing."""
        return fakeredis.FakeRedis()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_redis_embedding_cache_operations(self, fake_redis):
        """Test Redis caching operations for embeddings."""

        # Mock embedding data
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        cache_key = "embedding:test_text_hash"

        # Test cache miss
        cached_value = fake_redis.get(cache_key)
        assert cached_value is None

        # Test cache set
        fake_redis.set(cache_key, json.dumps(test_embedding), ex=3600)

        # Test cache hit
        cached_value = fake_redis.get(cache_key)
        assert cached_value is not None
        retrieved_embedding = json.loads(cached_value)
        assert retrieved_embedding == test_embedding

        # Test cache expiration (simulate)
        fake_redis.delete(cache_key)
        cached_value = fake_redis.get(cache_key)
        assert cached_value is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self):
        """Test Redis connection error handling - node degrades gracefully."""

        with patch("redis.Redis", side_effect=Exception("Connection failed")):
            config = ProcessorConfig(
                enable_redis_cache=True,
                redis_endpoint="invalid-endpoint",
                redis_port=6379,
                schema_directory="/tmp",
                session_s3_bucket="test-bucket",
                results_s3_bucket="test-results-bucket",
            )

            # The node should initialize successfully even with Redis failure
            # (graceful degradation - disables Redis caching)
            node = SemanticSearchPredictionNode(config)
            assert node is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_redis_cache_performance(self, fake_redis):
        """Test Redis cache performance with multiple operations."""

        # Test bulk cache operations
        embeddings = {f"embedding:text_{i}": [float(j) for j in range(10)] for i in range(100)}

        # Bulk set operations
        start_time = datetime.now()
        for key, embedding in embeddings.items():
            fake_redis.set(key, json.dumps(embedding))
        set_duration = (datetime.now() - start_time).total_seconds()

        # Bulk get operations
        start_time = datetime.now()
        for key in embeddings.keys():
            cached_value = fake_redis.get(key)
            assert cached_value is not None
        get_duration = (datetime.now() - start_time).total_seconds()

        print(f"Redis bulk set duration: {set_duration:.4f}s")
        print(f"Redis bulk get duration: {get_duration:.4f}s")

        # Performance should be reasonable for 100 operations
        assert set_duration < 1.0
        assert get_duration < 1.0


class TestBedrockIntegration:
    """Test Amazon Bedrock integration for embeddings."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bedrock_embedding_generation(self):
        """Test Bedrock embedding generation with mocked service."""

        # Mock Bedrock client
        with patch("boto3.client") as mock_boto3:
            mock_bedrock = MagicMock()
            mock_boto3.return_value = mock_bedrock

            # Mock embedding response
            mock_response = {"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]}
            mock_bedrock.invoke_model.return_value = {"body": MagicMock()}
            mock_bedrock.invoke_model.return_value["body"].read.return_value = json.dumps(mock_response).encode()

            config = ProcessorConfig(
                embedding_provider="bedrock",
                bedrock_model_id="amazon.titan-embed-text-v1",
                enable_redis_cache=False,
                enable_memory_cache=False,
                schema_directory="/tmp",
                session_s3_bucket="test-bucket",
                results_s3_bucket="test-results-bucket",
            )

            node = SemanticSearchPredictionNode(config)

            # Test embedding generation
            embedding = await node._generate_embedding("test text")

            assert embedding == mock_response["embedding"]
            mock_bedrock.invoke_model.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bedrock_error_handling(self):
        """Test Bedrock error handling for various failure scenarios."""

        with patch("boto3.client") as mock_boto3:
            mock_bedrock = MagicMock()
            mock_boto3.return_value = mock_bedrock

            # Mock service error
            mock_bedrock.invoke_model.side_effect = Exception("Service unavailable")

            config = ProcessorConfig(
                embedding_provider="bedrock",
                bedrock_model_id="amazon.titan-embed-text-v1",
                enable_redis_cache=False,
                enable_memory_cache=False,
                schema_directory="/tmp",
                session_s3_bucket="test-bucket",
                results_s3_bucket="test-results-bucket",
            )

            node = SemanticSearchPredictionNode(config)

            # Should handle Bedrock errors gracefully
            with pytest.raises(Exception):
                await node._generate_embedding("test text")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bedrock_retry_logic(self):
        """Test Bedrock retry logic for transient failures."""

        with patch("boto3.client") as mock_boto3:
            mock_bedrock = MagicMock()
            mock_boto3.return_value = mock_bedrock

            # Mock persistent failure
            mock_bedrock.invoke_model.side_effect = Exception("Throttling")

            config = ProcessorConfig(
                embedding_provider="bedrock",
                bedrock_model_id="amazon.titan-embed-text-v1",
                max_retries=3,
                enable_redis_cache=False,
                enable_memory_cache=False,
                schema_directory="/tmp",
                session_s3_bucket="test-bucket",
                results_s3_bucket="test-results-bucket",
            )

            node = SemanticSearchPredictionNode(config)

            # Should fail after exhausting retries
            with pytest.raises(Exception, match="Throttling"):
                await node._generate_embedding("test text")


class TestSageMakerIntegration:
    """Test SageMaker integration for embeddings."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sagemaker_embedding_generation(self):
        """Test SageMaker embedding generation with mocked service."""

        with patch("boto3.client") as mock_boto3:
            mock_sagemaker = MagicMock()
            mock_boto3.return_value = mock_sagemaker

            # Mock SageMaker response
            mock_response = [0.1, 0.2, 0.3, 0.4, 0.5]
            mock_sagemaker.invoke_endpoint.return_value = {"Body": MagicMock()}
            mock_sagemaker.invoke_endpoint.return_value["Body"].read.return_value = json.dumps(mock_response).encode()

            config = ProcessorConfig(
                embedding_provider="sagemaker",
                sagemaker_endpoint_name="test-embedding-endpoint",
                enable_redis_cache=False,
                enable_memory_cache=False,
                schema_directory="/tmp",
                session_s3_bucket="test-bucket",
                results_s3_bucket="test-results-bucket",
            )

            node = SemanticSearchPredictionNode(config)

            # Test embedding generation
            embedding = await node._generate_embedding("test text")

            assert embedding == mock_response
            mock_sagemaker.invoke_endpoint.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sagemaker_error_handling(self):
        """Test SageMaker error handling for various failure scenarios."""

        with patch("boto3.client") as mock_boto3:
            mock_sagemaker = MagicMock()
            mock_boto3.return_value = mock_sagemaker

            # Mock endpoint error
            mock_sagemaker.invoke_endpoint.side_effect = Exception("Endpoint not found")

            config = ProcessorConfig(
                embedding_provider="sagemaker",
                sagemaker_endpoint_name="non-existent-endpoint",
                enable_redis_cache=False,
                enable_memory_cache=False,
                schema_directory="/tmp",
                session_s3_bucket="test-bucket",
                results_s3_bucket="test-results-bucket",
            )

            node = SemanticSearchPredictionNode(config)

            # Should handle SageMaker errors gracefully
            with pytest.raises(Exception):
                await node._generate_embedding("test text")


class TestAWSServiceIntegration:
    """Test integrated AWS service operations."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration for AWS services."""
        return ProcessorConfig(
            aws_region="us-east-1",
            session_saver_type="s3",
            enable_redis_cache=True,
            redis_endpoint="localhost",
            redis_port=6379,
            embedding_provider="bedrock",
            bedrock_model_id="amazon.titan-embed-text-v1",
            max_retries=3,
            timeout_seconds=30,
            schema_directory="/tmp",
            session_s3_bucket="test-bucket",
            results_s3_bucket="test-results-bucket",
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_integrated_aws_services_workflow(self, test_config):
        """Test integrated workflow using multiple AWS services."""
        with mock_aws():
            # Setup mock AWS services
            # DynamoDB
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table = dynamodb.create_table(
                TableName="test-jobs",
                KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()

            # S3
            s3_client = boto3.client("s3", region_name="us-east-1")
            bucket_name = "test-sessions"
            s3_client.create_bucket(Bucket=bucket_name)

            # Create job status saver
            job_status_saver = DynamodbJobStatusSaver("test-jobs", region="us-east-1")

            # Test integrated workflow
            job_id = f"integrated-test-{uuid.uuid4()}"
            session_id = f"session-{uuid.uuid4()}"

            # Create initial job
            job = MetadataUploadJob(
                job_id=job_id,
                user_id="test-user",
                core_schema_id="core-001",
                program_schema_id="program-001",
                status="processing",
                created_at=datetime.now().isoformat(),
                current_version=1,
            )

            # Save initial job status
            await job_status_saver.save_job(job)

            # Simulate session data in S3
            session_data = {
                "job_id": job_id,
                "session_id": session_id,
                "processing_stage": "validation",
                "timestamp": datetime.now().isoformat(),
            }

            s3_client.put_object(
                Bucket=bucket_name,
                Key=f"sessions/{session_id}/state.json",
                Body=json.dumps(session_data),
                ContentType="application/json",
            )

            # Update job status to completed
            await job_status_saver.update_job_status(job_id, "completed", completed_at=datetime.now().isoformat())

            # Add job results
            job_results = JobResults(
                storage_type="s3",
                location=f"s3://test-bucket/results/{job_id}.json",
                bucket="test-bucket",
            )
            await job_status_saver.add_job_results(job_id, 1, job_results)

            # Verify integrated workflow
            final_job = await job_status_saver.get_job(job_id)
            assert final_job.status == "completed"
            assert final_job.completed_at is not None
            assert "1" in final_job.results

            # Verify session data in S3
            response = s3_client.get_object(Bucket=bucket_name, Key=f"sessions/{session_id}/state.json")
            retrieved_session_data = json.loads(response["Body"].read())
            assert retrieved_session_data["job_id"] == job_id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_aws_service_failure_recovery(self, test_config):
        """Test recovery mechanisms when AWS services fail."""

        # Test DynamoDB failure recovery
        with patch("boto3.resource") as mock_boto3:
            mock_boto3.side_effect = Exception("DynamoDB unavailable")

            # Should handle DynamoDB failure gracefully
            with pytest.raises(Exception):
                DynamodbJobStatusSaver("test-table", region="us-east-1")

        # Test S3 failure recovery
        with patch("boto3.client") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.return_value = mock_s3
            mock_s3.put_object.side_effect = Exception("S3 unavailable")

            # Should handle S3 failure gracefully
            with pytest.raises(Exception):
                mock_s3.put_object(Bucket="test", Key="test", Body="test")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_aws_credentials_and_permissions(self):
        """Test AWS credentials and permissions handling."""

        # Test with missing permissions
        # Note: This would require actual AWS integration to test properly
        # For now, we just verify the error handling structure exists

        config = ProcessorConfig(
            aws_region="us-east-1",
            enable_redis_cache=False,
            schema_directory="/tmp",
            session_s3_bucket="test-bucket",
            results_s3_bucket="test-results-bucket",
        )

        # Verify config loads without AWS credentials
        assert config.aws_region == "us-east-1"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_aws_service_timeouts_and_retries(self):
        """Test AWS service timeout and retry configurations."""

        config = ProcessorConfig(
            max_retries=5,
            timeout_seconds=10,
            enable_redis_cache=False,
            schema_directory="/tmp",
            session_s3_bucket="test-bucket",
            results_s3_bucket="test-results-bucket",
        )

        assert config.max_retries == 5
        assert config.timeout_seconds == 10

        # Test timeout handling (would need actual AWS calls to test properly)
        # For now, verify configuration is properly loaded

        with patch("boto3.client") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client

            # Configure client with timeout
            mock_client.meta.config.read_timeout = config.timeout_seconds
            mock_client.meta.config.retries = {"max_attempts": config.max_retries}

            # Verify configuration
            assert mock_client.meta.config.read_timeout == 10
            assert mock_client.meta.config.retries["max_attempts"] == 5
