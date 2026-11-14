"""Append-only writes to the UsageEvent model. No business logic here — see app.services."""

import uuid
from collections.abc import Mapping, Sequence

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
