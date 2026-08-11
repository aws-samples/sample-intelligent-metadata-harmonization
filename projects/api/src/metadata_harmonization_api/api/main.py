# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""REST API."""

import time
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger

from metadata_harmonization_api.api.router import router
from metadata_harmonization_api.config import api_config, load_api_configuration
from metadata_harmonization_api.utils.log_redaction import redact_headers
from metadata_harmonization_api.utils.logging import setup_unified_logging
from metadata_harmonization_api.utils.shared_dependencies import get_ddb_manager

# Set up unified logging for both REST API and MCP server
setup_unified_logging(api_config.log_level)

# Create MCP server first (outside of lifespan)
mcp_server = None
mcp_app = None

try:
    # Load configuration for MCP server
    api_config_loaded, processor_config = load_api_configuration()

    mcp_enabled = getattr(api_config_loaded.metadata, "mcp_enabled", True)

    if mcp_enabled:
        logger.info("Creating MCP server...")

        # Create MCP server using new pattern
        from metadata_harmonization_api.mcp.server import create_mcp_server

        mcp_server = create_mcp_server(processor_config)

        # Create ASGI app from MCP server
        mcp_app = mcp_server.http_app(path="/mcp")

        logger.info("MCP server created successfully")
    else:
        logger.info("MCP server disabled in configuration")

except Exception as e:
    logger.error(f"Failed to create MCP server: {e}")
    logger.warning("Continuing without MCP server")


@asynccontextmanager
async def core_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan for FastAPI."""
    logger.info("Starting Metadata Harmonization API...")

    # Load configuration with environment detection
    try:
        api_config_loaded, processor_config = load_api_configuration()
        logger.info("Successfully loaded API and processor configurations")

        # Log configuration status
        environment = processor_config.local_development_mode and "local" or "cloud"
        logger.info(f"Running in {environment} mode")
        logger.info(f"Job status saver: {processor_config.job_status_saver_type}")
        logger.info(f"Result saver: {processor_config.result_saver_type}")
        logger.info(f"Session type: {processor_config.session_saver_type}")
        logger.info(f"Authentication enabled: {api_config_loaded.metadata.enable_auth}")

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise RuntimeError(f"Configuration loading failed: {e}")

    # Initialize shared dependencies using dependency injection system
    # Only initialize DynamoDB manager if it's actually being used
    ddb_manager = None
    if processor_config.job_status_saver_type == "dynamodb":
        try:
            logger.info("Initializing DynamoDB manager (required for job status storage)")
            ddb_manager = get_ddb_manager()
            await ddb_manager.start()

            logger.info("Successfully initialized DynamoDB manager")

        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB manager: {e}")
            raise RuntimeError(f"DynamoDB manager initialization failed: {e}")
    else:
        logger.info(
            f"Skipping DynamoDB manager initialization (job_status_saver_type={processor_config.job_status_saver_type})"
        )

    # Store only essential configs in app state for dependency injection
    app.state.api_config = api_config_loaded
    app.state.processor_config = processor_config

    # Store MCP server in app state if available
    if mcp_server:
        app.state.mcp_server = mcp_server
        app.state.mcp_mount_path = ""
        logger.info("MCP server stored in app state")

    logger.info("API startup completed successfully")
    yield

    # Clean up resources
    logger.info("Shutting down API...")

    # Log MCP server shutdown if it was running
    if hasattr(app.state, "mcp_server") and app.state.mcp_server:
        from metadata_harmonization_api.utils.logging import log_mcp_server_shutdown

        log_mcp_server_shutdown("metadata-harmonization-mcp-server")

    # Clean up AWS clients (only if initialized)
    if ddb_manager is not None:
        try:
            await ddb_manager.stop()
            logger.info("Successfully cleaned up DynamoDB manager")
        except Exception as e:
            logger.warning(f"Error during DynamoDB cleanup: {e}")
    else:
        logger.info("No DynamoDB manager to clean up")

    # Clear shared dependency cache
    from metadata_harmonization_api.utils.shared_dependencies import clear_dependency_cache

    clear_dependency_cache()
    logger.info("Cleared shared dependency cache")

    logger.info("API shutdown completed")


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        # 1) Start your core app resources first
        await stack.enter_async_context(core_lifespan(app))

        # 2) Then (optionally) start MCP’s lifespan so it can use core’s resources
        if mcp_app and hasattr(mcp_app, "lifespan"):
            await stack.enter_async_context(mcp_app.lifespan(app))

        # App is ready
        yield
        # Shutdown order will be: MCP first, then your core teardown.


# Create FastAPI app
app = FastAPI(
    lifespan=combined_lifespan,
    debug=api_config.log_level == "DEBUG",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
)

# Mount MCP server if available
if mcp_app:
    app.mount("/agent", mcp_app)
    logger.info("MCP server mounted at")
app.include_router(router)


# Global exception handler for HTTPException to ensure 500 errors are logged
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global exception handler to log all HTTP exceptions, especially 500 errors."""

    # Get request context for logging
    request_id = getattr(request.state, "request_id", "unknown")
    user_id = getattr(request.state, "user_id", "unknown")

    # FORCE log to stdout for debugging - this should always appear
    print(f"[EXCEPTION HANDLER] HTTP {exc.status_code} error: {exc.detail}")
    print(f"[EXCEPTION HANDLER] Path: {request.method} {request.url.path}")
    print(f"[EXCEPTION HANDLER] Request ID: {request_id}, User: {user_id}")

    # Log 500-level errors with full details
    if exc.status_code >= 500:
        # Force critical level logging
        print("[CRITICAL ERROR] 500-level error occurred!")
        logger.critical(f"CRITICAL: HTTP {exc.status_code} error in {request.method} {request.url.path}: {exc.detail}")
        logger.error(
            f"HTTP {exc.status_code} error in {request.method} {request.url.path}: {exc.detail}",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "status_code": exc.status_code,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "error_detail": exc.detail,
                "headers": redact_headers(request.headers),
            },
        )
    elif exc.status_code >= 400:
        # Log 400-level errors with less detail
        print(f"[CLIENT ERROR] 400-level error: {exc.status_code}")
        logger.warning(
            f"HTTP {exc.status_code} error in {request.method} {request.url.path}: {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "method": request.method,
                "path": request.url.path,
                "error_detail": exc.detail,
            },
        )

    # Return the original HTTPException response
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=getattr(exc, "headers", None)
    )


# Global exception handler for any unhandled exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for any unhandled exceptions."""

    request_id = getattr(request.state, "request_id", "unknown")
    user_id = getattr(request.state, "user_id", "unknown")

    # FORCE log to stdout for debugging
    print(f"[UNHANDLED EXCEPTION] {type(exc).__name__}: {str(exc)}")
    print(f"[UNHANDLED EXCEPTION] Path: {request.method} {request.url.path}")
    print(f"[UNHANDLED EXCEPTION] Request ID: {request_id}, User: {user_id}")

    # Log with logger as well
    logger.critical(f"UNHANDLED EXCEPTION: {type(exc).__name__}: {str(exc)}")
    logger.exception(f"Unhandled exception in {request.method} {request.url.path}")

    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# MCP server info endpoint (separate from mounted MCP server)
@app.get("/api/mcp/info")
async def get_mcp_info():
    """Get MCP server information and available tools."""
    if hasattr(app.state, "mcp_server") and app.state.mcp_server:
        from metadata_harmonization_api.mcp.server import get_mcp_server_info

        return await get_mcp_server_info(app.state.mcp_server)
    else:
        return {"status": "disabled", "message": "MCP server is not enabled"}


# MCP server metrics endpoint
@app.get("/api/mcp/metrics")
async def get_mcp_metrics():
    """Get MCP server performance metrics."""
    if hasattr(app.state, "mcp_server") and app.state.mcp_server:
        from metadata_harmonization_api.utils.logging import get_mcp_metrics, log_mcp_metrics

        # Log current metrics
        log_mcp_metrics()

        # Return metrics data
        metrics = get_mcp_metrics()
        return {"status": "enabled", "metrics": metrics, "mount_path": getattr(app.state, "mcp_mount_path", "/mcp")}
    else:
        return {"status": "disabled", "message": "MCP server is not enabled", "metrics": None}


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://d3pt2kypvv4zgl.cloudfront.net", "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Request-ID",
    ],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def process_request(request: Request, call_next: Any) -> Any:
    """Middleware for processing all HTTP requests."""
    request_id = str(uuid4())  # Unique ID for this request
    request.state.request_id = request_id  # Store for exception handler
    if not hasattr(request.state, "user_id"):
        request.state.user_id = "local-test-user"

    tic = time.time()

    # Determine if this is an MCP request
    is_mcp_request = request.url.path.startswith("/mcp")
    client_id = request.headers.get("x-client-id", "unknown")

    with logger.contextualize(
        request_id=request_id,
        endpoint=request.url.path,
        event="rest_api_request" if not is_mcp_request else "mcp_http_request",
        client_id=client_id,
    ):
        try:
            # Never log any part of the token itself - presence is all that is useful
            logger.debug(f"Authorization header present: {'authorization' in request.headers}")

            # Log request start with appropriate context
            if is_mcp_request:
                logger.debug(
                    "MCP HTTP request started",
                    extra={
                        "method": request.method,
                        "client_id": client_id,
                        "user_agent": request.headers.get("user-agent", "unknown"),
                    },
                )
            else:
                logger.debug("REST API request started")

            # Update request state
            request.state.logger = logger

            # Attempt to call the next request handler
            response = await call_next(request)

            # If response is successful, log the finish status
            duration = time.time() - tic
            status_code = response.status_code if hasattr(response, "status_code") else 200

            # Log different levels based on status code
            if status_code >= 500:
                log_level = "error"
                log_message = f"Request failed with {status_code} (took {duration:.2f} seconds)"
            elif status_code >= 400:
                log_level = "warning"
                log_message = f"Request returned {status_code} (took {duration:.2f} seconds)"
            else:
                log_level = "debug"
                log_message = f"Request completed with {status_code} (took {duration:.2f} seconds)"

            if is_mcp_request:
                getattr(logger, log_level)(
                    f"MCP HTTP {log_message}",
                    extra={"duration_seconds": round(duration, 3), "status_code": status_code, "client_id": client_id},
                )
            else:
                getattr(logger, log_level)(
                    f"REST API {log_message}",
                    extra={"duration_seconds": round(duration, 3), "status_code": status_code},
                )

        except Exception as e:
            # In case of an exception, log the error and prepare a generic response
            duration = time.time() - tic

            if is_mcp_request:
                logger.exception(
                    "MCP HTTP request error (took {duration:.2f} seconds): {error}",
                    duration=duration,
                    error=str(e),
                    extra={"client_id": client_id},
                )
            else:
                logger.exception(
                    "REST API request error (took {duration:.2f} seconds): {error}",
                    duration=duration,
                    error=str(e),
                )

            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        # Add the unique request ID to the response headers
        if response is not None and isinstance(response, Response):
            response.headers["X-Request-ID"] = request_id

    return response
