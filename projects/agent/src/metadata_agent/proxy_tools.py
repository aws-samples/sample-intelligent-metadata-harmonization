# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""MCP proxy tools that inject DataFrame data and schema IDs when calling remote MCP server."""

from loguru import logger

from strands import tool
from .session_state import AgentSessionState


class MCPProxyTools:
    """Proxy tools that automatically inject DataFrame content and schema IDs into MCP server calls."""

    def __init__(self, session_state: AgentSessionState, mcp_client):
        """Initialize with session state and MCP client.

        Args:
            session_state: Agent session state containing DataFrame and schema context
            mcp_client: Connected MCP client for calling remote server tools
        """
        self.session_state = session_state
        self.mcp_client = mcp_client
        logger.info("🔗 MCP proxy tools initialized")

    @tool
    async def submit_metadata_validation(self, format: str = "csv") -> dict:
        """Submit current DataFrame for metadata validation using remote MCP server.

        This tool automatically injects:
        - Current DataFrame as CSV content
        - Schema IDs from session context

        Args:
            format: Format of metadata: 'csv' or 'json' (default: 'csv')

        Returns:
            Dictionary containing validation results or error information
        """
        try:
            # Check if DataFrame is loaded
            if not self.session_state.is_dataframe_loaded():
                return {
                    "success": False,
                    "error": "No DataFrame loaded. Load a CSV file first using the agent.",
                    "error_code": "NO_DATAFRAME",
                }

            # Get DataFrame as CSV content
            csv_content = self.session_state.get_csv_content()
            logger.info(f"📊 Injecting DataFrame content ({len(csv_content)} chars)")

            # Get schema IDs from session context
            core_schema_id, program_schema_id = self.session_state.get_schema_ids()

            if not core_schema_id or not program_schema_id:
                return {
                    "success": False,
                    "error": "No schema context available. Schema IDs must be set before validation.",
                    "error_code": "NO_SCHEMA_CONTEXT",
                    "hint": "Use the CLI schema selection or agent schema discovery tools first.",
                }

            logger.info(f"🎯 Injecting schema context: {core_schema_id}/{program_schema_id}")

            # Call remote MCP server tool with injected parameters
            result = await self.mcp_client.call_tool(
                name="submit_metadata_validation",
                arguments={
                    "metadata_content": csv_content,
                    "core_schema_id": core_schema_id,
                    "program_schema_id": program_schema_id,
                    "format": format,
                },
            )

            logger.info("✅ Validation request sent to remote MCP server")
            return result

        except Exception as e:
            logger.error(f"❌ Error in submit_metadata_validation proxy: {e}")
            return {"success": False, "error": f"Proxy tool error: {str(e)}", "error_code": "PROXY_ERROR"}

    @tool
    async def list_schemas(self) -> dict:
        """List all available schemas from remote MCP server.

        Returns:
            Dictionary containing list of available schemas or error information
        """
        try:
            logger.info("📋 Requesting schema list from remote MCP server")

            # Call remote MCP server tool
            result = await self.mcp_client.call_tool(name="list_schemas", arguments={})

            logger.info("✅ Schema list received from remote MCP server")
            return result

        except Exception as e:
            logger.error(f"❌ Error in list_schemas proxy: {e}")
            return {"success": False, "error": f"Proxy tool error: {str(e)}", "error_code": "PROXY_ERROR"}

    @tool
    async def get_schema_details(self, core_schema_id: str, program_schema_id: str) -> dict:
        """Get detailed information about a specific schema combination from remote MCP server.

        Args:
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier

        Returns:
            Dictionary containing detailed schema information or error
        """
        try:
            logger.info(f"📋 Requesting schema details for {core_schema_id}/{program_schema_id}")

            # Call remote MCP server tool
            result = await self.mcp_client.call_tool(
                name="get_schema_details",
                arguments={"core_schema_id": core_schema_id, "program_schema_id": program_schema_id},
            )

            logger.info("✅ Schema details received from remote MCP server")
            return result

        except Exception as e:
            logger.error(f"❌ Error in get_schema_details proxy: {e}")
            return {"success": False, "error": f"Proxy tool error: {str(e)}", "error_code": "PROXY_ERROR"}

    @tool
    async def get_schema_columns(self, core_schema_id: str, program_schema_id: str) -> dict:
        """Get expected columns for a specific schema combination from remote MCP server.

        Args:
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier

        Returns:
            Dictionary containing column information or error
        """
        try:
            logger.info(f"📋 Requesting schema columns for {core_schema_id}/{program_schema_id}")

            # Call remote MCP server tool
            result = await self.mcp_client.call_tool(
                name="get_schema_columns",
                arguments={"core_schema_id": core_schema_id, "program_schema_id": program_schema_id},
            )

            logger.info("✅ Schema columns received from remote MCP server")
            return result

        except Exception as e:
            logger.error(f"❌ Error in get_schema_columns proxy: {e}")
            return {"success": False, "error": f"Proxy tool error: {str(e)}", "error_code": "PROXY_ERROR"}

    @tool
    async def get_validation_rules(self, core_schema_id: str, program_schema_id: str) -> dict:
        """Get validation rules for a specific schema combination from remote MCP server.

        Args:
            core_schema_id: Core schema identifier
            program_schema_id: Program schema identifier

        Returns:
            Dictionary containing validation rules or error
        """
        try:
            logger.info(f"📋 Requesting validation rules for {core_schema_id}/{program_schema_id}")

            # Call remote MCP server tool
            result = await self.mcp_client.call_tool(
                name="get_validation_rules",
                arguments={"core_schema_id": core_schema_id, "program_schema_id": program_schema_id},
            )

            logger.info("✅ Validation rules received from remote MCP server")
            return result

        except Exception as e:
            logger.error(f"❌ Error in get_validation_rules proxy: {e}")
            return {"success": False, "error": f"Proxy tool error: {str(e)}", "error_code": "PROXY_ERROR"}

    @tool
    async def set_schema_context(self, core_schema_id: str, program_schema_id: str) -> dict:
        """Set schema context for automatic injection into validation calls.

        This tool updates the session state so that subsequent validation calls
        automatically use these schema IDs.

        Args:
            core_schema_id: Core schema identifier to use for validation
            program_schema_id: Program schema identifier to use for validation

        Returns:
            Dictionary with operation result
        """
        try:
            # Validate schema IDs exist by calling get_schema_details
            schema_check = await self.get_schema_details(core_schema_id, program_schema_id)

            if not schema_check.get("success", False):
                return {
                    "success": False,
                    "error": f"Invalid schema combination: {schema_check.get('error', 'Unknown error')}",
                    "error_code": "INVALID_SCHEMA_IDS",
                }

            # Set schema context in session state
            self.session_state.set_schema_context(core_schema_id, program_schema_id)

            logger.info(f"🎯 Schema context set: {core_schema_id}/{program_schema_id}")

            return {
                "success": True,
                "core_schema_id": core_schema_id,
                "program_schema_id": program_schema_id,
                "message": "Schema context set. Future validation calls will automatically use these schemas.",
                "operation": "set_schema_context",
            }

        except Exception as e:
            logger.error(f"❌ Error setting schema context: {e}")
            return {
                "success": False,
                "error": f"Failed to set schema context: {str(e)}",
                "error_code": "SCHEMA_CONTEXT_ERROR",
            }

    @tool
    def get_session_status(self) -> dict:
        """Get current session status including DataFrame and schema context.

        Returns:
            Dictionary with comprehensive session information
        """
        try:
            session_info = self.session_state.get_session_info()

            return {
                "success": True,
                "session_status": session_info,
                "dataframe_loaded": session_info["dataframe"]["loaded"],
                "schema_context_available": session_info["schema_context"]["has_schema_context"],
                "ready_for_validation": (
                    session_info["dataframe"]["loaded"] and session_info["schema_context"]["has_schema_context"]
                ),
                "operation_count": session_info["operation_count"],
            }

        except Exception as e:
            logger.error(f"❌ Error getting session status: {e}")
            return {
                "success": False,
                "error": f"Failed to get session status: {str(e)}",
                "error_code": "SESSION_STATUS_ERROR",
            }

    @tool
    def clear_schema_context(self) -> dict:
        """Clear current schema context.

        Returns:
            Dictionary with operation result
        """
        try:
            old_core, old_program = self.session_state.get_schema_ids()
            self.session_state.clear_schema_context()

            logger.info("🧹 Schema context cleared")

            return {
                "success": True,
                "message": "Schema context cleared. You'll need to set schema IDs before validation.",
                "previous_context": {"core_schema_id": old_core, "program_schema_id": old_program},
                "operation": "clear_schema_context",
            }

        except Exception as e:
            logger.error(f"❌ Error clearing schema context: {e}")
            return {
                "success": False,
                "error": f"Failed to clear schema context: {str(e)}",
                "error_code": "CLEAR_CONTEXT_ERROR",
            }
