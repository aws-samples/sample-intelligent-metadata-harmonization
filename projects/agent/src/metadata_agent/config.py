# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Configuration management for the Metadata Harmonization Agent."""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import yaml


@dataclass
class AgentConfig:
    """Configuration for the Metadata Harmonization Agent."""

    # API Server Configuration
    api_base_url: str = "http://localhost:8080"  # Base URL for HTTP API
    mcp_url: str = "http://localhost:8080/agent/mcp"  # MCP endpoint (for proxy pattern)
    mcp_pat: Optional[str] = None  # Optional for local servers

    # Connection Settings
    timeout: int = 30

    # Logging Configuration
    log_level: str = "INFO"

    # Demo Configuration
    test_data_dir: str = "test_data"

    @classmethod
    def from_file(cls, config_path: str) -> "AgentConfig":
        """Load configuration from a YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            # Return default configuration if file doesn't exist
            return cls()

        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f) or {}

        # Map old field names to new ones for backward compatibility
        if "mcp_server_url" in config_data:
            config_data["mcp_url"] = config_data.pop("mcp_server_url")
        if "connection_timeout" in config_data:
            config_data["timeout"] = config_data.pop("connection_timeout")

        return cls(**{k: v for k, v in config_data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        return cls(
            api_base_url=os.getenv("API_BASE_URL", "http://localhost:8080"),
            mcp_url=os.getenv("MCP_URL", "http://localhost:8080/agent/mcp"),
            mcp_pat=os.getenv("MCP_PAT"),  # None if not set, for local dev
            timeout=int(os.getenv("MCP_TIMEOUT", "30")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            test_data_dir=os.getenv("TEST_DATA_DIR", "test_data"),
        )

    def get_headers(self) -> Optional[dict]:
        """Get HTTP headers for MCP connection."""
        if self.mcp_pat:
            return {"Authorization": f"Bearer {self.mcp_pat}"}
        return None
