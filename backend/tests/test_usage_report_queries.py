"""Runs the usage-report skill's SQL (.claude/skills/usage-report/queries.sql) on seeded rows."""

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.usage_event import UsageEvent
from app.models.user import User

QUERIES_FILE = (
    Path(__file__).resolve().parents[2] / ".claude" / "skills" / "usage-report" / "queries.sql"
)


def _queries(exclude: str) -> dict[str, str]:
    sql = QUERIES_FILE.read_text(encoding="utf-8").replace("{{EXCLUDE}}", exclude)
    parts = re.split(r"^-- name: (\w+)\s*$", sql, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def _at(day: int, hour: int = 15, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc)


def _event(
    user: User | None, action: str, when: datetime, **metadata: str
) -> AuditLog | UsageEvent:
    """Logins live in audit_log; every other action is a usage_events row."""
    if action == "login":
        return AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity="auth",
            event_metadata=metadata or None,
            created_at=when,
        )
    assert user is not None
    return UsageEvent(
        user_id=user.id,
        action=action,
        path=metadata.get("path"),
        section=metadata.get("section"),
        device=metadata.get("device"),
        created_at=when,
    )


@pytest.fixture()
def seeded(db_session: Session) -> dict[str, User]:
    users = {
        key: User(google_id=f"g-{key}", email=f"{key}@example.com", display_name=key.title())
        for key in ("alice", "bob", "cara", "tester")
    }
    db_session.add_all(users.values())
    db_session.flush()
    a, b, t = users["alice"], users["bob"], users["tester"]
    db_session.add_all(
        [
            _event(a, "login", _at(8)),
            _event(a, "login", _at(10)),
            _event(a, "session_start", _at(10), device="phone"),
            _event(a, "page_view", _at(10), path="/picks"),
            _event(a, "section_open", _at(10), section="standings"),
            # three heartbeats in two distinct 30-second buckets
            _event(a, "heartbeat", _at(10, 15, 0), path="/"),
            _event(a, "heartbeat", _at(10, 15, 0), path="/"),
            _event(a, "heartbeat", _at(10, 15, 1), path="/"),
            _event(b, "login", _at(9)),
            _event(t, "login", _at(9)),
            _event(None, "login", _at(9)),
        ]
    )
    db_session.flush()
    return users


def _run(db_session: Session, name: str, exclude: str = "'tester@example.com'") -> list[dict]:
    rows = db_session.execute(text(_queries(exclude)[name])).mappings().all()
    return [dict(r) for r in rows]


def test_every_named_query_runs(db_session: Session, seeded: dict[str, User]) -> None:
    for name in _queries("''"):
        _run(db_session, name)


def test_users_excludes_test_accounts(db_session: Session, seeded: dict[str, User]) -> None:
    names = {r["display_name"] for r in _run(db_session, "users")}
    assert names == {"Alice", "Bob", "Cara"}


def test_logins_and_deleted_users(db_session: Session, seeded: dict[str, User]) -> None:
    by_user = {r["user_id"]: r["login_count"] for r in _run(db_session, "logins_per_user")}
    assert by_user == {str(seeded["alice"].id): 2, str(seeded["bob"].id): 1}


def test_active_time_counts_distinct_30s_buckets(
    db_session: Session, seeded: dict[str, User]
) -> None:
    rows = _run(db_session, "active_buckets_per_user")
    assert [(r["user_id"], r["buckets"]) for r in rows] == [(str(seeded["alice"].id), 2)]


def test_dau_is_zero_filled_and_excludes_tester(
    db_session: Session, seeded: dict[str, User]
) -> None:
    by_day = {r["day"]: r["users"] for r in _run(db_session, "dau")}
    assert by_day == {"2026-11-08": 1, "2026-11-09": 1, "2026-11-10": 1}


def test_feature_adoption_marks_unused_features(
    db_session: Session, seeded: dict[str, User]
) -> None:
    by_feature = {r["feature"]: r["users"] for r in _run(db_session, "feature_adoption")}
    assert by_feature["Picks page"] == 1
    assert by_feature["Standings section"] == 1
    assert by_feature["Profile section"] == 0


def test_never_returned_and_no_data_yet(db_session: Session, seeded: dict[str, User]) -> None:
    status = {r["user_id"]: r["status"] for r in _run(db_session, "never_returned")}
    assert status == {
        str(seeded["bob"].id): "never returned",
        str(seeded["cara"].id): "no data yet",
    }


def test_never_returned_uses_activity_when_there_is_no_login_row(
    db_session: Session, seeded: dict[str, User]
) -> None:
    """Members who stay signed in via the refresh cookie have no login row."""
    dan = User(google_id="g-dan", email="dan@example.com", display_name="Dan")
    erin = User(google_id="g-erin", email="erin@example.com", display_name="Erin")
    db_session.add_all([dan, erin])
    db_session.flush()
    db_session.add_all(
        [
            _event(dan, "session_start", _at(10), device="phone"),
            _event(erin, "session_start", _at(10), device="desktop"),
            _event(erin, "page_view", _at(11), path="/picks"),
        ]
    )
    db_session.flush()

    status = {r["user_id"]: r["status"] for r in _run(db_session, "never_returned")}
    assert status[str(dan.id)] == "never returned"  # active one day only, not 'no data yet'
    assert str(erin.id) not in status  # came back on a later day


def test_activity_without_login_rows_still_counts_in_dau(
    db_session: Session, seeded: dict[str, User]
) -> None:
    dan = User(google_id="g-dan", email="dan@example.com", display_name="Dan")
    db_session.add(dan)
    db_session.flush()
    db_session.add(_event(dan, "page_view", _at(12), path="/picks"))
    db_session.flush()

    by_day = {r["day"]: r["users"] for r in _run(db_session, "dau")}
    assert by_day["2026-11-12"] == 1
    assert by_day["2026-11-11"] == 0  # zero-filled gap
    wau = {r["week_start"]: r["users"] for r in _run(db_session, "wau")}
    assert wau["2026-11-09"] == 3  # Alice, Bob (logins) and Dan (page_view only)
