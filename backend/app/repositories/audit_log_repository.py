"""Append-only writes to the AuditLog model. No business logic here — see app.services."""

import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def create(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    entity: str,
    event_metadata: dict[str, str] | None,
) -> AuditLog:
    row = AuditLog(user_id=user_id, action=action, entity=entity, event_metadata=event_metadata)
    db.add(row)
    db.flush()
    return row
