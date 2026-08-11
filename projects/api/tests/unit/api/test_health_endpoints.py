# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Unit tests for health check endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from metadata_harmonization_api.api.v1.routes.health import router


client = TestClient(FastAPI(routes=router.routes))


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_detailed_health_check(self):
        response = client.get("/health/detailed")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "api_config" in body["configuration_report"]
        assert "processor_config" in body["configuration_report"]
