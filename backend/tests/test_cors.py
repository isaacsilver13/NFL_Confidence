"""Regression tests for browser preflight requests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/v1/auth/me", "GET"),
        ("/api/v1/auth/dev-login", "POST"),
    ],
)
def test_auth_preflight_allows_local_frontend(path: str, method: str) -> None:
    with TestClient(app) as client:
        response = client.options(
            path,
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
