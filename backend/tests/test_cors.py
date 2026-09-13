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
def test_auth_preflight_allows_local_frontend(
    path: str, method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This test boots the real app lifespan against the CI database's default
    # `public` schema, which never has migrations applied (tests otherwise run
    # against an isolated, freshly created-from-models schema -- see conftest's
    # `db_engine` fixture). Skip the startup schema-drift check accordingly,
    # the same way test_health.py's test_lifespan_can_disable_scheduler does.
    monkeypatch.setattr("app.main._validate_startup_schema", lambda: None)

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
