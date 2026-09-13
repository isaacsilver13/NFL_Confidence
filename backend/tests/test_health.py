"""Basic smoke test for the health endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.api import health
from app.core.config import Settings
from app.db.schema_validator import _validate_table
from app.db.session import Base
from app.main import app, settings

client = TestClient(app)


def test_health_check_returns_healthy_status() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "healthy"}, "message": None}


def test_readiness_check_verifies_database_and_scheduler(client) -> None:
    response = client.get("/api/v1/health/ready")
    expected_scheduler = "running" if settings.enable_scheduler else "disabled"

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "status": "ready",
            "database": "healthy",
            "schema": "valid",
            "scheduler": expected_scheduler,
        },
        "message": None,
    }


def test_readiness_check_reports_schema_drift(client, monkeypatch) -> None:
    monkeypatch.setattr(
        health,
        "validate_schema",
        lambda _db: [
            {"kind": "missing_table", "table": "refresh_tokens"},
        ],
    )

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "SCHEMA_DRIFT",
            "message": "The database schema does not match the application.",
            "details": [{"kind": "missing_table", "table": "refresh_tokens"}],
        }
    }


def test_validate_schema_reports_missing_objects(monkeypatch) -> None:
    class FakeInspector:
        def has_table(self, table_name: str) -> bool:
            return False

    monkeypatch.setattr("app.db.schema_validator.inspect", lambda _bind: FakeInspector())

    class FakeSession:
        def get_bind(self):
            return object()

    issues = _validate_table(Base.metadata.tables["refresh_tokens"], FakeInspector())

    assert {issue["table"] for issue in issues} == {"refresh_tokens"}
    assert issues[0]["kind"] == "missing_table"


@pytest.mark.asyncio
async def test_startup_schema_drift_prevents_scheduler_creation(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.validate_schema",
        lambda _db: [{"kind": "missing_column", "table": "users", "column": "email"}],
    )

    with pytest.raises(RuntimeError, match="schema drift"):
        async with app.router.lifespan_context(app):
            pass


def test_lifespan_can_disable_scheduler(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_scheduler", False)
    monkeypatch.setattr("app.main._validate_startup_schema", lambda: None)

    with TestClient(app):
        assert app.state.scheduler is None
        assert app.state.scheduler_enabled is False


def test_settings_normalize_fly_postgres_urls() -> None:
    for database_url in (
        "postgres://user:password@db.internal:5432/pool",
        "postgresql://user:password@db.internal:5432/pool",
    ):
        settings = Settings(database_url=database_url)
        assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_can_disable_scheduler(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_SCHEDULER", "false")
    settings = Settings(_env_file=None)

    assert settings.enable_scheduler is False
