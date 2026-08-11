# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unified logging configuration for REST API and MCP server."""

import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional
from uuid import uuid4

from loguru import logger

from metadata_harmonization_api.models import LogLevel


class MCPLoggerContext:
    """Context manager for MCP-specific logging with performance metrics."""

    def __init__(self, tool_name: str, client_id: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None):
        self.tool_name = tool_name
        self.client_id = client_id or "unknown"
        self.parameters = parameters or {}
        self.start_time = None
        self.request_id = str(uuid4())

    def __enter__(self):
        """Enter the logging context."""
        self.start_time = time.time()

        # Log tool call start with parameters (sanitized)
        sanitized_params = self._sanitize_parameters(self.parameters)

        with logger.contextualize(
            request_id=self.request_id,
            endpoint=f"mcp/{self.tool_name}",
            event="mcp_tool_start",
            client_id=self.client_id,
        ):
            logger.info(
                f"MCP tool call started: {self.tool_name}",
                extra={
                    "tool_name": self.tool_name,
                    "client_id": self.client_id,
                    "parameters": sanitized_params,
                    "parameter_count": len(self.parameters),
                },
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the logging context with performance metrics."""
        duration = time.time() - self.start_time if self.start_time else 0

        with logger.contextualize(
            request_id=self.request_id,
            endpoint=f"mcp/{self.tool_name}",
            event="mcp_tool_complete",
            client_id=self.client_id,
        ):
            if exc_type is None:
                # Success case
                logger.info(
                    f"MCP tool call completed: {self.tool_name}",
                    extra={
                        "tool_name": self.tool_name,
                        "client_id": self.client_id,
                        "duration_seconds": round(duration, 3),
                        "status": "success",
                    },
                )
            else:
                # Error case
                logger.error(
                    f"MCP tool call failed: {self.tool_name}",
                    extra={
                        "tool_name": self.tool_name,
                        "client_id": self.client_id,
                        "duration_seconds": round(duration, 3),
                        "status": "error",
                        "error_type": exc_type.__name__ if exc_type else "unknown",
                        "error_message": str(exc_val) if exc_val else "unknown",
                    },
                )

    def log_progress(self, message: str, **extra_data):
        """Log progress during tool execution."""
        with logger.contextualize(
            request_id=self.request_id,
            endpoint=f"mcp/{self.tool_name}",
            event="mcp_tool_progress",
            client_id=self.client_id,
        ):
            logger.debug(
                f"MCP tool progress: {self.tool_name} - {message}",
                extra={
                    "tool_name": self.tool_name,
                    "client_id": self.client_id,
                    "progress_message": message,
                    **extra_data,
                },
            )

    def _sanitize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters for logging (remove sensitive data, truncate large content)."""
        sanitized = {}

        for key, value in params.items():
            # Check for sensitive keys (case-insensitive)
            if any(sensitive in key.lower() for sensitive in ["password", "token", "secret", "key", "api_key"]):
                sanitized[key] = "[REDACTED]"
            elif key == "metadata_content" and isinstance(value, str):
                # Truncate large content for logging
                if len(value) > 500:
                    sanitized[key] = f"{value[:500]}... [truncated, total length: {len(value)}]"
                else:
                    sanitized[key] = value
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = f"{value[:1000]}... [truncated, total length: {len(value)}]"
            else:
                sanitized[key] = value

        return sanitized


class MCPPerformanceMetrics:
    """Track and log MCP server performance metrics."""

    def __init__(self):
        self.tool_call_counts = {}
        self.tool_execution_times = {}
        self.client_connections = {}
        self.error_counts = {}

    def record_tool_call(self, tool_name: str, duration: float, success: bool, client_id: str):
        """Record a tool call for metrics tracking."""
        # Update call counts
        if tool_name not in self.tool_call_counts:
            self.tool_call_counts[tool_name] = {"success": 0, "error": 0}

        if success:
            self.tool_call_counts[tool_name]["success"] += 1
        else:
            self.tool_call_counts[tool_name]["error"] += 1

        # Update execution times
        if tool_name not in self.tool_execution_times:
            self.tool_execution_times[tool_name] = []
        self.tool_execution_times[tool_name].append(duration)

        # Keep only last 100 measurements per tool
        if len(self.tool_execution_times[tool_name]) > 100:
            self.tool_execution_times[tool_name] = self.tool_execution_times[tool_name][-100:]

        # Update client connections
        self.client_connections[client_id] = time.time()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current performance metrics summary."""
        summary = {
            "tool_statistics": {},
            "active_clients": len(self.client_connections),
            "total_calls": 0,
            "total_errors": 0,
        }

        for tool_name, counts in self.tool_call_counts.items():
            total_calls = counts["success"] + counts["error"]
            summary["total_calls"] += total_calls
            summary["total_errors"] += counts["error"]

            # Calculate average execution time
            avg_time = 0
            if tool_name in self.tool_execution_times and self.tool_execution_times[tool_name]:
                avg_time = sum(self.tool_execution_times[tool_name]) / len(self.tool_execution_times[tool_name])

            summary["tool_statistics"][tool_name] = {
                "total_calls": total_calls,
                "success_calls": counts["success"],
                "error_calls": counts["error"],
                "success_rate": counts["success"] / total_calls if total_calls > 0 else 0,
                "average_execution_time_seconds": round(avg_time, 3),
            }

        return summary

    def log_metrics_summary(self):
        """Log current metrics summary."""
        summary = self.get_metrics_summary()

        with logger.contextualize(request_id="metrics", endpoint="mcp/metrics", event="mcp_metrics_summary"):
            logger.info(
                "MCP server performance metrics summary",
                extra={
                    "metrics": summary,
                    "active_clients": summary["active_clients"],
                    "total_calls": summary["total_calls"],
                    "total_errors": summary["total_errors"],
                    "overall_success_rate": (
                        (summary["total_calls"] - summary["total_errors"]) / summary["total_calls"]
                        if summary["total_calls"] > 0
                        else 1.0
                    ),
                },
            )


# Global metrics instance
mcp_metrics = MCPPerformanceMetrics()


def setup_unified_logging(log_level: LogLevel = LogLevel.INFO) -> None:
    """
    Set up unified logging configuration for both REST API and MCP server.

    Args:
        log_level: Logging level to use
    """
    # Remove default logger
    logger.remove()

    # Configure unified logger with consistent format
    logger.configure(
        extra={
            "request_id": "NO_REQUEST_ID",
            "endpoint": "NO_ENDPOINT",
            "event": "NO_EVENT",
            "client_id": "NO_CLIENT_ID",
        },
        handlers=[
            {
                "sink": sys.stdout,
                "format": (
                    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                    "<level>{level:<8}</level> | "
                    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                    "<cyan>{extra[request_id]}</cyan> | "
                    "<yellow>{extra[endpoint]}</yellow> | "
                    "<blue>{extra[event]}</blue> | "
                    "<magenta>{extra[client_id]}</magenta> | "
                    "{message}"
                ),
                "level": log_level.value,
                "serialize": False,
            }
        ],
    )

    logger.info(f"Unified logging configured with level: {log_level.value}")


def log_mcp_client_connection(client_id: str, event: str, **extra_data):
    """
    Log MCP client connection events.

    Args:
        client_id: Unique identifier for the client
        event: Connection event type (connect, disconnect, error)
        **extra_data: Additional data to log
    """
    with logger.contextualize(
        request_id=str(uuid4()), endpoint="mcp/connection", event=f"mcp_client_{event}", client_id=client_id
    ):
        if event == "connect":
            logger.info(
                f"MCP client connected: {client_id}",
                extra={"client_id": client_id, "connection_event": event, **extra_data},
            )
        elif event == "disconnect":
            logger.info(
                f"MCP client disconnected: {client_id}",
                extra={"client_id": client_id, "connection_event": event, **extra_data},
            )
        elif event == "error":
            logger.error(
                f"MCP client connection error: {client_id}",
                extra={"client_id": client_id, "connection_event": event, **extra_data},
            )


def log_mcp_server_startup(server_name: str, tools: list, mount_path: str):
    """
    Log MCP server startup information.

    Args:
        server_name: Name of the MCP server
        tools: List of available tools
        mount_path: Path where server is mounted
    """
    with logger.contextualize(request_id="startup", endpoint="mcp/server", event="mcp_server_startup"):
        logger.info(
            f"MCP server started: {server_name}",
            extra={
                "server_name": server_name,
                "mount_path": mount_path,
                "tools_count": len(tools),
                "available_tools": tools,
                "startup_event": "server_ready",
            },
        )


def log_mcp_server_shutdown(server_name: str):
    """
    Log MCP server shutdown information.

    Args:
        server_name: Name of the MCP server
    """
    with logger.contextualize(request_id="shutdown", endpoint="mcp/server", event="mcp_server_shutdown"):
        logger.info(
            f"MCP server shutting down: {server_name}",
            extra={"server_name": server_name, "shutdown_event": "server_stopping"},
        )


@contextmanager
def mcp_tool_context(tool_name: str, client_id: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None):
    """
    Context manager for MCP tool execution with automatic logging and metrics.

    Args:
        tool_name: Name of the MCP tool being executed
        client_id: Optional client identifier
        parameters: Optional tool parameters

    Yields:
        MCPLoggerContext instance for additional logging
    """
    context = MCPLoggerContext(tool_name, client_id, parameters)

    try:
        with context:
            yield context
            # Record successful execution
            duration = time.time() - context.start_time if context.start_time else 0
            mcp_metrics.record_tool_call(tool_name, duration, True, context.client_id)

    except Exception:
        # Record failed execution
        duration = time.time() - context.start_time if context.start_time else 0
        mcp_metrics.record_tool_call(tool_name, duration, False, context.client_id)
        raise


def get_mcp_metrics() -> Dict[str, Any]:
    """Get current MCP performance metrics."""
    return mcp_metrics.get_metrics_summary()


def log_mcp_metrics():
    """Log current MCP performance metrics."""
    mcp_metrics.log_metrics_summary()
