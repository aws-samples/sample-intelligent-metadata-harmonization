# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""MCP server setup and integration with FastAPI."""

from fastmcp import FastMCP
from loguru import logger

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.utils.logging import log_mcp_server_startup


def create_mcp_server(processor_config: ProcessorConfig, server_name: str = "Metadata Harmonization Tools") -> FastMCP:
    """
    Create MCP server with tools.

    Args:
        processor_config: ProcessorConfig instance for shared component initialization
        server_name: Name of the MCP server

    Returns:
        Configured FastMCP server instance
    """
    logger.info(f"Creating MCP server: {server_name}")

    # Create FastMCP server instance
    mcp = FastMCP(server_name)

    # Import and register tools with shared dependency injection
    from .tools.validation import setup_validation_tools
    from .tools.schema import setup_schema_tools

    # Register validation tools using shared dependency injection
    setup_validation_tools(mcp, processor_config)
    logger.info("Registered MCP validation tools using shared dependency injection")

    # Register schema tools using shared dependency injection
    setup_schema_tools(mcp, processor_config)
    logger.info("Registered MCP schema tools using shared dependency injection")

    # Log server startup with available tools
    available_tools = [
        "submit_metadata_validation",
        "list_schemas",
        "get_schema_details",
        "get_schema_columns",
        "get_validation_rules",
    ]

    log_mcp_server_startup(server_name, available_tools, "/mcp")

    logger.info(f"MCP server '{server_name}' created successfully with all tools registered")

    return mcp


async def get_mcp_server_info(mcp: FastMCP) -> dict:
    """
    Get information about the MCP server and its tools.

    Args:
        mcp: FastMCP server instance

    Returns:
        Dictionary containing server information
    """
    try:
        # Get server capabilities and tools
        tools_info = []

        # Note: FastMCP doesn't expose tools directly, so we'll provide static info
        tools_info = [
            {
                "name": "submit_metadata_validation",
                "description": "Submit metadata for validation and get complete results",
                "parameters": [
                    "metadata_content (str): CSV content to validate",
                    "core_schema_id (str): Core schema identifier for validation",
                    "program_schema_id (str): Program schema identifier for validation",
                    "format (str, optional): Format of metadata: 'csv' or 'json'",
                ],
            },
            {"name": "list_schemas", "description": "List all available schemas with their metadata", "parameters": []},
            {
                "name": "get_schema_details",
                "description": "Get detailed information about a specific schema combination",
                "parameters": [
                    "core_schema_id (str): Core schema identifier",
                    "program_schema_id (str): Program schema identifier",
                ],
            },
        ]

        return {
            "server_name": mcp.name if hasattr(mcp, "name") else "metadata-harmonization-mcp-server",
            "status": "running",
            "tools_count": len(tools_info),
            "tools": tools_info,
        }

    except Exception as e:
        logger.error(f"Error getting MCP server info: {e}")
        return {"server_name": "metadata-harmonization-mcp-server", "status": "error", "error": str(e)}
