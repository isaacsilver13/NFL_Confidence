"""Usage tracking: record client events in usage_events and server-side logins in audit_log."""

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories import audit_log_repository, usage_event_repository
from app.schemas.usage import EventIn

AUTH_ENTITY = "auth"
logger = logging.getLogger(__name__)


def record_login(db: Session, user_id: uuid.UUID) -> None:
    """Record a real sign-in (not a token refresh). Never raises: tracking must not block login."""
    try:
        audit_log_repository.create(
            db, user_id=user_id, action="login", entity=AUTH_ENTITY, event_metadata=None
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.warning("Failed to record login event", exc_info=True)


def record_events(db: Session, user_id: uuid.UUID, events: list[EventIn]) -> None:
    usage_event_repository.create_many(
        db, user_id, [{"action": e.action, **(e.metadata or {})} for e in events]
    )
    db.commit()
