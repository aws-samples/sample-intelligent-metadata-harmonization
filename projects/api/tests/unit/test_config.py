# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for configuration loading and environment detection."""

import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch
import pytest

from metadata_harmonization_api.config import MetadataConfig, deep_merge_dicts
from metadata_harmonization_api.services.processor_manager import detect_environment_overrides


class TestEnvironmentDetection:
    """Test cases for environment detection and configuration overrides."""

    def test_detect_environment_overrides_local(self):
        """Test environment detection for local development."""
        with patch.dict(os.environ, {"PROCESSOR_ENVIRONMENT": "local"}, clear=False):
            overrides = detect_environment_overrides()

            assert overrides["job_status_saver_type"] == "local"
            assert overrides["result_saver_type"] == "local"
            assert overrides["session_type"] == "file"
            assert overrides["local_development_mode"] is True
            assert overrides["enable_redis_cache"] is False
            assert overrides["enable_memory_cache"] is True

    def test_detect_environment_overrides_cloud(self):
        """Test environment detection for cloud deployment."""
        with patch.dict(os.environ, {"PROCESSOR_ENVIRONMENT": "cloud"}, clear=False):
            overrides = detect_environment_overrides()

            assert overrides["job_status_saver_type"] == "dynamodb"
            assert overrides["result_saver_type"] == "s3"
            assert overrides["session_type"] == "s3"
            # Cloud mode only sets storage backends; local_development_mode,
            # enable_redis_cache, enable_memory_cache are set via env var mappings
            assert "local_development_mode" not in overrides

    def test_detect_environment_overrides_cloud_with_env_vars(self):
        """Test cloud environment with specific environment variable overrides."""
        env_vars = {
            "PROCESSOR_ENVIRONMENT": "cloud",
            "PROCESSOR_JOB_STATUS_TABLE_NAME": "test-jobs-table",
            "PROCESSOR_RESULTS_S3_BUCKET": "test-results-bucket",
            "PROCESSOR_RESULTS_S3_PREFIX": "test-prefix/",
            "PROCESSOR_AWS_REGION": "us-west-2",
            "PROCESSOR_BEDROCK_MODEL_ID": "amazon.titan-embed-text-v1",
            "PROCESSOR_COSINE_SIMILARITY_THRESHOLD": "0.8",
            "PROCESSOR_ENABLE_REDIS_CACHE": "true",
            "PROCESSOR_REDIS_PORT": "6379",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            overrides = detect_environment_overrides()

            # Check cloud defaults
            assert overrides["job_status_saver_type"] == "dynamodb"
            assert overrides["result_saver_type"] == "s3"

            # Check environment variable overrides
            assert overrides["job_status_table_name"] == "test-jobs-table"
            assert overrides["results_s3_bucket"] == "test-results-bucket"
            assert overrides["results_s3_prefix"] == "test-prefix/"
            assert overrides["aws_region"] == "us-west-2"
            assert overrides["bedrock_model_id"] == "amazon.titan-embed-text-v1"
            assert overrides["cosine_similarity_threshold"] == 0.8  # Should be converted to float
            assert overrides["enable_redis_cache"] is True  # Should be converted to boolean
            assert overrides["redis_port"] == 6379  # Should be converted to int

    def test_detect_environment_overrides_default_local(self):
        """Test that local is the default environment."""
        # Remove PROCESSOR_ENVIRONMENT if it exists
        env_without_processor = {k: v for k, v in os.environ.items() if k != "PROCESSOR_ENVIRONMENT"}

        with patch.dict(os.environ, env_without_processor, clear=True):
            overrides = detect_environment_overrides()

            # Should default to local configuration
            assert overrides["job_status_saver_type"] == "local"
            assert overrides["result_saver_type"] == "local"
            assert overrides["local_development_mode"] is True


class TestConfigurationLoading:
    """Test cases for configuration file loading and validation."""

    def test_yaml_file_parsing(self):
        """Test basic YAML file parsing functionality."""
        config_data = {
            "api": {
                "max_file_size_mb": 100,
                "validation_timeout_seconds": 600,
                "enable_auth": True,
                "allowed_file_types": ["text/csv"],
            },
            "processor": {
                "schema_directory": "./test_schemas",
                "local_development_mode": True,
                "job_status_saver_type": "local",
                "result_saver_type": "local",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # Test that YAML can be loaded and parsed
            with open(config_path) as f:
                loaded_data = yaml.safe_load(f)

            assert loaded_data["api"]["max_file_size_mb"] == 100
            assert loaded_data["processor"]["schema_directory"] == "./test_schemas"

        finally:
            config_path.unlink()

    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML content."""
        invalid_yaml = "invalid: yaml: content: ["

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            config_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                with open(config_path) as f:
                    yaml.safe_load(f)
        finally:
            config_path.unlink()

    def test_environment_variable_parsing(self):
        """Test environment variable parsing and type conversion."""
        env_vars = {
            "API_MAX_FILE_SIZE_MB": "200",
            "API_ENABLE_AUTH": "true",
            "PROCESSOR_ENABLE_REDIS_CACHE": "false",
            "PROCESSOR_COSINE_SIMILARITY_THRESHOLD": "0.8",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Test boolean conversion
            assert os.getenv("API_ENABLE_AUTH").lower() == "true"
            assert os.getenv("PROCESSOR_ENABLE_REDIS_CACHE").lower() == "false"

            # Test numeric conversion
            assert int(os.getenv("API_MAX_FILE_SIZE_MB")) == 200
            assert float(os.getenv("PROCESSOR_COSINE_SIMILARITY_THRESHOLD")) == 0.8


class TestDeepMergeDicts:
    """Test cases for deep dictionary merging utility."""

    def test_deep_merge_dicts_simple(self):
        """Test simple dictionary merging."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = deep_merge_dicts(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_dicts_nested(self):
        """Test nested dictionary merging."""
        base = {"level1": {"a": 1, "b": 2, "level2": {"x": 10, "y": 20}}, "other": "value"}

        override = {"level1": {"b": 3, "c": 4, "level2": {"y": 30, "z": 40}}}

        result = deep_merge_dicts(base, override)

        expected = {"level1": {"a": 1, "b": 3, "c": 4, "level2": {"x": 10, "y": 30, "z": 40}}, "other": "value"}

        assert result == expected

    def test_deep_merge_dicts_override_with_non_dict(self):
        """Test merging when override value is not a dictionary."""
        base = {"config": {"setting1": "value1", "setting2": "value2"}}

        override = {"config": "simple_string"}

        result = deep_merge_dicts(base, override)

        # Override should completely replace the nested dict
        assert result == {"config": "simple_string"}

    def test_deep_merge_dicts_empty_dicts(self):
        """Test merging with empty dictionaries."""
        base = {"a": 1, "b": 2}
        override = {}

        result = deep_merge_dicts(base, override)
        assert result == base

        base = {}
        override = {"a": 1, "b": 2}

        result = deep_merge_dicts(base, override)
        assert result == override


class TestMetadataConfig:
    """Test cases for MetadataConfig validation."""

    def test_metadata_config_defaults(self):
        """Test MetadataConfig default values."""
        config = MetadataConfig()

        assert config.max_file_size_mb == 50
        assert config.allowed_file_types == ["text/csv", "application/csv"]
        assert config.validation_timeout_seconds == 300
        assert config.enable_auth is False
        assert config.mcp_enabled is True
        assert config.mcp_mount_path == "/mcp"

    def test_metadata_config_with_env_vars(self):
        """Test MetadataConfig with environment variable overrides."""
        env_vars = {
            "API_MAX_FILE_SIZE_MB": "100",
            "API_VALIDATION_TIMEOUT_SECONDS": "600",
            "API_ENABLE_AUTH": "true",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = MetadataConfig()

        assert config.max_file_size_mb == 100
        assert config.validation_timeout_seconds == 600
        assert config.enable_auth is True

    def test_metadata_config_field_types(self):
        """Test MetadataConfig field type validation."""
        # Test default configuration
        config = MetadataConfig()

        # Verify field types
        assert isinstance(config.max_file_size_mb, int)
        assert isinstance(config.validation_timeout_seconds, int)
        assert isinstance(config.enable_auth, bool)
        assert isinstance(config.allowed_file_types, list)
        assert isinstance(config.mcp_enabled, bool)
        assert isinstance(config.mcp_mount_path, str)
