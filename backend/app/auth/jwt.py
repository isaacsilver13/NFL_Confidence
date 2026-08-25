"""JWT access tokens and opaque refresh tokens.

Access tokens are short-lived signed JWTs (stateless, verified via signature + exp).
Refresh tokens are long, random, opaque strings; only their SHA-256 hash is ever
persisted (see `app.models.refresh_token.RefreshToken`), so a stolen database dump
cannot be used to mint new sessions. Raw refresh tokens are never logged.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

ACCESS_TOKEN_TYPE = "access"


class InvalidTokenError(Exception):
    """Raised when a JWT access token is missing, malformed, expired, or forged."""


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Return (encoded_jwt, expires_in_seconds)."""
    expires_in = settings.jwt_access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token, returning its payload.

    Raises InvalidTokenError on any signature, expiry, or format problem.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise InvalidTokenError("Invalid or expired access token") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Invalid token type")

    return payload


def generate_refresh_token() -> str:
    """Generate a new opaque, high-entropy refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str) -> str:
    """Hash a raw refresh token for storage/lookup (SHA-256 hex digest)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
