"""Business rules for league creation, membership, and invitations.

Routes stay thin — this module enforces the single-league invariant, commissioner
permissions, and invite lifecycle, then delegates persistence to the repositories.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.enums import LeagueRole
from app.models.invite import Invite
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.user import User
from app.repositories import invite_repository, league_member_repository, league_repository
from app.services.email_service import send_league_invitation

settings = get_settings()

INVITE_EXPIRY_DAYS = 7


def create_league(db: Session, *, owner: User, name: str, season: int) -> League:
    """Create the app's single league. Fails if a league already exists."""
    if league_repository.get_active(db) is not None:
        raise ConflictError("A league already exists. This application supports only one league.")

    invite_code = secrets.token_urlsafe(8)
    league = league_repository.create(
        db, name=name, season=season, owner_id=owner.id, invite_code=invite_code
    )
    league_member_repository.create(
        db, league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER
    )
    db.commit()
    db.refresh(league)
    return league


def get_active_league(db: Session) -> League:
    league = league_repository.get_active(db)
    if league is None:
        raise NotFoundError("No league has been created yet.")
    return league


def get_member_count(db: Session, league: League) -> int:
    return league_repository.count_members(db, league.id)


def list_members(db: Session, league: League) -> list[LeagueMember]:
    return league_member_repository.list_by_league(db, league.id)


def _require_owner(league: League, user: User) -> None:
    if league.owner_id != user.id:
        raise ForbiddenError("Only the league commissioner can perform this action.")


def create_invite(db: Session, *, league: League, inviter: User, email: str) -> Invite:
    _require_owner(league, inviter)

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)
    invite = invite_repository.create(
        db, league_id=league.id, email=email, token=token, expires_at=expires_at
    )
    db.commit()
    db.refresh(invite)

    invite_link = f"{settings.app_url}/join?token={token}"
    send_league_invitation(
        to=email,
        league_name=league.name,
        commissioner_name=inviter.display_name,
        invite_link=invite_link,
        expires_at=expires_at.isoformat(),
    )
    return invite


def join_league(db: Session, *, user: User, token: str) -> LeagueMember:
    invite = invite_repository.get_by_token(db, token)
    if invite is None:
        raise NotFoundError("Invite not found.")
    if invite.accepted_at is not None:
        raise ConflictError("This invite has already been used.")

    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise ValidationError("This invite has expired.")

    existing_membership = league_member_repository.get_by_league_and_user(
        db, invite.league_id, user.id
    )
    if existing_membership is not None:
        raise ConflictError("You are already a member of this league.")

    membership = league_member_repository.create(
        db, league_id=invite.league_id, user_id=user.id, role=LeagueRole.MEMBER
    )
    invite_repository.mark_accepted(db, invite)
    db.commit()
    db.refresh(membership)
    return membership
