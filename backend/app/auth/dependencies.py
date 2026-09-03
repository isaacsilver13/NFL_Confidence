"""FastAPI dependencies for authenticating requests."""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import InvalidTokenError, decode_access_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.session import get_db
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.user import User
from app.repositories import league_member_repository, league_repository, user_repository

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer access token, or raise 401."""
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except ValueError as exc:
        raise UnauthorizedError("Invalid access token") from exc

    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError("User not found")

    return user


def get_active_league_member(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[League, LeagueMember]:
    """Resolve the active league and verify the user is a member, or raise 403.

    Returns (League, LeagueMember) tuple if user is a member of the active league.
    Raises ForbiddenError (403) without revealing league details if user is not a member.
    """
    league = league_repository.get_active(db)
    if league is None:
        raise ForbiddenError("No active league")

    member = league_member_repository.get_by_league_and_user(db, league.id, current_user.id)
    if member is None:
        raise ForbiddenError("Not a member of this league")

    return league, member
