"""Basic smoke test for the health endpoint."""

from fastapi.testclient import TestClient

from app.core.config import Settings
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
            "scheduler": expected_scheduler,
        },
        "message": None,
    }


def test_lifespan_can_disable_scheduler(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_scheduler", False)

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
