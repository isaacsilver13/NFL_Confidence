"""Usage tracking: record client-reported events and server-side logins in audit_log."""

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories import audit_log_repository
from app.schemas.usage import EventIn

USAGE_ENTITY = "usage"
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
    for event in events:
        audit_log_repository.create(
            db,
            user_id=user_id,
            action=event.action,
            entity=USAGE_ENTITY,
            event_metadata=event.metadata,
        )
    db.commit()
