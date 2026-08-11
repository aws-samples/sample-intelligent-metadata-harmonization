# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Unit tests for configuration management system.

Tests the ProcessorConfig class and configuration loading functions
with various scenarios including YAML loading, path resolution,
validation, and error handling.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from metadata_harmonization_processor.config import (
    ProcessorConfig,
    SemanticPredictionConfig,
    deep_merge_dicts,
    load_processor_settings,
    resolve_relative_paths,
)


class TestProcessorConfig:
    """Test ProcessorConfig class validation and initialization."""

    def test_default_config(self):
        """Test ProcessorConfig with minimal required fields."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="test-bucket",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=False,
        )

        assert config.aws_region == "us-east-1"
        assert config.aws_profile is None
        assert config.session_saver_type == "s3"
        assert config.session_s3_prefix == "sessions/"
        assert config.enable_redis_cache is False
        assert config.redis_port == 6379
        assert config.enable_memory_cache is True
        assert config.memory_cache_max_size == 50000
        assert config.embedding_provider == "bedrock"
        assert config.max_retries == 3
        assert config.timeout_seconds == 300
        assert config.cosine_similarity_threshold == 0.8
        assert config.schema_directory == "/path/to/schemas"

    def test_s3_session_manager_validation_success(self):
        """Test successful S3 session manager configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_saver_type="s3",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=False,
        )

        assert config.session_saver_type == "s3"
        assert config.session_s3_bucket == "my-bucket"

    def test_s3_session_manager_validation_failure(self):
        """Test S3 session manager validation fails without bucket."""
        with pytest.raises(
            ValueError,
            match="session_s3_bucket is required when session_saver_type is 's3'",
        ):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_saver_type="s3",
                results_s3_bucket="test-results-bucket",
                enable_redis_cache=False,
            )

    def test_file_session_manager_validation_success(self):
        """Test successful file session manager configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_saver_type="file",
            file_session_directory="/tmp/sessions",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=False,
        )

        assert config.session_saver_type == "file"
        assert config.file_session_directory == "/tmp/sessions"

    def test_file_session_manager_validation_failure(self):
        """Test file session manager validation fails without directory."""
        with pytest.raises(
            ValueError,
            match="file_session_directory is required when session_type is 'file'",
        ):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_saver_type="file",
                results_s3_bucket="test-results-bucket",  # Required for default s3 result saver
                enable_redis_cache=False,  # Disable to avoid requiring redis_endpoint
            )

    def test_redis_cache_validation_success(self):
        """Test successful Redis cache configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=True,
            redis_endpoint="redis.example.com",
        )

        assert config.enable_redis_cache is True
        assert config.redis_endpoint == "redis.example.com"

    def test_redis_cache_validation_failure(self):
        """Test Redis cache validation fails without endpoint."""
        with pytest.raises(
            ValueError,
            match="redis_endpoint is required when enable_redis_cache is True",
        ):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_s3_bucket="my-bucket",
                results_s3_bucket="test-results-bucket",
                enable_redis_cache=True,
            )

    def test_redis_cache_disabled(self):
        """Test Redis cache can be disabled without endpoint."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=False,
        )

        assert config.enable_redis_cache is False
        assert config.redis_endpoint is None

    def test_bedrock_ai_config_validation_success(self):
        """Test successful Bedrock AI configuration via semantic_prediction."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            semantic_prediction=SemanticPredictionConfig(
                embedding_provider="bedrock",
                embedding_model="amazon.titan-embed-text-v2:0",
            ),
            enable_redis_cache=False,
        )

        assert config.semantic_prediction.embedding_provider == "bedrock"
        assert config.semantic_prediction.embedding_model == "amazon.titan-embed-text-v2:0"

    def test_bedrock_ai_config_validation_failure(self):
        """Test Bedrock AI validation fails without model ID."""
        with pytest.raises(ValueError, match="semantic_prediction.embedding_model is required"):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_s3_bucket="my-bucket",
                results_s3_bucket="test-results-bucket",
                semantic_prediction=SemanticPredictionConfig(embedding_provider="bedrock", embedding_model=""),
                enable_redis_cache=False,
            )

    def test_sagemaker_ai_config_validation_success(self):
        """Test successful SageMaker AI configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            semantic_prediction=SemanticPredictionConfig(embedding_provider="sagemaker"),
            sagemaker_endpoint_name="my-endpoint",
            enable_redis_cache=False,
        )

        assert config.semantic_prediction.embedding_provider == "sagemaker"
        assert config.sagemaker_endpoint_name == "my-endpoint"

    def test_sagemaker_ai_config_validation_failure(self):
        """Test SageMaker AI validation fails without endpoint name."""
        with pytest.raises(
            ValueError,
            match="sagemaker_endpoint_name is required when embedding_provider is 'sagemaker'",
        ):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_s3_bucket="my-bucket",
                results_s3_bucket="test-results-bucket",
                semantic_prediction=SemanticPredictionConfig(embedding_provider="sagemaker"),
                enable_redis_cache=False,
            )

    def test_dynamodb_job_status_saver_validation_success(self):
        """Test successful DynamoDB job status saver configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            job_status_saver_type="dynamodb",
            job_status_table_name="my-jobs-table",
            enable_redis_cache=False,
        )

        assert config.job_status_saver_type == "dynamodb"
        assert config.job_status_table_name == "my-jobs-table"

    def test_dynamodb_job_status_saver_validation_failure(self):
        """Test DynamoDB job status saver validation fails without table name."""
        with pytest.raises(
            ValueError,
            match="job_status_table_name is required when job_status_saver_type is 'dynamodb'",
        ):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_s3_bucket="my-bucket",
                results_s3_bucket="test-results-bucket",
                job_status_saver_type="dynamodb",
                job_status_table_name=None,
                enable_redis_cache=False,
            )

    def test_local_job_status_saver_validation_success(self):
        """Test successful local job status saver configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            job_status_saver_type="local",
            job_status_storage_dir="/tmp/jobs",
            enable_redis_cache=False,
        )

        assert config.job_status_saver_type == "local"
        assert config.job_status_storage_dir == "/tmp/jobs"

    def test_local_job_status_saver_validation_failure(self):
        """Test local job status saver validation fails without storage directory."""
        with pytest.raises(
            ValueError,
            match="job_status_storage_dir is required when job_status_saver_type is 'local'",
        ):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_s3_bucket="my-bucket",
                results_s3_bucket="test-results-bucket",
                job_status_saver_type="local",
                job_status_storage_dir=None,
                enable_redis_cache=False,
            )

    def test_s3_result_saver_validation_success(self):
        """Test successful S3 result saver configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            result_saver_type="s3",
            results_s3_bucket="my-results-bucket",
            enable_redis_cache=False,
        )

        assert config.result_saver_type == "s3"
        assert config.results_s3_bucket == "my-results-bucket"

    def test_s3_result_saver_validation_failure(self):
        """Test S3 result saver validation fails without bucket name."""
        with pytest.raises(
            ValueError,
            match="results_s3_bucket is required when result_saver_type is 's3'",
        ):
            ProcessorConfig(
                schema_directory="/path/to/schemas",
                session_s3_bucket="my-bucket",
                result_saver_type="s3",
                results_s3_bucket=None,
                enable_redis_cache=False,
            )

    def test_local_result_saver_validation_success(self):
        """Test successful local result saver configuration."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            result_saver_type="local",
            results_local_dir="/tmp/results",
            enable_redis_cache=False,
        )

        assert config.result_saver_type == "local"
        assert config.results_local_dir == "/tmp/results"

    def test_data_saver_defaults(self):
        """Test data saver configuration defaults."""
        config = ProcessorConfig(
            schema_directory="/path/to/schemas",
            session_s3_bucket="my-bucket",
            results_s3_bucket="test-results-bucket",
            enable_redis_cache=False,
        )

        # Job status saver defaults
        assert config.job_status_saver_type == "dynamodb"
        assert config.job_status_table_name == "metadata-jobs"
        assert config.job_status_storage_dir == "./data/job_status"

        # Result saver defaults
        assert config.result_saver_type == "s3"
        assert config.results_s3_bucket == "test-results-bucket"
        assert config.results_s3_prefix == "validation-results/"
        assert config.results_local_dir == "./data/validation-results"

    def test_custom_values(self):
        """Test ProcessorConfig with custom values."""
        config = ProcessorConfig(
            schema_directory="/custom/schemas",
            aws_region="us-west-2",
            aws_profile="my-profile",
            session_saver_type="file",
            file_session_directory="/custom/sessions",
            result_saver_type="local",  # Use local to avoid needing S3 bucket
            results_local_dir="/custom/results",
            enable_redis_cache=False,
            enable_memory_cache=True,
            memory_cache_max_size=5000,
            embedding_provider="sagemaker",
            sagemaker_endpoint_name="custom-endpoint",
            max_retries=5,
            timeout_seconds=600,
            cosine_similarity_threshold=0.9,
        )

        assert config.schema_directory == "/custom/schemas"
        assert config.aws_region == "us-west-2"
        assert config.aws_profile == "my-profile"
        assert config.session_saver_type == "file"
        assert config.file_session_directory == "/custom/sessions"
        assert config.enable_redis_cache is False
        assert config.enable_memory_cache is True
        assert config.memory_cache_max_size == 5000
        assert config.embedding_provider == "sagemaker"
        assert config.sagemaker_endpoint_name == "custom-endpoint"
        assert config.max_retries == 5
        assert config.timeout_seconds == 600
        assert config.cosine_similarity_threshold == 0.9


class TestDeepMergeDicts:
    """Test deep_merge_dicts utility function."""

    def test_simple_merge(self):
        """Test simple dictionary merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = deep_merge_dicts(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test nested dictionary merge."""
        base = {
            "level1": {"a": 1, "b": 2, "level2": {"x": 10, "y": 20}},
            "other": "value",
        }
        override = {"level1": {"b": 3, "c": 4, "level2": {"y": 30, "z": 40}}}

        result = deep_merge_dicts(base, override)

        expected = {
            "level1": {"a": 1, "b": 3, "c": 4, "level2": {"x": 10, "y": 30, "z": 40}},
            "other": "value",
        }

        assert result == expected

    def test_override_with_non_dict(self):
        """Test override with non-dictionary value."""
        base = {"a": {"nested": "value"}}
        override = {"a": "simple_value"}

        result = deep_merge_dicts(base, override)

        assert result == {"a": "simple_value"}

    def test_empty_dicts(self):
        """Test merge with empty dictionaries."""
        assert deep_merge_dicts({}, {}) == {}
        assert deep_merge_dicts({"a": 1}, {}) == {"a": 1}
        assert deep_merge_dicts({}, {"a": 1}) == {"a": 1}


class TestResolveRelativePaths:
    """Test resolve_relative_paths utility function."""

    def test_resolve_schema_directory(self):
        """Test resolving relative schema directory path."""
        config_dir = Path("/config")
        data = {"schema_directory": "schemas"}

        result = resolve_relative_paths(data, config_dir)

        assert result["schema_directory"] == "/config/schemas"

    def test_resolve_file_session_directory(self):
        """Test resolving relative file session directory path."""
        config_dir = Path("/config")
        data = {"file_session_directory": "../sessions"}

        result = resolve_relative_paths(data, config_dir)

        assert result["file_session_directory"] == "/sessions"

    def test_resolve_job_status_storage_dir(self):
        """Test resolving relative job status storage directory path."""
        config_dir = Path("/config")
        data = {"job_status_storage_dir": "job_status"}

        result = resolve_relative_paths(data, config_dir)

        assert result["job_status_storage_dir"] == "/config/job_status"

    def test_resolve_results_local_dir(self):
        """Test resolving relative results local directory path."""
        config_dir = Path("/config")
        data = {"results_local_dir": "results"}

        result = resolve_relative_paths(data, config_dir)

        assert result["results_local_dir"] == "/config/results"

    def test_absolute_paths_unchanged(self):
        """Test that absolute paths are not changed."""
        config_dir = Path("/config")
        data = {
            "schema_directory": "/absolute/schemas",
            "file_session_directory": "/absolute/sessions",
            "job_status_storage_dir": "/absolute/jobs",
            "results_local_dir": "/absolute/results",
        }

        result = resolve_relative_paths(data, config_dir)

        assert result["schema_directory"] == "/absolute/schemas"
        assert result["file_session_directory"] == "/absolute/sessions"
        assert result["job_status_storage_dir"] == "/absolute/jobs"
        assert result["results_local_dir"] == "/absolute/results"

    def test_none_values_unchanged(self):
        """Test that None values are not changed."""
        config_dir = Path("/config")
        data = {
            "schema_directory": None,
            "file_session_directory": None,
            "job_status_storage_dir": None,
            "results_local_dir": None,
        }

        result = resolve_relative_paths(data, config_dir)

        assert result["schema_directory"] is None
        assert result["file_session_directory"] is None
        assert result["job_status_storage_dir"] is None
        assert result["results_local_dir"] is None

    def test_other_fields_unchanged(self):
        """Test that non-path fields are unchanged."""
        config_dir = Path("/config")
        data = {
            "aws_region": "us-east-1",
            "enable_redis_cache": True,
            "schema_directory": "schemas",
            "job_status_storage_dir": "jobs",
            "results_local_dir": "results",
        }

        result = resolve_relative_paths(data, config_dir)

        assert result["aws_region"] == "us-east-1"
        assert result["enable_redis_cache"] is True
        assert result["schema_directory"] == "/config/schemas"
        assert result["job_status_storage_dir"] == "/config/jobs"
        assert result["results_local_dir"] == "/config/results"


class TestLoadProcessorSettings:
    """Test load_processor_settings function."""

    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "schema_directory": "schemas",
            "aws_region": "us-west-2",
            "session_saver_type": "s3",
            "session_s3_bucket": "test-bucket",
            "results_s3_bucket": "test-results-bucket",
            "enable_redis_cache": True,
            "redis_endpoint": "redis.example.com",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            settings = load_processor_settings(config_path)

            assert settings.schema_directory.endswith("schemas")
            assert settings.aws_region == "us-west-2"
            assert settings.session_saver_type == "s3"
            assert settings.session_s3_bucket == "test-bucket"
            assert settings.enable_redis_cache is True
            assert settings.redis_endpoint == "redis.example.com"
        finally:
            config_path.unlink()

    def test_load_with_relative_paths(self):
        """Test loading configuration with relative paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_path = temp_path / "config.yaml"
            config_data = {
                "schema_directory": "schemas",
                "session_saver_type": "file",
                "file_session_directory": "sessions",
                "result_saver_type": "local",
                "enable_redis_cache": False,
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            settings = load_processor_settings(config_path)

            # Use resolve() to get the canonical path for comparison
            expected_schema_dir = str((temp_path / "schemas").resolve())
            expected_session_dir = str((temp_path / "sessions").resolve())

            assert settings.schema_directory == expected_schema_dir
            assert settings.file_session_directory == expected_session_dir

    def test_load_with_overrides(self):
        """Test loading configuration with overrides."""
        config_data = {
            "schema_directory": "schemas",
            "aws_region": "us-west-2",
            "session_saver_type": "s3",
            "session_s3_bucket": "test-bucket",
            "results_s3_bucket": "test-results-bucket",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            override = {
                "aws_region": "eu-west-1",
                "max_retries": 5,
                "enable_redis_cache": False,
            }

            settings = load_processor_settings(config_path, override)

            assert settings.aws_region == "eu-west-1"  # Overridden
            assert settings.max_retries == 5  # Overridden
            assert settings.enable_redis_cache is False  # Overridden
            assert settings.session_s3_bucket == "test-bucket"  # From file
        finally:
            config_path.unlink()

    def test_load_nested_overrides(self):
        """Test loading configuration with nested overrides."""
        config_data = {
            "schema_directory": "schemas",
            "session_saver_type": "s3",
            "session_s3_bucket": "test-bucket",
            "results_s3_bucket": "test-results-bucket",
            "enable_redis_cache": False,
            "aws_region": "us-west-2",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            override = {"aws_region": "eu-west-1", "max_retries": 5}

            settings = load_processor_settings(config_path, override)

            # Check that overrides work correctly
            assert settings.session_s3_bucket == "test-bucket"  # From file
            assert settings.aws_region == "eu-west-1"  # Overridden
            assert settings.max_retries == 5  # Overridden
        finally:
            config_path.unlink()

    def test_load_without_config_file(self):
        """Test loading configuration without config file (overrides only)."""
        override = {
            "schema_directory": "/path/to/schemas",
            "session_saver_type": "file",
            "file_session_directory": "/tmp/sessions",
            "result_saver_type": "local",
            "aws_region": "us-west-2",
            "enable_redis_cache": False,
        }

        settings = load_processor_settings(override=override)

        assert settings.schema_directory == "/path/to/schemas"
        assert settings.session_saver_type == "file"
        assert settings.file_session_directory == "/tmp/sessions"
        assert settings.aws_region == "us-west-2"

    def test_load_nonexistent_file_error(self):
        """Test error when config file doesn't exist."""
        nonexistent_path = Path("/nonexistent/config.yaml")

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_processor_settings(nonexistent_path)

    def test_load_invalid_yaml_error(self):
        """Test error when YAML file is invalid."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError, match="Invalid YAML in config file"):
                load_processor_settings(config_path)
        finally:
            config_path.unlink()

    def test_load_validation_error(self):
        """Test error when configuration validation fails."""
        config_data = {
            "schema_directory": "schemas",
            "session_saver_type": "s3",
            "results_s3_bucket": "test-results-bucket",
            # Missing required session_s3_bucket for session manager
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_processor_settings(config_path)
        finally:
            config_path.unlink()

    def test_load_validation_error_with_overrides(self):
        """Test error when configuration validation fails with overrides only."""
        override = {
            "schema_directory": "/path/to/schemas",
            "session_saver_type": "s3",
            "results_s3_bucket": "test-results-bucket",
            # Missing required session_s3_bucket for session manager
        }

        with pytest.raises(ValueError, match="Configuration validation failed with overrides"):
            load_processor_settings(override=override)

    def test_load_empty_yaml_file(self):
        """Test loading empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            config_path = Path(f.name)

        try:
            override = {
                "schema_directory": "/path/to/schemas",
                "session_saver_type": "file",
                "file_session_directory": "/tmp/sessions",
                "result_saver_type": "local",
                "enable_redis_cache": False,
            }

            settings = load_processor_settings(config_path, override)

            assert settings.schema_directory == "/path/to/schemas"
            assert settings.session_saver_type == "file"
        finally:
            config_path.unlink()
