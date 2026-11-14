"""Tests for the UsageEvent model: round trip and user-delete cascade."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import UsageEvent, User


def _make_user(db_session: Session) -> User:
    user = User(google_id="g-usage", email="usage@example.com", display_name="usage")
    db_session.add(user)
    db_session.flush()
    return user


def test_usage_event_round_trip(db_session: Session) -> None:
    user = _make_user(db_session)
    event = UsageEvent(user_id=user.id, action="page_view", path="/picks")
    db_session.add(event)
    db_session.flush()
    db_session.expire_all()

    loaded = db_session.get(UsageEvent, event.id)

    assert loaded is not None
    assert loaded.user_id == user.id
    assert loaded.action == "page_view"
    assert loaded.path == "/picks"
    assert loaded.section is None
    assert loaded.device is None
    assert loaded.created_at is not None


def test_deleting_user_deletes_their_usage_events(db_session: Session) -> None:
    user = _make_user(db_session)
    db_session.add_all(
        [
            UsageEvent(user_id=user.id, action="page_view", path="/picks"),
            UsageEvent(user_id=user.id, action="section_view", section="picks"),
        ]
    )
    db_session.flush()

    db_session.delete(user)
    db_session.flush()
    db_session.expire_all()

    count = db_session.execute(select(func.count()).select_from(UsageEvent)).scalar_one()
    assert count == 0
