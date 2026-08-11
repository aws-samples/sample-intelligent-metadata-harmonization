# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Health check endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Request

from metadata_harmonization_api.config import load_api_configuration

api_config_loaded, processor_config = load_api_configuration()

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(request: Request) -> Dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "metadata-validation-api"}


@router.get("/detailed")
async def detailed_health_check(request: Request) -> Dict[str, Any]:
    """Detailed health check with full configuration report."""
    from datetime import datetime

    return {
        "status": "healthy",
        "service": "metadata-validation-api",
        "timestamp": datetime.utcnow().isoformat(),
        "configuration_report": {
            "api_config": api_config_loaded.model_dump(),
            "processor_config": processor_config.model_dump(),
        },
    }
