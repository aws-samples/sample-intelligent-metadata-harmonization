# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Router for API."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from loguru import logger

from metadata_harmonization_api.api.auth import OIDCHTTPBearer
from metadata_harmonization_api.api.v1.routes.metadata import validation as v1_metadata_endpoints
from metadata_harmonization_api.api.v1.routes import health as health_endpoints
from metadata_harmonization_api.config import api_config

# Add security dependencies if ENABLE_AUTH - use metadata config for auth
dependencies = [Depends(OIDCHTTPBearer())] if api_config.metadata.enable_auth else []

router = APIRouter()

# Register health check endpoints (no auth required)
logger.info("Registering health check endpoints...")
router.include_router(
    health_endpoints.router,
    prefix="/api/v1",
    tags=["health"],
)

# Register metadata validation endpoints
logger.info("Registering metadata validation endpoints...")
logger.info(f"Routes in module: {list(v1_metadata_endpoints.router.routes)}")
router.include_router(
    v1_metadata_endpoints.router,
    prefix="/api/v1/metadata",
    tags=["metadata"],
    dependencies=dependencies,
)

logger.info("All registered routes:")
for route in router.routes:
    # Not every entry in `router.routes` is a plain route. Since fastapi 0.137.0,
    # `include_router` leaves `_IncludedRouter` markers here, which have no `.path` --
    # reading it unguarded raised AttributeError at import time and took the whole app
    # down. Use getattr so a debug log line can never break startup.
    path = getattr(route, "path", None)
    if path is None:
        continue
    logger.info(f"Path: {path}, Methods: {getattr(route, 'methods', None)}")


@router.get("/api/health")
async def health_check() -> JSONResponse:
    """Health check path.

    Note: This endpoint needs to match the path in the config.yaml file.
    """
    content = {"status": "OK"}

    return JSONResponse(content=content, status_code=200)
