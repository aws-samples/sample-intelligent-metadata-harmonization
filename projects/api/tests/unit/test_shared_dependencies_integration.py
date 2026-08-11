# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Integration tests for shared dependency injection system.

This module tests that REST API endpoints and MCP server tools can
successfully use the same shared component instances.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.utils.shared_dependencies import (
    get_schema_collector,
    get_processor_manager,
    get_ddb_manager,
    get_metadata_worker,
    clear_dependency_cache,
)


@pytest.fixture
def mock_processor_config():
    """Create a mock ProcessorConfig for testing."""
    config = Mock(spec=ProcessorConfig)
    config.schema_directory = "/test/schemas"
    config.local_development_mode = True
    config.job_status_saver_type = "local"
    config.result_saver_type = "local"
    config.session_saver_type = "file"
    return config


class TestSharedDependenciesIntegration:
    """Integration test cases for shared dependency injection system."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_dependency_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_dependency_cache()

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.MetadataWorker")
    def test_rest_api_and_mcp_server_integration(
        self,
        mock_metadata_worker_class,
        mock_ddb_manager_class,
        mock_processor_manager_class,
        mock_schema_collector_class,
        mock_processor_config,
    ):
        """Test that REST API and MCP server can use shared dependencies in realistic scenario."""

        # Setup mock instances
        mock_schema_collector = Mock()
        mock_processor_manager = Mock()
        mock_ddb_manager = Mock()
        mock_metadata_worker1 = Mock()
        mock_metadata_worker2 = Mock()

        mock_schema_collector_class.return_value = mock_schema_collector
        mock_processor_manager_class.return_value = mock_processor_manager
        mock_ddb_manager_class.return_value = mock_ddb_manager
        mock_metadata_worker_class.side_effect = [mock_metadata_worker1, mock_metadata_worker2]

        # Simulate REST API validation endpoint getting dependencies
        rest_schema_collector = get_schema_collector(mock_processor_config)
        rest_processor_manager = get_processor_manager(mock_processor_config)
        rest_ddb_manager = get_ddb_manager()
        rest_metadata_worker = get_metadata_worker(rest_processor_manager)

        # Simulate MCP server validation tool getting dependencies
        mcp_schema_collector = get_schema_collector(mock_processor_config)
        mcp_processor_manager = get_processor_manager(mock_processor_config)
        mcp_ddb_manager = get_ddb_manager()
        mcp_metadata_worker = get_metadata_worker(mcp_processor_manager)

        # Verify both interfaces get the same cached instances
        assert rest_schema_collector is mcp_schema_collector
        assert rest_processor_manager is mcp_processor_manager
        assert rest_ddb_manager is mcp_ddb_manager

        # MetadataWorker should be different instances (not cached)
        assert rest_metadata_worker is not mcp_metadata_worker

        # Verify singleton instances were only created once
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)
        mock_ddb_manager_class.assert_called_once()

        # MetadataWorker should be created twice (not cached)
        assert mock_metadata_worker_class.call_count == 2

        # Both MetadataWorker instances should use the same ProcessorManager
        for call in mock_metadata_worker_class.call_args_list:
            assert call[0][0] is mock_processor_manager

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    def test_rest_api_validation_handler_usage(self, mock_schema_collector_class, mock_processor_config):
        """Test that REST API validation handler can use shared dependencies."""
        mock_schema_collector = AsyncMock()
        mock_schema_collector_class.return_value = mock_schema_collector

        # Simulate REST API validation handler getting schema collector
        from metadata_harmonization_api.api.v1.routes.metadata.validation import get_shared_schema_collector

        # Create mock request with processor config
        mock_request = Mock()
        mock_request.app.state.processor_config = mock_processor_config

        # Get schema collector through REST API dependency
        schema_collector = get_shared_schema_collector(mock_request)

        # Verify it's the same instance as direct access
        direct_schema_collector = get_schema_collector(mock_processor_config)

        assert schema_collector is direct_schema_collector
        assert schema_collector is mock_schema_collector

        # Should only be instantiated once
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)

    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    def test_mcp_server_tool_usage(self, mock_processor_manager_class, mock_processor_config):
        """Test that MCP server tools can use shared dependencies."""
        mock_processor_manager = Mock()
        mock_processor_manager_class.return_value = mock_processor_manager

        # Simulate MCP server tool getting processor manager
        mcp_processor_manager = get_processor_manager(mock_processor_config)

        # Simulate REST API also getting processor manager
        rest_processor_manager = get_processor_manager(mock_processor_config)

        # Both should get the same instance
        assert mcp_processor_manager is rest_processor_manager
        assert mcp_processor_manager is mock_processor_manager

        # Should only be instantiated once
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)

    @patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager")
    def test_database_connection_sharing(self, mock_ddb_manager_class):
        """Test that database connections are shared between REST API and MCP server."""
        mock_ddb_manager = Mock()
        mock_ddb_manager_class.return_value = mock_ddb_manager

        # Simulate multiple components getting DDB manager
        rest_ddb_manager = get_ddb_manager()
        mcp_ddb_manager = get_ddb_manager()
        handler_ddb_manager = get_ddb_manager()

        # All should get the same instance
        assert rest_ddb_manager is mcp_ddb_manager
        assert mcp_ddb_manager is handler_ddb_manager
        assert rest_ddb_manager is mock_ddb_manager

        # Should only be instantiated once
        mock_ddb_manager_class.assert_called_once()

    @patch("metadata_harmonization_api.utils.shared_dependencies.MetadataWorker")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    def test_metadata_worker_uses_shared_processor_manager(
        self, mock_processor_manager_class, mock_metadata_worker_class, mock_processor_config
    ):
        """Test that MetadataWorker instances use the shared ProcessorManager."""
        mock_processor_manager = Mock()
        mock_metadata_worker = Mock()

        mock_processor_manager_class.return_value = mock_processor_manager
        mock_metadata_worker_class.return_value = mock_metadata_worker

        # Get shared processor manager
        shared_processor_manager = get_processor_manager(mock_processor_config)

        # Create MetadataWorker instances (should use shared ProcessorManager)
        get_metadata_worker(shared_processor_manager)
        get_metadata_worker(shared_processor_manager)

        # Both workers should be created with the same shared ProcessorManager
        assert mock_metadata_worker_class.call_count == 2
        for call in mock_metadata_worker_class.call_args_list:
            assert call[0][0] is shared_processor_manager
            assert call[0][0] is mock_processor_manager

        # ProcessorManager should only be created once
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)

    def test_cache_isolation_between_different_configs(self):
        """Test that different processor configs get different instances."""
        with patch(
            "metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector"
        ) as mock_schema_collector_class:
            mock_instance1 = Mock()
            mock_instance2 = Mock()
            mock_schema_collector_class.side_effect = [mock_instance1, mock_instance2]

            # Create two different configs
            config1 = Mock(spec=ProcessorConfig)
            config1.schema_directory = "/test/schemas1"

            config2 = Mock(spec=ProcessorConfig)
            config2.schema_directory = "/test/schemas2"

            # Get schema collectors for different configs
            collector1 = get_schema_collector(config1)
            collector2 = get_schema_collector(config2)

            # Should get different instances for different configs
            assert collector1 is not collector2
            assert collector1 is mock_instance1
            assert collector2 is mock_instance2

            # Should be called twice with different schema directories
            assert mock_schema_collector_class.call_count == 2
            mock_schema_collector_class.assert_any_call(config1.schema_directory)
            mock_schema_collector_class.assert_any_call(config2.schema_directory)
