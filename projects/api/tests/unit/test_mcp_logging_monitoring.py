# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Tests for MCP logging and monitoring functionality."""

import pytest
import time
from unittest.mock import patch

from metadata_harmonization_api.utils.logging import (
    MCPLoggerContext,
    MCPPerformanceMetrics,
    mcp_tool_context,
    setup_unified_logging,
    log_mcp_client_connection,
    log_mcp_server_startup,
    log_mcp_server_shutdown,
    get_mcp_metrics,
    log_mcp_metrics,
)
from metadata_harmonization_api.models import LogLevel


class TestMCPLoggerContext:
    """Test MCP logger context functionality."""

    def test_logger_context_creation(self):
        """Test creating MCP logger context."""
        context = MCPLoggerContext(
            tool_name="test_tool", client_id="test_client", parameters={"param1": "value1", "param2": "value2"}
        )

        assert context.tool_name == "test_tool"
        assert context.client_id == "test_client"
        assert context.parameters == {"param1": "value1", "param2": "value2"}
        assert context.start_time is None
        assert context.request_id is not None

    def test_logger_context_with_defaults(self):
        """Test creating MCP logger context with default values."""
        context = MCPLoggerContext(tool_name="test_tool")

        assert context.tool_name == "test_tool"
        assert context.client_id == "unknown"
        assert context.parameters == {}

    def test_parameter_sanitization(self):
        """Test parameter sanitization for logging."""
        context = MCPLoggerContext(
            tool_name="test_tool",
            parameters={
                "password": "secret123",
                "token": "abc123",
                "metadata_content": "a" * 1000,  # Large content
                "normal_param": "normal_value",
                "large_string": "x" * 2000,  # Very large string
            },
        )

        sanitized = context._sanitize_parameters(context.parameters)

        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"
        assert "truncated" in sanitized["metadata_content"]
        assert sanitized["normal_param"] == "normal_value"
        assert "truncated" in sanitized["large_string"]

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_context_manager_success(self, mock_logger):
        """Test context manager for successful execution."""
        with MCPLoggerContext("test_tool", "test_client") as context:
            assert context.start_time is not None
            time.sleep(0.01)  # Small delay to test duration

        # Verify logger was called for start and completion
        assert mock_logger.contextualize.called
        assert mock_logger.info.called

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_context_manager_error(self, mock_logger):
        """Test context manager for error handling."""
        with pytest.raises(ValueError):
            with MCPLoggerContext("test_tool", "test_client") as context:
                assert context.start_time is not None
                raise ValueError("Test error")

        # Verify logger was called for start and error
        assert mock_logger.contextualize.called
        assert mock_logger.error.called

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_log_progress(self, mock_logger):
        """Test progress logging during tool execution."""
        context = MCPLoggerContext("test_tool", "test_client")
        context.log_progress("Processing data", step=1, total=5)

        assert mock_logger.contextualize.called
        assert mock_logger.debug.called


class TestMCPPerformanceMetrics:
    """Test MCP performance metrics functionality."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = MCPPerformanceMetrics()

        assert metrics.tool_call_counts == {}
        assert metrics.tool_execution_times == {}
        assert metrics.client_connections == {}
        assert metrics.error_counts == {}

    def test_record_successful_tool_call(self):
        """Test recording successful tool calls."""
        metrics = MCPPerformanceMetrics()

        metrics.record_tool_call("test_tool", 1.5, True, "client1")

        assert "test_tool" in metrics.tool_call_counts
        assert metrics.tool_call_counts["test_tool"]["success"] == 1
        assert metrics.tool_call_counts["test_tool"]["error"] == 0
        assert "test_tool" in metrics.tool_execution_times
        assert 1.5 in metrics.tool_execution_times["test_tool"]
        assert "client1" in metrics.client_connections

    def test_record_failed_tool_call(self):
        """Test recording failed tool calls."""
        metrics = MCPPerformanceMetrics()

        metrics.record_tool_call("test_tool", 0.5, False, "client1")

        assert "test_tool" in metrics.tool_call_counts
        assert metrics.tool_call_counts["test_tool"]["success"] == 0
        assert metrics.tool_call_counts["test_tool"]["error"] == 1
        assert "test_tool" in metrics.tool_execution_times
        assert 0.5 in metrics.tool_execution_times["test_tool"]

    def test_execution_time_limit(self):
        """Test execution time list size limit."""
        metrics = MCPPerformanceMetrics()

        # Add more than 100 measurements
        for i in range(150):
            metrics.record_tool_call("test_tool", i * 0.1, True, "client1")

        # Should only keep last 100 measurements
        assert len(metrics.tool_execution_times["test_tool"]) == 100
        assert metrics.tool_execution_times["test_tool"][0] == 5.0  # 50 * 0.1
        assert metrics.tool_execution_times["test_tool"][-1] == 14.9  # 149 * 0.1

    def test_metrics_summary(self):
        """Test metrics summary generation."""
        metrics = MCPPerformanceMetrics()

        # Record some tool calls
        metrics.record_tool_call("tool1", 1.0, True, "client1")
        metrics.record_tool_call("tool1", 2.0, True, "client1")
        metrics.record_tool_call("tool1", 0.5, False, "client2")
        metrics.record_tool_call("tool2", 3.0, True, "client1")

        summary = metrics.get_metrics_summary()

        assert summary["active_clients"] == 2
        assert summary["total_calls"] == 4
        assert summary["total_errors"] == 1

        # Check tool1 statistics
        tool1_stats = summary["tool_statistics"]["tool1"]
        assert tool1_stats["total_calls"] == 3
        assert tool1_stats["success_calls"] == 2
        assert tool1_stats["error_calls"] == 1
        assert tool1_stats["success_rate"] == 2 / 3
        assert tool1_stats["average_execution_time_seconds"] == 1.167  # (1.0 + 2.0 + 0.5) / 3

        # Check tool2 statistics
        tool2_stats = summary["tool_statistics"]["tool2"]
        assert tool2_stats["total_calls"] == 1
        assert tool2_stats["success_calls"] == 1
        assert tool2_stats["error_calls"] == 0
        assert tool2_stats["success_rate"] == 1.0
        assert tool2_stats["average_execution_time_seconds"] == 3.0

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_log_metrics_summary(self, mock_logger):
        """Test logging metrics summary."""
        metrics = MCPPerformanceMetrics()
        metrics.record_tool_call("test_tool", 1.0, True, "client1")

        metrics.log_metrics_summary()

        assert mock_logger.contextualize.called
        assert mock_logger.info.called


class TestUnifiedLogging:
    """Test unified logging setup and functionality."""

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_setup_unified_logging(self, mock_logger):
        """Test unified logging setup."""
        setup_unified_logging(LogLevel.DEBUG)

        assert mock_logger.remove.called
        assert mock_logger.configure.called
        assert mock_logger.info.called

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_log_mcp_client_connection(self, mock_logger):
        """Test MCP client connection logging."""
        log_mcp_client_connection("client1", "connect", remote_addr="127.0.0.1")

        assert mock_logger.contextualize.called
        assert mock_logger.info.called

        log_mcp_client_connection("client1", "disconnect")
        log_mcp_client_connection("client1", "error", error_message="Connection failed")

        # Should have been called multiple times
        assert mock_logger.contextualize.call_count >= 3

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_log_mcp_server_startup(self, mock_logger):
        """Test MCP server startup logging."""
        tools = ["tool1", "tool2", "tool3"]
        log_mcp_server_startup("test-server", tools, "/mcp")

        assert mock_logger.contextualize.called
        assert mock_logger.info.called

    @patch("metadata_harmonization_api.utils.logging.logger")
    def test_log_mcp_server_shutdown(self, mock_logger):
        """Test MCP server shutdown logging."""
        log_mcp_server_shutdown("test-server")

        assert mock_logger.contextualize.called
        assert mock_logger.info.called


class TestMCPToolContext:
    """Test MCP tool context decorator/context manager."""

    @patch("metadata_harmonization_api.utils.logging.mcp_metrics")
    def test_mcp_tool_context_success(self, mock_metrics):
        """Test MCP tool context for successful execution."""
        with mcp_tool_context("test_tool", "client1", {"param": "value"}) as context:
            assert isinstance(context, MCPLoggerContext)
            assert context.tool_name == "test_tool"
            assert context.client_id == "client1"

        # Should record successful execution
        mock_metrics.record_tool_call.assert_called_once()
        args = mock_metrics.record_tool_call.call_args[0]
        assert args[0] == "test_tool"  # tool_name
        assert args[2] is True  # success
        assert args[3] == "client1"  # client_id

    @patch("metadata_harmonization_api.utils.logging.mcp_metrics")
    def test_mcp_tool_context_error(self, mock_metrics):
        """Test MCP tool context for error handling."""
        with pytest.raises(ValueError):
            with mcp_tool_context("test_tool", "client1"):
                raise ValueError("Test error")

        # Should record failed execution
        mock_metrics.record_tool_call.assert_called_once()
        args = mock_metrics.record_tool_call.call_args[0]
        assert args[0] == "test_tool"  # tool_name
        assert args[2] is False  # success
        assert args[3] == "client1"  # client_id


class TestMetricsIntegration:
    """Test metrics integration functionality."""

    @patch("metadata_harmonization_api.utils.logging.mcp_metrics")
    def test_get_mcp_metrics(self, mock_metrics):
        """Test getting MCP metrics."""
        mock_summary = {
            "tool_statistics": {"test_tool": {"total_calls": 5}},
            "active_clients": 2,
            "total_calls": 5,
            "total_errors": 1,
        }
        mock_metrics.get_metrics_summary.return_value = mock_summary

        result = get_mcp_metrics()

        assert result == mock_summary
        mock_metrics.get_metrics_summary.assert_called_once()

    @patch("metadata_harmonization_api.utils.logging.mcp_metrics")
    def test_log_mcp_metrics(self, mock_metrics):
        """Test logging MCP metrics."""
        log_mcp_metrics()

        mock_metrics.log_metrics_summary.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
