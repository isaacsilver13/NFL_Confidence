"""Business rules for league creation, membership, and invitations.

Routes stay thin — this module enforces the single-league invariant, commissioner
permissions, and invite lifecycle, then delegates persistence to the repositories.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
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
    try:
        league = league_repository.create(
            db, name=name, season=season, owner_id=owner.id, invite_code=invite_code
        )
        league_member_repository.create(
            db, league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "A league already exists. This application supports only one league."
        ) from exc
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

    # Normalize email for consistency in database and matching.
    email_normalized = email.lower().strip()

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)
    invite = invite_repository.create(
        db, league_id=league.id, email=email_normalized, token=token, expires_at=expires_at
    )
    db.commit()
    db.refresh(invite)

    invite_link = f"{settings.app_url}/join?token={token}"
    send_league_invitation(
        to=email_normalized,
        league_name=league.name,
        commissioner_name=inviter.display_name,
        invite_link=invite_link,
        expires_at=expires_at.isoformat(),
    )
    return invite


def join_league(db: Session, *, user: User, token: str) -> LeagueMember:
    invite = invite_repository.get_by_token_for_update(db, token)
    if invite is None:
        raise NotFoundError("Invite not found.")

    # Verify the authenticated user's email matches the invite recipient email.
    # Normalize both emails to handle case and whitespace variations.
    # This check must come before checking if the invite was already accepted,
    # to avoid leaking information about other users' invites.
    user_email_normalized = user.email.lower().strip()
    invite_email_normalized = invite.email.lower().strip()
    if user_email_normalized != invite_email_normalized:
        raise ValidationError(
            "This invite was sent to a different email address. "
            "You must log in with the email the invite was sent to."
        )

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

    try:
        membership = league_member_repository.create(
            db, league_id=invite.league_id, user_id=user.id, role=LeagueRole.MEMBER
        )
        invite_repository.mark_accepted(db, invite)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("You are already a member of this league.") from exc
    db.refresh(membership)
    return membership


def join_league_with_code(db: Session, *, user: User, code: str) -> LeagueMember:
    """Add an authenticated user to the active league using its shared passcode."""
    league = league_repository.get_by_invite_code(db, code.strip())
    if league is None or not league.is_active:
        raise ValidationError("That league passcode is invalid.")

    existing_membership = league_member_repository.get_by_league_and_user(
        db, league.id, user.id
    )
    if existing_membership is not None:
        raise ConflictError("You are already a member of this league.")

    try:
        membership = league_member_repository.create(
            db, league_id=league.id, user_id=user.id, role=LeagueRole.MEMBER
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("You are already a member of this league.") from exc
    db.refresh(membership)
    return membership


def remove_member(
    db: Session, *, league: League, commissioner: User, user_id: uuid.UUID
) -> None:
    """Remove a member without deleting their user account."""
    _require_owner(league, commissioner)
    if user_id == league.owner_id:
        raise ForbiddenError("The league commissioner cannot be removed.")

    membership = league_member_repository.get_by_league_and_user(db, league.id, user_id)
    if membership is None:
        raise NotFoundError("League member not found.")

    league_member_repository.delete(db, membership)
    db.commit()
