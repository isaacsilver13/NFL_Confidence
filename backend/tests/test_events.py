"""Tests for the usage events endpoint (POST /api/v1/events)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models.audit_log import AuditLog
from app.models.usage_event import UsageEvent
from app.models.user import User


@pytest.fixture()
def member(db_session: Session) -> User:
    user = User(google_id="g-events", email="events@example.com", display_name="Events User")
    db_session.add(user)
    db_session.commit()
    return user


def _auth(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _post(client, user: User, events: list[dict]):
    return client.post("/api/v1/events", json={"events": events}, headers=_auth(user))


def _rows(db_session: Session) -> list[UsageEvent]:
    return list(db_session.execute(select(UsageEvent)).scalars())


def test_requires_auth(client) -> None:
    response = client.post("/api/v1/events", json={"events": [{"action": "session_start"}]})
    assert response.status_code == 401


def test_records_events(client, db_session: Session, member: User) -> None:
    response = _post(
        client,
        member,
        [
            {"action": "session_start", "metadata": {"device": "phone"}},
            {"action": "page_view", "metadata": {"path": "/picks"}},
            {"action": "heartbeat", "metadata": {"path": "/"}},
            {"action": "section_open", "metadata": {"section": "standings"}},
        ],
    )

    assert response.status_code == 204
    rows = _rows(db_session)
    assert {r.action for r in rows} == {"session_start", "page_view", "heartbeat", "section_open"}
    assert all(r.user_id == member.id for r in rows)
    by_action = {r.action: r for r in rows}
    assert by_action["page_view"].path == "/picks"
    assert by_action["section_open"].section == "standings"


def test_batch_maps_each_action_to_typed_columns(client, db_session: Session, member: User) -> None:
    _post(
        client,
        member,
        [
            {"action": "session_start", "metadata": {"device": "phone"}},
            {"action": "page_view", "metadata": {"path": "/picks"}},
            {"action": "heartbeat", "metadata": {"path": "/"}},
            {"action": "section_open", "metadata": {"section": "standings"}},
        ],
    )

    by_action = {r.action: r for r in _rows(db_session)}
    typed = lambda r: (r.device, r.path, r.section)  # noqa: E731
    assert typed(by_action["session_start"]) == ("phone", None, None)
    assert typed(by_action["page_view"]) == (None, "/picks", None)
    assert typed(by_action["heartbeat"]) == (None, "/", None)
    assert typed(by_action["section_open"]) == (None, None, "standings")


def test_client_events_do_not_write_audit_log(client, db_session: Session, member: User) -> None:
    assert (
        _post(client, member, [{"action": "page_view", "metadata": {"path": "/"}}]).status_code
        == 204
    )
    usage_audit = db_session.execute(select(AuditLog).where(AuditLog.entity == "usage")).scalars()
    assert list(usage_audit) == []


def test_rejects_unknown_action(client, db_session: Session, member: User) -> None:
    assert _post(client, member, [{"action": "purchase"}]).status_code == 422
    assert _rows(db_session) == []


def test_login_action_not_accepted_from_client(client, db_session: Session, member: User) -> None:
    assert _post(client, member, [{"action": "login"}]).status_code == 422
    assert _rows(db_session) == []


@pytest.mark.parametrize("path", ["/join?code=ABC123", "/#standings", "picks", ""])
def test_rejects_query_string_hash_or_relative_path(
    client, db_session: Session, member: User, path: str
) -> None:
    response = _post(client, member, [{"action": "page_view", "metadata": {"path": path}}])
    assert response.status_code == 422
    assert _rows(db_session) == []


@pytest.mark.parametrize(
    "event",
    [
        {"action": "section_open", "metadata": {"section": "admin"}},
        {"action": "session_start", "metadata": {"device": "toaster"}},
        {"action": "page_view", "metadata": {"path": "/", "email": "a@b.c"}},
        {"action": "page_view"},
        {"action": "session_start", "metadata": {"path": "/"}},
    ],
)
def test_rejects_bad_metadata(client, db_session: Session, member: User, event: dict) -> None:
    assert _post(client, member, [event]).status_code == 422
    assert _rows(db_session) == []


def test_rejects_more_than_5_events(client, db_session: Session, member: User) -> None:
    events = [{"action": "heartbeat", "metadata": {"path": "/"}}] * 6
    assert _post(client, member, events).status_code == 422
    assert _rows(db_session) == []


def test_rejects_empty_batch(client, member: User) -> None:
    assert _post(client, member, []).status_code == 422
