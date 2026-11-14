"""The daily usage_events retention job."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs import usage_retention
from app.models.audit_log import AuditLog
from app.models.usage_event import UsageEvent


def test_prune_deletes_only_rows_past_retention(
    db_session: Session, owner_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        usage_retention,
        "SessionLocal",
        lambda: Session(bind=db_session.get_bind(), join_transaction_mode="create_savepoint"),
    )
    now = datetime.now(timezone.utc)
    old_usage = UsageEvent(
        user_id=owner_user.id, action="page_view", created_at=now - timedelta(days=721)
    )
    fresh_usage = UsageEvent(
        user_id=owner_user.id, action="page_view", created_at=now - timedelta(days=719)
    )
    old_audit = AuditLog(
        user_id=owner_user.id, action="x", entity="y", created_at=now - timedelta(days=900)
    )
    db_session.add_all([old_usage, fresh_usage, old_audit])
    db_session.flush()

    assert usage_retention.prune_usage_events() == 1
    assert usage_retention.prune_usage_events() == 0

    db_session.expire_all()
    assert [e.id for e in db_session.execute(select(UsageEvent)).scalars()] == [fresh_usage.id]
    assert db_session.get(AuditLog, old_audit.id) is not None
