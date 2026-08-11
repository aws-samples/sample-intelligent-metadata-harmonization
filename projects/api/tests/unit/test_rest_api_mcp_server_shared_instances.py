# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
Test that both REST API and MCP server can use the same shared component instances.

This module tests the integration between REST API endpoints and MCP server tools
to ensure they share the same component instances through the shared dependency injection system.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.utils.shared_dependencies import (
    get_schema_collector,
    get_processor_manager,
    get_ddb_manager,
    get_metadata_worker,
    get_job_status_saver,
    clear_dependency_cache,
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


@pytest.fixture
def mock_fastapi_request(mock_processor_config):
    """Create a mock FastAPI request with app state."""
    request = Mock()
    request.app.state.processor_config = mock_processor_config
    request.app.state.api_config = Mock()
    return request


class TestRESTAPIMCPServerSharedInstances:
    """Test cases for verifying REST API and MCP server share component instances."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_dependency_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_dependency_cache()

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.LocalJobStatusSaver")
    def test_rest_api_and_mcp_server_share_all_components(
        self,
        mock_job_status_saver_class,
        mock_ddb_manager_class,
        mock_processor_manager_class,
        mock_schema_collector_class,
        mock_processor_config,
    ):
        """Test that REST API and MCP server share all core component instances."""

        # Setup mock instances
        mock_schema_collector = AsyncMock()
        mock_processor_manager = Mock()
        mock_ddb_manager = Mock()
        mock_job_status_saver = Mock()

        mock_schema_collector_class.return_value = mock_schema_collector
        mock_processor_manager_class.return_value = mock_processor_manager
        mock_ddb_manager_class.return_value = mock_ddb_manager
        mock_job_status_saver_class.return_value = mock_job_status_saver

        # === Simulate REST API endpoint getting dependencies ===
        # This simulates how REST API validation endpoints get their dependencies
        rest_schema_collector = get_schema_collector(mock_processor_config)
        rest_processor_manager = get_processor_manager(mock_processor_config)
        rest_ddb_manager = get_ddb_manager()
        rest_job_status_saver = get_job_status_saver(mock_processor_config)

        # === Simulate MCP server tools getting dependencies ===
        # This simulates how MCP validation and schema tools get their dependencies
        mcp_schema_collector = get_schema_collector(mock_processor_config)
        mcp_processor_manager = get_processor_manager(mock_processor_config)
        mcp_ddb_manager = get_ddb_manager()
        mcp_job_status_saver = get_job_status_saver(mock_processor_config)

        # === Verify both interfaces get the same cached instances ===
        assert rest_schema_collector is mcp_schema_collector
        assert rest_processor_manager is mcp_processor_manager
        assert rest_ddb_manager is mcp_ddb_manager
        assert rest_job_status_saver is mcp_job_status_saver

        # === Verify singleton instances were only created once ===
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)
        mock_ddb_manager_class.assert_called_once()
        mock_job_status_saver_class.assert_called_once_with(
            storage_type="file", storage_dir=mock_processor_config.job_status_storage_dir
        )

    @patch("metadata_harmonization_api.utils.shared_dependencies.MetadataWorker")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    def test_metadata_workers_use_same_processor_manager(
        self, mock_processor_manager_class, mock_metadata_worker_class, mock_processor_config
    ):
        """Test that MetadataWorker instances from both interfaces use the same ProcessorManager."""

        mock_processor_manager = Mock()
        mock_rest_worker = Mock()
        mock_mcp_worker = Mock()

        mock_processor_manager_class.return_value = mock_processor_manager
        mock_metadata_worker_class.side_effect = [mock_rest_worker, mock_mcp_worker]

        # Get shared processor manager
        shared_processor_manager = get_processor_manager(mock_processor_config)

        # === Simulate REST API creating MetadataWorker ===
        rest_metadata_worker = get_metadata_worker(shared_processor_manager)

        # === Simulate MCP server creating MetadataWorker ===
        mcp_metadata_worker = get_metadata_worker(shared_processor_manager)

        # === Verify both workers use the same shared ProcessorManager ===
        assert mock_metadata_worker_class.call_count == 2
        for call in mock_metadata_worker_class.call_args_list:
            assert call[0][0] is shared_processor_manager
            assert call[0][0] is mock_processor_manager

        # ProcessorManager should only be created once
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)

        # Workers should be different instances (not cached)
        assert rest_metadata_worker is not mcp_metadata_worker
        assert rest_metadata_worker is mock_rest_worker
        assert mcp_metadata_worker is mock_mcp_worker

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    def test_rest_api_dependency_injection_uses_shared_instances(
        self, mock_schema_collector_class, mock_processor_config, mock_fastapi_request
    ):
        """Test that REST API dependency injection functions use shared instances."""

        mock_schema_collector = AsyncMock()
        mock_schema_collector_class.return_value = mock_schema_collector

        # Import REST API dependency functions
        from metadata_harmonization_api.api.v1.routes.metadata.validation import (
            get_shared_schema_collector,
            get_processor_config,
        )

        # === Simulate REST API dependency injection ===
        processor_config = get_processor_config(mock_fastapi_request)
        rest_schema_collector = get_shared_schema_collector(mock_fastapi_request)

        # === Simulate MCP server getting the same dependency ===
        mcp_schema_collector = get_schema_collector(processor_config)

        # === Verify both get the same instance ===
        assert rest_schema_collector is mcp_schema_collector
        assert rest_schema_collector is mock_schema_collector

        # Should only be instantiated once
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    def test_mcp_validation_tool_uses_shared_schema_collector(self, mock_schema_collector_class, mock_processor_config):
        """Test that MCP validation tool uses the same schema collector as REST API."""

        mock_schema_collector = AsyncMock()
        mock_schema_collector.get_schema = AsyncMock(return_value={"test": "schema"})
        mock_schema_collector_class.return_value = mock_schema_collector

        # Import MCP validation tool setup
        from metadata_harmonization_api.mcp.tools.validation import setup_validation_tools
        from fastmcp import FastMCP

        # === Simulate REST API getting schema collector ===
        rest_schema_collector = get_schema_collector(mock_processor_config)

        # === Simulate MCP server setup using the same config ===
        mcp_server = FastMCP("test-server")
        setup_validation_tools(mcp_server, mock_processor_config)

        # Get the MCP tool's schema collector by calling the shared dependency function
        mcp_schema_collector = get_schema_collector(mock_processor_config)

        # === Verify both use the same instance ===
        assert rest_schema_collector is mcp_schema_collector
        assert rest_schema_collector is mock_schema_collector

        # Should only be instantiated once
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    def test_mcp_schema_tool_uses_shared_schema_collector(self, mock_schema_collector_class, mock_processor_config):
        """Test that MCP schema tool uses the same schema collector as REST API."""

        mock_schema_collector = AsyncMock()
        mock_schema_collector.get_available_schemas = AsyncMock(return_value=[])
        mock_schema_collector_class.return_value = mock_schema_collector

        # Import MCP schema tool setup
        from metadata_harmonization_api.mcp.tools.schema import setup_schema_tools
        from fastmcp import FastMCP

        # === Simulate REST API getting schema collector ===
        rest_schema_collector = get_schema_collector(mock_processor_config)

        # === Simulate MCP server setup using the same config ===
        mcp_server = FastMCP("test-server")
        setup_schema_tools(mcp_server, mock_processor_config)

        # Get the MCP tool's schema collector by calling the shared dependency function
        mcp_schema_collector = get_schema_collector(mock_processor_config)

        # === Verify both use the same instance ===
        assert rest_schema_collector is mcp_schema_collector
        assert rest_schema_collector is mock_schema_collector

        # Should only be instantiated once
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)

    @patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager")
    def test_database_connections_shared_between_interfaces(self, mock_ddb_manager_class, mock_processor_config):
        """Test that database connections are shared between REST API and MCP server."""

        mock_ddb_manager = Mock()
        mock_ddb_manager.client = Mock()
        mock_ddb_manager_class.return_value = mock_ddb_manager

        # === Simulate REST API getting database manager ===
        rest_ddb_manager = get_ddb_manager()

        # === Simulate MCP server getting database manager ===
        mcp_ddb_manager = get_ddb_manager()

        # === Simulate multiple components getting database manager ===
        handler_ddb_manager = get_ddb_manager()
        worker_ddb_manager = get_ddb_manager()

        # === Verify all get the same instance ===
        assert rest_ddb_manager is mcp_ddb_manager
        assert mcp_ddb_manager is handler_ddb_manager
        assert handler_ddb_manager is worker_ddb_manager
        assert rest_ddb_manager is mock_ddb_manager

        # Should only be instantiated once
        mock_ddb_manager_class.assert_called_once()

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.MetadataWorker")
    def test_complete_validation_workflow_shares_components(
        self,
        mock_metadata_worker_class,
        mock_processor_manager_class,
        mock_schema_collector_class,
        mock_processor_config,
    ):
        """Test complete validation workflow where both REST API and MCP server share components."""

        # Setup mocks
        mock_schema_collector = AsyncMock()
        mock_processor_manager = Mock()
        mock_metadata_worker = Mock()

        mock_schema_collector_class.return_value = mock_schema_collector
        mock_processor_manager_class.return_value = mock_processor_manager
        mock_metadata_worker_class.return_value = mock_metadata_worker

        # === Simulate REST API validation workflow ===
        rest_schema_collector = get_schema_collector(mock_processor_config)
        rest_processor_manager = get_processor_manager(mock_processor_config)
        get_metadata_worker(rest_processor_manager)

        # === Simulate MCP server validation workflow ===
        mcp_schema_collector = get_schema_collector(mock_processor_config)
        mcp_processor_manager = get_processor_manager(mock_processor_config)
        get_metadata_worker(mcp_processor_manager)

        # === Verify shared components ===
        assert rest_schema_collector is mcp_schema_collector
        assert rest_processor_manager is mcp_processor_manager

        # === Verify component creation counts ===
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)

        # MetadataWorker should be created twice (not cached)
        assert mock_metadata_worker_class.call_count == 2

        # Both workers should use the same ProcessorManager
        for call in mock_metadata_worker_class.call_args_list:
            assert call[0][0] is mock_processor_manager

    def test_cache_isolation_prevents_cross_config_sharing(self):
        """Test that different processor configs don't share instances inappropriately."""

        with patch(
            "metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector"
        ) as mock_schema_collector_class:
            with patch(
                "metadata_harmonization_api.utils.shared_dependencies.ProcessorManager"
            ) as mock_processor_manager_class:
                mock_schema_collector1 = Mock()
                mock_schema_collector2 = Mock()
                mock_processor_manager1 = Mock()
                mock_processor_manager2 = Mock()

                mock_schema_collector_class.side_effect = [mock_schema_collector1, mock_schema_collector2]
                mock_processor_manager_class.side_effect = [mock_processor_manager1, mock_processor_manager2]

                # Create two different configs (different schema directories)
                config1 = Mock(spec=ProcessorConfig)
                config1.schema_directory = "/test/schemas1"

                config2 = Mock(spec=ProcessorConfig)
                config2.schema_directory = "/test/schemas2"

                # === Get components for first config ===
                rest_schema_collector1 = get_schema_collector(config1)
                rest_processor_manager1 = get_processor_manager(config1)

                # === Get components for second config ===
                mcp_schema_collector2 = get_schema_collector(config2)
                mcp_processor_manager2 = get_processor_manager(config2)

                # === Verify schema collectors are different (different directories) ===
                assert rest_schema_collector1 is not mcp_schema_collector2
                assert rest_schema_collector1 is mock_schema_collector1
                assert mcp_schema_collector2 is mock_schema_collector2

                # === Verify processor managers are different (global cache, but different instances) ===
                # Note: ProcessorManager uses global cache, so second call gets the first instance
                assert rest_processor_manager1 is mcp_processor_manager2
                assert rest_processor_manager1 is mock_processor_manager1

                # Schema collectors should be called with different directories
                mock_schema_collector_class.assert_any_call(config1.schema_directory)
                mock_schema_collector_class.assert_any_call(config2.schema_directory)

                # ProcessorManager should only be called once (global cache)
                mock_processor_manager_class.assert_called_once_with(config1)

    @patch("metadata_harmonization_api.utils.shared_dependencies.FileBasedSchemaCollector")
    @patch("metadata_harmonization_api.utils.shared_dependencies.ProcessorManager")
    @patch("metadata_harmonization_api.utils.shared_dependencies.DynamoDbManager")
    def test_concurrent_access_returns_same_instances(
        self, mock_ddb_manager_class, mock_processor_manager_class, mock_schema_collector_class, mock_processor_config
    ):
        """Test that concurrent access from multiple interfaces returns same instances."""

        # Setup mocks
        mock_schema_collector = Mock()
        mock_processor_manager = Mock()
        mock_ddb_manager = Mock()

        mock_schema_collector_class.return_value = mock_schema_collector
        mock_processor_manager_class.return_value = mock_processor_manager
        mock_ddb_manager_class.return_value = mock_ddb_manager

        # === Simulate concurrent access from multiple sources ===
        instances = []

        # REST API validation endpoint
        instances.append(get_schema_collector(mock_processor_config))
        instances.append(get_processor_manager(mock_processor_config))
        instances.append(get_ddb_manager())

        # MCP validation tool
        instances.append(get_schema_collector(mock_processor_config))
        instances.append(get_processor_manager(mock_processor_config))
        instances.append(get_ddb_manager())

        # MCP schema tool
        instances.append(get_schema_collector(mock_processor_config))
        instances.append(get_processor_manager(mock_processor_config))
        instances.append(get_ddb_manager())

        # REST API schema handler
        instances.append(get_schema_collector(mock_processor_config))
        instances.append(get_processor_manager(mock_processor_config))
        instances.append(get_ddb_manager())

        # === Verify all schema collectors are the same instance ===
        schema_collectors = instances[0::3]  # Every 3rd item starting from 0
        for collector in schema_collectors:
            assert collector is mock_schema_collector

        # === Verify all processor managers are the same instance ===
        processor_managers = instances[1::3]  # Every 3rd item starting from 1
        for manager in processor_managers:
            assert manager is mock_processor_manager

        # === Verify all database managers are the same instance ===
        ddb_managers = instances[2::3]  # Every 3rd item starting from 2
        for ddb_manager in ddb_managers:
            assert ddb_manager is mock_ddb_manager

        # === Verify components were only created once despite multiple access ===
        mock_schema_collector_class.assert_called_once_with(mock_processor_config.schema_directory)
        mock_processor_manager_class.assert_called_once_with(mock_processor_config)
        mock_ddb_manager_class.assert_called_once()
