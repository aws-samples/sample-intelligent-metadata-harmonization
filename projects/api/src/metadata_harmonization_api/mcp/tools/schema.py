# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""MCP schema tools using shared dependency injection."""

from typing import Dict, Any

from fastmcp import FastMCP
from loguru import logger

from metadata_harmonization_processor.config import ProcessorConfig
from metadata_harmonization_api.utils.shared_dependencies import get_schema_collector


def setup_schema_tools(mcp: FastMCP, processor_config: ProcessorConfig) -> None:
    """
    Set up MCP schema tools using shared dependency injection.

    Args:
        mcp: FastMCP server instance
        processor_config: ProcessorConfig instance for shared component initialization
    """

    @mcp.tool(description="List all available schemas with their metadata")
    async def list_schemas() -> Dict[str, Any]:
        """
        List all available schemas with their metadata.

        Returns:
            Dictionary containing list of available schemas or error information
        """
        logger.info("Retrieving available schemas")

        # Use shared SchemaCollector via dependency injection
        schema_collector = get_schema_collector(processor_config)

        # Use await instead of creating new event loop (we're already in async context)
        collector_schemas = await schema_collector.get_available_schemas()

        # Convert SchemaInfo objects to simplified format for MCP
        schemas = []
        for schema_info in collector_schemas:
            schemas.append(
                {
                    "core_schema_id": schema_info.core_uuid,
                    "core_name": schema_info.core_name,
                    "core_path": schema_info.core_path,
                    "program_schema_id": schema_info.program_uuid,
                    "program_name": schema_info.program_name,
                    "program_path": schema_info.program_path,
                    "description": f"Core: {schema_info.core_name}, Program: {schema_info.program_name}",
                }
            )

        logger.info(f"Schema retrieval completed - found {len(schemas)} schemas")

        return {"success": True, "schemas": schemas, "count": len(schemas)}

    @mcp.tool(description="Get detailed information about a specific schema combination")
    async def get_schema_details(core_schema_id: str, program_schema_id: str) -> Dict[str, Any]:
        """
        Get detailed schema information for a specific core/program combination.

        Args:
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier

        Returns:
            Dictionary containing detailed schema information or error
        """
        logger.info(f"Getting schema details for {core_schema_id}/{program_schema_id}")

        # Validate input parameters
        if not core_schema_id or not core_schema_id.strip():
            logger.error("Invalid input: core_schema_id cannot be empty")
            return {"success": False, "error": "core_schema_id cannot be empty", "error_code": "INVALID_INPUT"}

        if not program_schema_id or not program_schema_id.strip():
            logger.error("Invalid input: program_schema_id cannot be empty")
            return {"success": False, "error": "program_schema_id cannot be empty", "error_code": "INVALID_INPUT"}

        # Use shared SchemaCollector via dependency injection
        schema_collector = get_schema_collector(processor_config)

        # Use await instead of creating new event loop (we're already in async context)
        # Get schema definition
        schema_data = await schema_collector.get_schema(program_schema_id, core_schema_id)

        # Get schema columns
        schema_columns = await schema_collector.get_schema_columns(program_schema_id, core_schema_id)

        # Get validation rules
        validation_rules = await schema_collector.get_validation_rules(program_schema_id, core_schema_id)

        column_count = len(schema_columns) if schema_columns else 0
        logger.info(f"Schema details retrieved successfully - {column_count} columns")

        return {
            "success": True,
            "core_schema_id": core_schema_id,
            "program_schema_id": program_schema_id,
            "schema_data": schema_data,
            "columns": schema_columns,
            "validation_rules": validation_rules,
            "column_count": column_count,
        }

    @mcp.tool(description="Get expected columns for a specific schema combination")
    async def get_schema_columns(core_schema_id: str, program_schema_id: str) -> Dict[str, Any]:
        """
        Get list of expected columns for a specific schema combination.

        Args:
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier

        Returns:
            Dictionary containing column information or error
        """
        logger.info(f"Getting schema columns for {core_schema_id}/{program_schema_id}")

        # Validate input parameters
        if not core_schema_id or not core_schema_id.strip():
            logger.error("Invalid input: core_schema_id cannot be empty")
            return {"success": False, "error": "core_schema_id cannot be empty", "error_code": "INVALID_INPUT"}

        if not program_schema_id or not program_schema_id.strip():
            logger.error("Invalid input: program_schema_id cannot be empty")
            return {"success": False, "error": "program_schema_id cannot be empty", "error_code": "INVALID_INPUT"}

        # Use shared SchemaCollector via dependency injection
        schema_collector = get_schema_collector(processor_config)

        # Use await instead of creating new event loop (we're already in async context)
        schema_columns = await schema_collector.get_schema_columns(program_schema_id, core_schema_id)

        logger.info(f"Schema columns retrieved successfully - {len(schema_columns)} columns")

        return {
            "success": True,
            "core_schema_id": core_schema_id,
            "program_schema_id": program_schema_id,
            "columns": schema_columns,
            "column_count": len(schema_columns),
        }

    @mcp.tool(description="Get validation rules for a specific schema combination")
    async def get_validation_rules(core_schema_id: str, program_schema_id: str) -> Dict[str, Any]:
        """
        Get validation rules for a specific schema combination.

        Args:
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier

        Returns:
            Dictionary containing validation rules or error
        """
        logger.info(f"Getting validation rules for {core_schema_id}/{program_schema_id}")

        # Validate input parameters
        if not core_schema_id or not core_schema_id.strip():
            logger.error("Invalid input: core_schema_id cannot be empty")
            return {"success": False, "error": "core_schema_id cannot be empty", "error_code": "INVALID_INPUT"}

        if not program_schema_id or not program_schema_id.strip():
            logger.error("Invalid input: program_schema_id cannot be empty")
            return {"success": False, "error": "program_schema_id cannot be empty", "error_code": "INVALID_INPUT"}

        # Use shared SchemaCollector via dependency injection
        schema_collector = get_schema_collector(processor_config)

        # Use await instead of creating new event loop (we're already in async context)
        validation_rules = await schema_collector.get_validation_rules(program_schema_id, core_schema_id)

        rules_count = len(validation_rules) if isinstance(validation_rules, dict) else 0
        logger.info(f"Validation rules retrieved successfully - {rules_count} rules")

        return {
            "success": True,
            "core_schema_id": core_schema_id,
            "program_schema_id": program_schema_id,
            "validation_rules": validation_rules,
            "rules_count": rules_count,
        }

    logger.info("MCP schema tools registered successfully")
