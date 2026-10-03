"""The externally triggered tick: auth, slot claiming, idempotency, and failure handling.

Score idempotency itself (a repeated sync never double-counts points) is covered by
`test_scoring.test_score_week_recomputes_points_and_is_idempotent`; these tests cover
the tick's own guarantee that a duplicate or late call never re-runs a claimed slot.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.jobs import tick
from app.models.job_execution import JobExecution

CHICAGO = ZoneInfo("America/Chicago")
TOKEN = "test-tick-token"


def sunday(hour: int, minute: int = 5) -> datetime:
    return datetime(2026, 10, 4, hour, minute, tzinfo=CHICAGO)  # a Sunday (CDT)


@pytest.fixture()
def calls(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Point the tick at the rollback-wrapped session and replace every job with a counter."""
    monkeypatch.setattr(
        tick,
        "SessionLocal",
        lambda: Session(bind=db_session.get_bind(), join_transaction_mode="create_savepoint"),
    )
    counts: dict[str, int] = {}

    def fake(name: str):
        def run() -> int:
            counts[name] = counts.get(name, 0) + 1
            return 7

        return run

    monkeypatch.setattr(tick, "JOB_FUNCTIONS", {name: fake(name) for name in tick.JOB_FUNCTIONS})
    return counts


def executions(db_session: Session) -> list[JobExecution]:
    return list(db_session.execute(select(JobExecution)).scalars())


# --- endpoint auth ---------------------------------------------------------------------


def test_tick_is_disabled_without_a_configured_token(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "tick_token", "")

    response = client.post("/api/v1/internal/tick", headers={"Authorization": "Bearer anything"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TICK_DISABLED"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong-token"},
        {"Authorization": TOKEN},  # no scheme
        {"Authorization": f"Basic {TOKEN}"},
        {"Authorization": "Bearer "},
    ],
)
def test_tick_rejects_missing_or_wrong_token(client, monkeypatch, calls, headers) -> None:
    monkeypatch.setattr(get_settings(), "tick_token", TOKEN)

    response = client.post("/api/v1/internal/tick", headers=headers)

    assert response.status_code == 401
    assert calls == {}  # no job work happened


def test_tick_accepts_the_token_and_runs_due_jobs(client, monkeypatch, calls) -> None:
    monkeypatch.setattr(get_settings(), "tick_token", TOKEN)

    response = client.post("/api/v1/internal/tick", headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["timezone"] == "America/Chicago"
    assert isinstance(body["cold_start"], bool)
    # The pick-lock slot is due every hour regardless of the day.
    assert any(j["job"] == "lock_expired_picks" and j["status"] == "success" for j in body["jobs"])


def test_tick_only_accepts_post(client) -> None:
    assert client.get("/api/v1/internal/tick").status_code == 405


# --- slot claiming and idempotency -----------------------------------------------------


def test_run_tick_runs_due_slots_once_and_records_them(db_session, calls) -> None:
    summary = tick.run_tick(sunday(10))

    assert [(j["job"], j["status"]) for j in summary["jobs"]] == [
        ("sunday_score_sync", "success"),
        ("lock_expired_picks", "success"),
    ]
    assert calls == {"sunday_score_sync": 1, "lock_expired_picks": 1}
    rows = {(e.job_name, e.slot_key): e for e in executions(db_session)}
    row = rows[("sunday_score_sync", "sunday_score_sync:2026-10-04T10")]
    assert row.status == "success"
    assert row.result_count == 7
    assert row.completed_at is not None


def test_duplicate_call_in_the_same_hour_is_a_no_op(db_session, calls) -> None:
    tick.run_tick(sunday(10, 5))
    second = tick.run_tick(sunday(10, 5))

    assert {j["status"] for j in second["jobs"]} == {"skipped"}
    assert calls == {"sunday_score_sync": 1, "lock_expired_picks": 1}
    assert len(executions(db_session)) == 2


def test_late_call_inside_the_hour_does_not_rerun_a_claimed_slot(db_session, calls) -> None:
    tick.run_tick(sunday(23, 0))
    late = tick.run_tick(sunday(23, 1))

    assert {j["status"] for j in late["jobs"]} == {"skipped"}
    assert calls["sunday_score_sync"] == 1


def test_late_call_runs_a_slot_nobody_claimed(db_session, calls) -> None:
    # The 23:00 tick never happened; a tick at 23:01 still fires the slot once.
    summary = tick.run_tick(sunday(23, 1))

    assert ("sunday_score_sync", "success") in [(j["job"], j["status"]) for j in summary["jobs"]]
    assert calls["sunday_score_sync"] == 1


def test_the_next_hour_is_a_new_slot(db_session, calls) -> None:
    tick.run_tick(sunday(10))
    tick.run_tick(sunday(11))

    assert calls["sunday_score_sync"] == 2


def test_no_sunday_sync_after_the_window_closes(db_session, calls) -> None:
    summary = tick.run_tick(datetime(2026, 10, 5, 0, 5, tzinfo=CHICAGO))  # Monday 00:05

    assert "sunday_score_sync" not in [j["job"] for j in summary["jobs"]]


# --- failure handling ------------------------------------------------------------------


def test_a_failing_job_is_recorded_and_does_not_stop_the_tick(
    db_session, calls, monkeypatch
) -> None:
    def boom() -> int:
        raise RuntimeError("espn is down")

    monkeypatch.setitem(tick.JOB_FUNCTIONS, "sunday_score_sync", boom)

    summary = tick.run_tick(sunday(10))

    statuses = {j["job"]: j["status"] for j in summary["jobs"]}
    assert statuses == {"sunday_score_sync": "failed", "lock_expired_picks": "success"}
    failed = next(e for e in executions(db_session) if e.job_name == "sunday_score_sync")
    assert failed.status == "failed"
    assert failed.error_message == "espn is down"
    assert failed.completed_at is not None


def test_a_failed_slot_is_retried_until_it_succeeds(db_session, calls, monkeypatch) -> None:
    def boom() -> int:
        raise RuntimeError("espn is down")

    monkeypatch.setitem(tick.JOB_FUNCTIONS, "sunday_score_sync", boom)
    tick.run_tick(sunday(10))
    monkeypatch.setitem(tick.JOB_FUNCTIONS, "sunday_score_sync", lambda: 7)

    retry = tick.run_tick(sunday(10, 30))

    statuses = {j["job"]: j["status"] for j in retry["jobs"]}
    assert statuses["sunday_score_sync"] == "success"
    assert statuses["lock_expired_picks"] == "skipped"  # already succeeded, not re-run
    row = next(e for e in executions(db_session) if e.job_name == "sunday_score_sync")
    assert (row.status, row.error_message) == ("success", None)


def test_stale_running_slot_is_reclaimed_but_a_fresh_one_is_not(db_session, calls) -> None:
    tick.run_tick(sunday(10))
    row = next(e for e in executions(db_session) if e.job_name == "sunday_score_sync")
    row.status = "running"
    row.completed_at = None
    row.started_at = datetime.now(timezone.utc) - timedelta(minutes=3)
    db_session.flush()

    fresh = tick.run_tick(sunday(10, 8))  # presumed still running
    assert next(j for j in fresh["jobs"] if j["job"] == "sunday_score_sync")["status"] == "skipped"

    row.started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    db_session.flush()
    stale = tick.run_tick(sunday(10, 30))  # the run died
    assert next(j for j in stale["jobs"] if j["job"] == "sunday_score_sync")["status"] == "success"


def test_cold_start_flag_reflects_process_age(db_session, calls, monkeypatch) -> None:
    monkeypatch.setattr(tick, "_PROCESS_STARTED", tick.time.monotonic())
    assert tick.run_tick(sunday(14))["cold_start"] is True

    monkeypatch.setattr(
        tick, "_PROCESS_STARTED", tick.time.monotonic() - tick.COLD_START_WINDOW_SECONDS - 1
    )
    assert tick.run_tick(sunday(15))["cold_start"] is False
