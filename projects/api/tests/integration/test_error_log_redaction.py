# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""
End-to-end check that error logging never leaks credentials.

Two things are verified by driving a real request through the app with a bearer
token attached:

1. Nothing the app logs to its normal sink contains the token.
2. Even with a serializing sink -- which renders loguru's ``extra`` payload, the
   way structured CloudWatch logging would -- the token is still absent. This is
   the case that matters, because the 5xx branch of the exception handler puts
   the request's header set into ``extra``.
"""

import io

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from loguru import logger

from metadata_harmonization_api.api.main import app

# Fake JWT-shaped value, only ever used to prove it does not reach the logs
TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.super-secret-payload.super-secret-signature"  # nosec B105
COOKIE_VALUE = "super-secret-cookie"


@pytest.fixture
def boom_client():
    """Client with a route that raises a 500 so the error handler runs."""

    @app.get("/__test_boom")
    async def boom():
        raise HTTPException(status_code=500, detail="boom")

    client = TestClient(app, raise_server_exceptions=False)
    yield client

    # Remove the temporary route so other tests see an unmodified app
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/__test_boom"]


@pytest.fixture
def captured_logs():
    """Capture loguru output, serialized so the `extra` payload is rendered too."""
    buffer = io.StringIO()
    sink_id = logger.add(buffer, level="DEBUG", serialize=True)

    yield buffer

    logger.remove(sink_id)


def test_bearer_token_absent_from_500_logs(boom_client, captured_logs):
    """A 500 must not write the Authorization or Cookie header value into logs."""
    response = boom_client.get(
        "/__test_boom",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Cookie": f"session={COOKIE_VALUE}",
            "User-Agent": "pytest-redaction-check",
        },
    )

    assert response.status_code == 500

    logged = captured_logs.getvalue()

    # Sanity check: the handler really did run and log the header set
    assert "__test_boom" in logged
    assert "headers" in logged

    # The credentials themselves never appear
    assert TOKEN not in logged
    assert "Bearer" not in logged
    assert COOKIE_VALUE not in logged

    # Redaction happened, and allow-listed headers survive so logs stay useful
    assert "[REDACTED]" in logged
    assert "pytest-redaction-check" in logged
