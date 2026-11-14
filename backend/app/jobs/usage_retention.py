"""Daily retention for usage_events: drop client telemetry older than USAGE_RETENTION_DAYS."""

from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.repositories import usage_event_repository

USAGE_RETENTION_DAYS = 180


def prune_usage_events() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=USAGE_RETENTION_DAYS)
    with SessionLocal() as db:
        deleted = usage_event_repository.delete_older_than(db, cutoff)
        db.commit()
    return deleted
