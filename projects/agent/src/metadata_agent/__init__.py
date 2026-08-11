# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Metadata Harmonization Agent Package."""

from .config import AgentConfig
from .base_client import BaseMCPClient
from .streamable_http_client import StreamableHTTPMCPClient
from .main import MetadataAgent

__version__ = "0.1.0"
__author__ = "Metadata Harmonization Team"
__description__ = "AWS Strands agent for metadata validation and schema discovery"

__all__ = ["AgentConfig", "BaseMCPClient", "StreamableHTTPMCPClient", "MetadataAgent"]
