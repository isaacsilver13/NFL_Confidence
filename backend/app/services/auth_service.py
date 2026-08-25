"""Business logic for authentication: user upsert, token issuance, refresh rotation, logout."""

import uuid

from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.core.exceptions import UnauthorizedError
from app.models.user import User
from app.repositories import refresh_token_repository, user_repository

DEV_USER_GOOGLE_ID = "dev-local-user"
DEV_USER_EMAIL = "dev@localhost"
DEV_USER_DISPLAY_NAME = "Local Dev User"


class IssuedTokens:
    """Container for a freshly issued access/refresh token pair."""

    def __init__(self, *, access_token: str, expires_in: int, refresh_token: str, user: User):
        self.access_token = access_token
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.user = user


def get_or_create_google_user(
    db: Session, *, google_id: str, email: str, display_name: str, avatar_url: str | None
) -> User:
    """Find an existing user by Google ID, otherwise create a new one."""
    user = user_repository.get_by_google_id(db, google_id)
    if user is not None:
        return user
    return user_repository.create(
        db,
        google_id=google_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )


def get_or_create_dev_user(db: Session) -> User:
    """Find or create the fixed local-only dev user used when Google OAuth isn't configured."""
    return get_or_create_google_user(
        db,
        google_id=DEV_USER_GOOGLE_ID,
        email=DEV_USER_EMAIL,
        display_name=DEV_USER_DISPLAY_NAME,
        avatar_url=None,
    )


def issue_tokens(db: Session, user: User) -> IssuedTokens:
    """Issue a new access token and a new (rotated) refresh token for a user."""
    access_token, expires_in = create_access_token(user.id)
    raw_refresh_token = generate_refresh_token()
    refresh_token_repository.create(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=refresh_token_expiry(),
    )
    db.commit()
    return IssuedTokens(
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=raw_refresh_token,
        user=user,
    )


def refresh_session(db: Session, raw_refresh_token: str) -> IssuedTokens:
    """Validate a refresh token, revoke it, and issue a brand new access/refresh pair.

    Raises UnauthorizedError if the token is missing, unknown, expired, or already revoked.
    """
    token_hash = hash_refresh_token(raw_refresh_token)
    existing = refresh_token_repository.get_by_hash(db, token_hash)
    if existing is None or not refresh_token_repository.is_valid(existing):
        raise UnauthorizedError("Invalid or expired refresh token")

    user = user_repository.get_by_id(db, existing.user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired refresh token")

    refresh_token_repository.revoke(db, existing)
    return issue_tokens(db, user)


def logout(db: Session, *, user_id: uuid.UUID, raw_refresh_token: str) -> None:
    """Revoke a refresh token belonging to `user_id`.

    Silently no-ops if the token is unknown, already revoked, or belongs to a different
    user (avoids leaking whether an arbitrary token value is valid).
    """
    token_hash = hash_refresh_token(raw_refresh_token)
    existing = refresh_token_repository.get_by_hash(db, token_hash)
    if existing is not None and existing.user_id == user_id:
        refresh_token_repository.revoke(db, existing)
        db.commit()
