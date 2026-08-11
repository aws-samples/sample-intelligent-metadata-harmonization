# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""StreamableHTTPMCPClient implementation using Strands MCPClient."""

import time
import uuid
from typing import Any, Optional, Dict, List
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
from strands.tools.mcp.mcp_agent_tool import MCPAgentTool  # runtime type
from .base_client import BaseMCPClient
from loguru import logger


class StreamableHTTPMCPClient(BaseMCPClient):
    """MCP client using Strands MCPClient over Streamable HTTP."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(url, **kwargs)
        if not self.url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid HTTP URL format: {self.url}")
        self.headers = headers or {}
        self._mcp: Optional[MCPClient] = None

    def _build_client(self) -> MCPClient:
        """Build MCPClient with streamable HTTP transport."""
        # MCPClient expects a callable returning an async context manager
        # that yields (read_stream, write_stream[, get_session_id]).
        return MCPClient(
            lambda: streamablehttp_client(self.url, headers=self.headers),
            startup_timeout=int(self.timeout),
        )

    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        if self._connected and self._mcp:
            logger.debug("MCPClient already connected")
            return

        try:
            logger.info(f"Connecting MCPClient (streamable-http): {self.url}")
            self._mcp = self._build_client()
            self._mcp.start()  # blocks until initialized
            self._connected = True
            self._creation_time = time.time()
            self._connection_attempts = 0
            self._last_health_check = time.time()
            logger.info("Connected")
        except Exception as e:
            logger.error(f"Failed to connect to {self.url}: {e}")
            await self._cleanup()
            self._connected = False
            raise ConnectionError(f"Failed to connect to {self.url}: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if not self._connected:
            return

        try:
            logger.info("Disconnecting MCPClient")
            await self._cleanup()
        finally:
            self._connected = False

    async def _cleanup(self) -> None:
        """Clean up MCP client resources."""
        if self._mcp is not None:
            try:
                # mirrors context manager __exit__
                self._mcp.stop(None, None, None)
            except Exception as e:
                logger.warning(f"Error during MCP client cleanup: {e}")
            finally:
                self._mcp = None

    async def list_tools(self) -> List[MCPAgentTool]:
        """List available tools from the MCP server."""
        if not self._connected or not self._mcp:
            raise ConnectionError(f"Client not connected to {self.url}")
        return self._mcp.list_tools_sync()  # returns AgentTool objects

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        if not self._connected or not self._mcp:
            raise ConnectionError(f"Client not connected to {self.url}")

        tool_use_id = f"tool-{uuid.uuid4()}"
        return await self._mcp.call_tool_async(
            tool_use_id=tool_use_id,
            name=name,
            arguments=arguments,
        )

    # compatibility shim if needed elsewhere
    async def list_tools_sync(self):
        """Synchronous compatibility method for listing tools."""
        return await self.list_tools()

    @property
    def session_id(self):
        """Get session ID (MCPClient doesn't expose session id like low-level ClientSession)."""
        return None
