# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Loguru logging configuration for demo-friendly output."""

import sys
from loguru import logger


def configure_demo_logging(level: str = "INFO") -> None:
    """Configure Loguru for beautiful, demo-friendly logging output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default handler
    logger.remove()

    # Add colorful, structured handler for demo appeal
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
    )


def configure_quiet_logging() -> None:
    """Configure minimal logging for non-demo scenarios."""
    logger.remove()

    logger.add(
        sys.stdout,
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        level="WARNING",
        colorize=True,
    )


def log_tool_call(tool_name: str, arguments: dict) -> None:
    """Log MCP tool call with structured formatting.

    Args:
        tool_name: Name of the MCP tool being called
        arguments: Arguments passed to the tool
    """
    logger.info(f"🔧 Calling MCP tool: {tool_name}")
    if arguments:
        logger.debug(f"📥 Tool arguments: {arguments}")


def log_tool_response(tool_name: str, success: bool, duration_ms: float = None) -> None:
    """Log MCP tool response with structured formatting.

    Args:
        tool_name: Name of the MCP tool that was called
        success: Whether the tool call was successful
        duration_ms: Optional duration in milliseconds
    """
    status_icon = "✅" if success else "❌"
    duration_text = f" ({duration_ms:.1f}ms)" if duration_ms else ""

    if success:
        logger.info(f"{status_icon} Tool '{tool_name}' completed successfully{duration_text}")
    else:
        logger.error(f"{status_icon} Tool '{tool_name}' failed{duration_text}")


def log_connection_status(url: str, connected: bool, error: str = None) -> None:
    """Log MCP connection status with clear formatting.

    Args:
        url: MCP server URL
        connected: Whether connection was successful
        error: Optional error message if connection failed
    """
    if connected:
        logger.info(f"🔗 Connected to MCP server: {url}")
    else:
        error_msg = f" - {error}" if error else ""
        logger.error(f"💥 Failed to connect to MCP server: {url}{error_msg}")


def log_agent_startup(config_info: dict) -> None:
    """Log agent startup information with demo appeal.

    Args:
        config_info: Dictionary containing configuration details
    """
    logger.info("🚀 Starting Metadata Harmonization Agent")
    logger.info(f"🌐 MCP Server: {config_info.get('mcp_url', 'Not configured')}")
    logger.info("⚙️  Configuration loaded successfully")


def log_agent_shutdown() -> None:
    """Log agent shutdown with clean formatting."""
    logger.info("👋 Metadata Harmonization Agent shutting down")


def log_error_with_context(error: Exception, context: str = None) -> None:
    """Log errors with rich context and formatting.

    Args:
        error: The exception that occurred
        context: Optional context about where the error occurred
    """
    context_text = f" in {context}" if context else ""
    logger.error(f"💥 Error{context_text}: {str(error)}")
    logger.opt(exception=True).debug("Full error traceback:")
