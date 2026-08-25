"""CRUD operations for the Invite model. No business logic here — see app.services."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invite import Invite


def create(
    db: Session, *, league_id: uuid.UUID, email: str, token: str, expires_at: datetime
) -> Invite:
    invite = Invite(league_id=league_id, email=email, token=token, expires_at=expires_at)
    db.add(invite)
    db.flush()
    return invite


def get_by_token(db: Session, token: str) -> Invite | None:
    return db.execute(select(Invite).where(Invite.token == token)).scalar_one_or_none()


def mark_accepted(db: Session, invite: Invite) -> None:
    invite.accepted_at = datetime.now(timezone.utc)
    db.flush()
