# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Clients."""

from typing import Optional

from aiobotocore.client import AioBaseClient
from aiobotocore.config import AioConfig
from aiobotocore.session import get_session

from metadata_harmonization_api.config import api_config


class AWSAsyncManager:
    """Base class for async AWS service managers."""

    client: Optional[AioBaseClient] = None
    service_name: str = ""
    config: Optional[AioConfig] = None

    async def start(self) -> None:
        """Start client."""
        session = get_session()
        self.client = await session.create_client(
            self.service_name,
            region_name=api_config.aws.region,
            config=self.config,
        ).__aenter__()

    async def stop(self) -> None:
        """Stop client."""
        if self.client:
            await self.client.__aexit__(None, None, None)
            self.client = None

    def __call__(self) -> AioBaseClient:
        """Call method."""
        if self.client is None:
            error_message = f"{self.service_name} client not initialized"
            raise RuntimeError(error_message)
        return self.client


class DynamoDbManager(AWSAsyncManager):
    """Async manager for DynamoDB service."""

    service_name = "dynamodb"
