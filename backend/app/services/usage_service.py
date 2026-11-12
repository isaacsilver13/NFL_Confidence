"""Usage tracking: record client-reported events and server-side logins in audit_log."""

import uuid

from sqlalchemy.orm import Session

from app.repositories import audit_log_repository
from app.schemas.usage import EventIn

USAGE_ENTITY = "usage"


def record_events(db: Session, user_id: uuid.UUID, events: list[EventIn]) -> None:
    for event in events:
        audit_log_repository.create(
            db,
            user_id=user_id,
            action=event.action,
            entity=USAGE_ENTITY,
            event_metadata=event.metadata,
        )
    db.commit()
