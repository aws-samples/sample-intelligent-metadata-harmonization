# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""HTTP client for interacting with the Metadata Harmonization API."""

from typing import Dict, Any, List, Optional
import aiohttp
import json
from loguru import logger


class MetadataAPIClient:
    """HTTP client for the Metadata Harmonization API."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize the API client.

        Args:
            base_url: Base URL of the API (e.g., http://localhost:8080)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def list_schemas(self) -> List[Dict[str, Any]]:
        """List available schemas from the API.

        Returns:
            List of schema dictionaries with metadata
        """
        session = await self._get_session()

        try:
            url = f"{self.base_url}/api/v1/metadata/schema"
            logger.debug(f"📡 GET {url}")

            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                logger.info(f"✅ Retrieved {len(data)} schemas from API")
                return data

        except aiohttp.ClientError as e:
            logger.error(f"❌ HTTP error listing schemas: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error listing schemas: {e}")
            raise
