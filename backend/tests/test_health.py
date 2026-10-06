"""Basic smoke test for the health endpoint."""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import health
from app.core.config import Settings
from app.db.schema_validator import _validate_table
from app.db.session import Base
from app.main import app
from app.models import NflGame, NflWeek, Pick, User
from app.models.enums import WeekStatus

client = TestClient(app)


def test_health_check_returns_healthy_status() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "healthy"}, "message": None}


def test_metrics_on_an_empty_database_are_null_and_zero(client) -> None:
    response = client.get("/api/v1/health/metrics")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "last_activity_at": None,
        "data_freshness_at": None,
        "picks_total": 0,
        "games_total": 0,
    }


def test_metrics_expose_only_aggregates(client, db_session) -> None:
    synced = datetime(2026, 9, 14, 18, 30, tzinfo=timezone.utc)
    user = User(
        google_id=f"m-{uuid.uuid4().hex}",
        email=f"{uuid.uuid4().hex}@example.com",
        display_name="Secret Name",
    )
    week = NflWeek(
        season=2026,
        week_number=1,
        start_date=synced,
        end_date=synced,
        status=WeekStatus.COMPLETE,
    )
    db_session.add_all([user, week])
    db_session.flush()
    game = NflGame(
        week_id=week.id,
        espn_game_id=f"m-{uuid.uuid4().hex}",
        kickoff_time=synced,
        away_team="BUF",
        home_team="KC",
        last_synced=synced,
    )
    db_session.add(game)
    db_session.flush()
    db_session.add(Pick(user_id=user.id, game_id=game.id, picked_team="KC", confidence_value=7))
    db_session.flush()

    response = client.get("/api/v1/health/metrics")

    data = response.json()["data"]
    assert set(data) == {"last_activity_at", "data_freshness_at", "picks_total", "games_total"}
    assert data["picks_total"] == 1 and data["games_total"] == 1
    assert data["data_freshness_at"] == synced.isoformat()
    assert data["last_activity_at"] is not None
    assert "Secret Name" not in response.text and "KC" not in response.text


def test_readiness_check_verifies_database_and_reports_external_scheduler(client) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "status": "ready",
            "database": "healthy",
            "schema": "valid",
            "scheduler": "external",
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
async def test_startup_schema_drift_prevents_app_startup(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.validate_schema",
        lambda _db: [{"kind": "missing_column", "table": "users", "column": "email"}],
    )

    with pytest.raises(RuntimeError, match="schema drift"):
        async with app.router.lifespan_context(app):
            pass


def test_settings_normalize_fly_postgres_urls() -> None:
    for database_url in (
        "postgres://user:password@db.internal:5432/pool",
        "postgresql://user:password@db.internal:5432/pool",
    ):
        settings = Settings(database_url=database_url)
        assert settings.database_url.startswith("postgresql+psycopg://")
