# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Base MCP client interface for the Metadata Harmonization Agent."""

import time
from abc import ABC, abstractmethod
from typing import Any, List


class BaseMCPClient(ABC):
    """Abstract base class for MCP clients."""

    def __init__(self, url: str, timeout: int = 30, **kwargs):
        self.url = url
        self.timeout = timeout
        self._connected = False
        self._creation_time = time.time()
        self._connection_attempts = 0
        self._last_health_check = time.time()

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Any]:
        """List available tools from the MCP server."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        pass

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._connected
