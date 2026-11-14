"""Writes to the UsageEvent model (append, age-based delete). No business logic here."""

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.usage_event import UsageEvent


def create_many(db: Session, user_id: uuid.UUID, rows: Sequence[Mapping[str, str | None]]) -> None:
    db.add_all(
        UsageEvent(
            user_id=user_id,
            action=row["action"],
            path=row.get("path"),
            section=row.get("section"),
            device=row.get("device"),
        )
        for row in rows
    )
    db.flush()


def delete_older_than(db: Session, cutoff: datetime) -> int:
    """Delete usage events created before `cutoff`; returns the number removed."""
    result = db.execute(delete(UsageEvent).where(UsageEvent.created_at < cutoff))
    return result.rowcount
