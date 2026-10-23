"""CRUD operations for the RefreshToken model. No business logic here — see app.services."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


def create(
    db: Session, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> RefreshToken:
    refresh_token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(refresh_token)
    db.flush()
    return refresh_token


def get_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()


def revoke(db: Session, refresh_token: RefreshToken) -> None:
    refresh_token.revoked_at = datetime.now(timezone.utc)
    db.flush()


def is_valid(refresh_token: RefreshToken) -> bool:
    if refresh_token.revoked_at is not None:
        return False
    expires_at = refresh_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc)


def consume_valid_by_hash(db: Session, token_hash: str) -> uuid.UUID | None:
    """Atomically consume one live token in the replacement token's transaction.

    A concurrent UPDATE waits for the row lock and rechecks the live predicate;
    only one transaction can obtain the user id. No commit occurs here, so a
    failed replacement issuance rolls consumption back with the transaction.
    """
    now = datetime.now(timezone.utc)
    return db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(revoked_at=now)
        .returning(RefreshToken.user_id)
    ).scalar_one_or_none()
