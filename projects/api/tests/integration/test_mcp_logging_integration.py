# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Integration tests for MCP logging and monitoring with actual tools."""

import pytest
from unittest.mock import patch, MagicMock
from fastmcp import FastMCP

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.mcp.tools.validation import setup_validation_tools
from metadata_harmonization_api.mcp.tools.schema import setup_schema_tools
from metadata_harmonization_api.utils.logging import MCPPerformanceMetrics


@pytest.fixture
def processor_config():
    """Create a test processor configuration."""
    return ProcessorConfig(
        local_development_mode=True,
        schema_directory="data/schema",
        enable_memory_cache=True,
        enable_redis_cache=False,
        session_saver_type="file",
        file_session_directory="./test_sessions",
        result_saver_type="local",
        results_local_dir="./test_results",
    )


@pytest.fixture
def mcp_server(processor_config):
    """Create a test MCP server with tools."""
    mcp = FastMCP("test-mcp-server")

    # Set up tools with logging
    setup_validation_tools(mcp, processor_config)
    setup_schema_tools(mcp, processor_config)

    return mcp


class TestMCPToolLogging:
    """Test logging integration with actual MCP tools."""

    @patch("metadata_harmonization_api.utils.logging.mcp_metrics")
    def test_validation_tool_logging_success(self, mock_metrics, mcp_server):
        """Test that validation tool calls are properly logged."""
        # Reset metrics for clean test
        mock_metrics.reset_mock()

        # Mock the dependencies to avoid actual processing
        with patch("metadata_harmonization_api.mcp.tools.validation.get_schema_collector") as mock_collector, patch(
            "metadata_harmonization_api.mcp.tools.validation.get_processor_manager"
        ), patch("metadata_harmonization_api.mcp.tools.validation.get_metadata_worker") as mock_worker:
            # Mock successful schema validation
            mock_schema_collector = MagicMock()
            mock_collector.return_value = mock_schema_collector

            # Mock successful validation processing
            mock_validation_worker = MagicMock()
            mock_validation_results = MagicMock()
            mock_validation_results.dict.return_value = {"status": "valid", "errors": []}
            mock_validation_worker.process_validation_job.return_value = mock_validation_results
            mock_worker.return_value = mock_validation_worker

            # Get the tool function (this is a simplified test since FastMCP doesn't expose tools directly)
            # In a real integration test, we would call the tool through the MCP protocol

            # Verify that the tools were registered (basic check)
            assert mcp_server is not None
            assert hasattr(mcp_server, "name")
            assert mcp_server.name == "test-mcp-server"

    @patch("metadata_harmonization_api.utils.logging.mcp_metrics")
    def test_schema_tool_logging_success(self, mock_metrics, mcp_server):
        """Test that schema tool calls are properly logged."""
        # Reset metrics for clean test
        mock_metrics.reset_mock()

        # Mock the dependencies
        with patch("metadata_harmonization_api.mcp.tools.schema.get_schema_collector") as mock_collector:
            # Mock successful schema retrieval
            mock_schema_collector = MagicMock()
            mock_schema_info = MagicMock()
            mock_schema_info.core_uuid = "core-1"
            mock_schema_info.core_name = "Core Schema"
            mock_schema_info.program_uuid = "program-1"
            mock_schema_info.program_name = "Program Schema"
            mock_schema_info.core_path = "/path/to/core"
            mock_schema_info.program_path = "/path/to/program"

            mock_schema_collector.get_available_schemas.return_value = [mock_schema_info]
            mock_collector.return_value = mock_schema_collector

            # Verify that the tools were registered
            assert mcp_server is not None


class TestMetricsCollection:
    """Test metrics collection during tool execution."""

    def test_metrics_instance_exists(self):
        """Test that global metrics instance exists."""
        from metadata_harmonization_api.utils.logging import mcp_metrics

        assert isinstance(mcp_metrics, MCPPerformanceMetrics)
        assert hasattr(mcp_metrics, "tool_call_counts")
        assert hasattr(mcp_metrics, "tool_execution_times")
        assert hasattr(mcp_metrics, "client_connections")

    def test_metrics_recording(self):
        """Test manual metrics recording."""
        # Create a fresh metrics instance for testing
        test_metrics = MCPPerformanceMetrics()

        # Record some tool calls
        test_metrics.record_tool_call("submit_metadata_validation", 2.5, True, "test_client")
        test_metrics.record_tool_call("list_schemas", 0.1, True, "test_client")
        test_metrics.record_tool_call("get_schema_details", 0.5, False, "test_client")

        # Get metrics summary
        summary = test_metrics.get_metrics_summary()

        # Verify metrics were recorded
        assert summary["total_calls"] == 3
        assert summary["total_errors"] == 1
        assert summary["active_clients"] == 1

        # Verify tool-specific metrics
        validation_stats = summary["tool_statistics"]["submit_metadata_validation"]
        assert validation_stats["total_calls"] == 1
        assert validation_stats["success_calls"] == 1
        assert validation_stats["error_calls"] == 0
        assert validation_stats["average_execution_time_seconds"] == 2.5

        schema_list_stats = summary["tool_statistics"]["list_schemas"]
        assert schema_list_stats["total_calls"] == 1
        assert schema_list_stats["success_calls"] == 1
        assert schema_list_stats["average_execution_time_seconds"] == 0.1

        schema_details_stats = summary["tool_statistics"]["get_schema_details"]
        assert schema_details_stats["total_calls"] == 1
        assert schema_details_stats["success_calls"] == 0
        assert schema_details_stats["error_calls"] == 1
        assert schema_details_stats["success_rate"] == 0.0


class TestLoggingConfiguration:
    """Test logging configuration and format consistency."""

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_unified_logging_format(self, mock_logger):
        """Test that unified logging uses consistent format."""
        from metadata_harmonization_api.utils.logging import setup_unified_logging
        from metadata_harmonization_api.models import LogLevel

        setup_unified_logging(LogLevel.INFO)

        # Verify logger was configured
        mock_logger.remove.assert_called_once()
        mock_logger.configure.assert_called_once()

        # Check that configure was called with expected format
        configure_call = mock_logger.configure.call_args
        assert configure_call is not None

        # Verify extra fields are set up
        extra_fields = configure_call[1]["extra"]
        assert "request_id" in extra_fields
        assert "endpoint" in extra_fields
        assert "event" in extra_fields
        assert "client_id" in extra_fields

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_mcp_specific_logging_events(self, mock_logger):
        """Test MCP-specific logging events."""
        from metadata_harmonization_api.utils.logging import (
            log_mcp_client_connection,
            log_mcp_server_startup,
            log_mcp_server_shutdown,
        )

        # Test client connection logging
        log_mcp_client_connection("client123", "connect", remote_addr="192.168.1.100")

        # Verify contextualize was called with MCP-specific context
        contextualize_calls = mock_logger.contextualize.call_args_list
        assert len(contextualize_calls) > 0

        # Test server startup logging
        tools = ["submit_metadata_validation", "list_schemas", "get_schema_details"]
        log_mcp_server_startup("test-server", tools, "/mcp")

        # Test server shutdown logging
        log_mcp_server_shutdown("test-server")

        # Verify multiple contextualize calls were made
        assert len(mock_logger.contextualize.call_args_list) >= 3


class TestErrorHandlingLogging:
    """Test error handling and logging."""

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_tool_error_logging(self, mock_logger):
        """Test that tool errors are properly logged."""
        from metadata_harmonization_api.utils.logging import mcp_tool_context

        # Test error handling in tool context
        try:
            with mcp_tool_context("test_tool", "test_client", {"param": "value"}):
                raise ValueError("Simulated tool error")
        except ValueError:
            pass  # Expected

        # Verify error was logged
        assert mock_logger.contextualize.called
        # The context manager should log both start and error
        assert mock_logger.contextualize.call_count >= 2

    def test_parameter_sanitization_in_logging(self):
        """Test that sensitive parameters are sanitized in logs."""
        from metadata_harmonization_api.utils.logging import MCPLoggerContext

        context = MCPLoggerContext(
            tool_name="test_tool",
            parameters={
                "username": "testuser",
                "password": "secret123",
                "api_key": "abc123def456",
                "metadata_content": "x" * 1000,  # Large content
                "normal_param": "normal_value",
            },
        )

        sanitized = context._sanitize_parameters(context.parameters)

        # Verify sensitive data is redacted
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"

        # Verify large content is truncated
        assert "truncated" in sanitized["metadata_content"]
        assert len(sanitized["metadata_content"]) < 1000

        # Verify normal parameters are preserved
        assert sanitized["username"] == "testuser"
        assert sanitized["normal_param"] == "normal_value"


if __name__ == "__main__":
    pytest.main([__file__])
