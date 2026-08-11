# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Tests for shared dependency injection system.

This module tests that the shared dependency injection system provides
consistent singleton instances for both REST API and MCP server usage.
"""

import pytest
from unittest.mock import Mock, patch

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.utils.shared_dependencies import (
    get_schema_collector,
    get_processor_manager,
    get_ddb_manager,
    get_metadata_worker,
    get_core_dependencies,
    clear_dependency_cache,
    get_cache_info,
)


@pytest.fixture
def mock_processor_config():
    """Create a mock ProcessorConfig for testing."""
    config = Mock(spec=ProcessorConfig)
    config.schema_directory = "/test/schemas"
    config.local_development_mode = True
    config.job_status_saver_type = "local"
    config.job_status_storage_dir = "/test/job_status"
    config.result_saver_type = "local"
    config.session_saver_type = "file"
    return config


class TestSharedDependencies:
    """Test cases for shared dependency injection system."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_dependency_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_dependency_cache()

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    def test_get_schema_collector_singleton(self, mock_schema_collector_class, mock_processor_config):
        """Test that get_schema_collector returns the same instance for same config."""
        mock_instance = Mock()
        mock_schema_collector_class.return_value = mock_instance

        # First call should create instance
        collector1 = get_schema_collector(mock_processor_config)

        # Second call should return same instance (cached)
        collector2 = get_schema_collector(mock_processor_config)

        # Should be the same instance
        assert collector1 is collector2
        assert collector1 is mock_instance

        # FileBasedSchemaCollector should only be instantiated once with schema_directory
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)

    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    def test_get_processor_manager_singleton(self, mock_processor_manager_class, mock_processor_config):
        """Test that get_processor_manager returns the same instance for same config."""
        mock_instance = Mock()
        mock_processor_manager_class.return_value = mock_instance

        # First call should create instance
        manager1 = get_processor_manager(mock_processor_config)

        # Second call should return same instance (cached)
        manager2 = get_processor_manager(mock_processor_config)

        # Should be the same instance
        assert manager1 is manager2
        assert manager1 is mock_instance

        # ProcessorManager should only be instantiated once
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)

    @patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager")
    def test_get_ddb_manager_singleton(self, mock_ddb_manager_class):
        """Test that get_ddb_manager returns the same instance."""
        mock_instance = Mock()
        mock_ddb_manager_class.return_value = mock_instance

        # First call should create instance
        ddb1 = get_ddb_manager()

        # Second call should return same instance (cached)
        ddb2 = get_ddb_manager()

        # Should be the same instance
        assert ddb1 is ddb2
        assert ddb1 is mock_instance

        # DynamoDbManager should only be instantiated once
        mock_ddb_manager_class.assert_called_once()

    @patch("metadata_harmonization_api.utils.shared_dependencies.MetadataWorker")
    def test_get_metadata_worker_not_cached(self, mock_metadata_worker_class, mock_processor_config):
        """Test that get_metadata_worker creates new instances (not cached)."""
        mock_instance1 = Mock()
        mock_instance2 = Mock()
        mock_metadata_worker_class.side_effect = [mock_instance1, mock_instance2]

        mock_processor_manager = Mock()

        # First call should create instance
        worker1 = get_metadata_worker(mock_processor_manager)

        # Second call should create new instance (not cached)
        worker2 = get_metadata_worker(mock_processor_manager)

        # Should be different instances
        assert worker1 is not worker2
        assert worker1 is mock_instance1
        assert worker2 is mock_instance2

        # MetadataWorker should be instantiated twice
        assert mock_metadata_worker_class.call_count == 2

    @patch("metadata_harmonization_api.utils.shared_dependencies.MetadataWorker")
    @patch("metadata_harmonization_api.utils.shared_dependencies.LocalJobStatusSaver")
    @patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    def test_get_core_dependencies(
        self,
        mock_schema_collector_class,
        mock_processor_manager_class,
        mock_ddb_manager_class,
        mock_job_status_saver_class,
        mock_metadata_worker_class,
        mock_processor_config,
    ):
        """Test that get_core_dependencies returns all dependencies correctly."""
        # Setup mocks
        mock_schema_collector = Mock()
        mock_processor_manager = Mock()
        mock_ddb_manager = Mock()
        mock_job_status_saver = Mock()
        mock_metadata_worker = Mock()

        mock_schema_collector_class.return_value = mock_schema_collector
        mock_processor_manager_class.return_value = mock_processor_manager
        mock_ddb_manager_class.return_value = mock_ddb_manager
        mock_job_status_saver_class.return_value = mock_job_status_saver
        mock_metadata_worker_class.return_value = mock_metadata_worker

        # Get all dependencies
        schema_collector, processor_manager, ddb_manager, job_status_saver, metadata_worker = get_core_dependencies(
            mock_processor_config
        )

        # Verify all dependencies are returned
        assert schema_collector is mock_schema_collector
        assert processor_manager is mock_processor_manager
        assert ddb_manager is mock_ddb_manager
        assert job_status_saver is mock_job_status_saver
        assert metadata_worker is mock_metadata_worker

        # Verify correct instantiation
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)
        mock_ddb_manager_class.assert_called_once()
        mock_job_status_saver_class.assert_called_once_with(
            storage_type="file", storage_dir=mock_processor_config.job_status_storage_dir
        )
        mock_metadata_worker_class.assert_called_once_with(mock_processor_manager)

    def test_clear_dependency_cache(self, mock_processor_config):
        """Test that clear_dependency_cache clears all cached instances."""
        with patch(
            "metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector"
        ) as mock_schema_collector_class:
            mock_instance1 = Mock()
            mock_instance2 = Mock()
            mock_schema_collector_class.side_effect = [mock_instance1, mock_instance2]

            # Get instance (should be cached)
            collector1 = get_schema_collector(mock_processor_config)

            # Clear cache
            clear_dependency_cache()

            # Get instance again (should create new instance)
            collector2 = get_schema_collector(mock_processor_config)

            # Should be different instances
            assert collector1 is not collector2
            assert collector1 is mock_instance1
            assert collector2 is mock_instance2

            # Should have been called twice
            assert mock_schema_collector_class.call_count == 2

    def test_get_cache_info(self, mock_processor_config):
        """Test that get_cache_info returns cache statistics."""
        with patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector"):
            with patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager"):
                with patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager"):
                    # Get some instances to populate cache
                    get_schema_collector(mock_processor_config)
                    get_processor_manager(mock_processor_config)
                    get_ddb_manager()

                    # Get cache info
                    cache_info = get_cache_info()

                    # Verify structure
                    assert isinstance(cache_info, dict)
                    assert "schema_collector" in cache_info
                    assert "processor_manager" in cache_info
                    assert "ddb_manager" in cache_info

                    # Verify cache status is tracked
                    # schema_collector uses dictionary cache with schema directories
                    assert "cached_instances" in cache_info["schema_collector"]
                    assert "schema_directories" in cache_info["schema_collector"]
                    assert cache_info["schema_collector"]["cached_instances"] == 1
                    assert "/test/schemas" in cache_info["schema_collector"]["schema_directories"]

                    # processor_manager uses simple boolean cache
                    assert "cached" in cache_info["processor_manager"]
                    assert cache_info["processor_manager"]["cached"] is True

                    # ddb_manager uses lru_cache with detailed stats
                    assert "hits" in cache_info["ddb_manager"]
                    assert "misses" in cache_info["ddb_manager"]
                    assert "currsize" in cache_info["ddb_manager"]

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    def test_rest_api_and_mcp_server_share_instances(
        self, mock_processor_manager_class, mock_schema_collector_class, mock_processor_config
    ):
        """Test that REST API and MCP server would use the same shared instances."""
        mock_schema_collector = Mock()
        mock_processor_manager = Mock()

        mock_schema_collector_class.return_value = mock_schema_collector
        mock_processor_manager_class.return_value = mock_processor_manager

        # Simulate REST API getting dependencies
        rest_schema_collector = get_schema_collector(mock_processor_config)
        rest_processor_manager = get_processor_manager(mock_processor_config)

        # Simulate MCP server getting dependencies
        mcp_schema_collector = get_schema_collector(mock_processor_config)
        mcp_processor_manager = get_processor_manager(mock_processor_config)

        # Both should get the same instances
        assert rest_schema_collector is mcp_schema_collector
        assert rest_processor_manager is mcp_processor_manager

        # Components should only be instantiated once
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)
