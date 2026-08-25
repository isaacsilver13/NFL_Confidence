"""CRUD operations for the League model. No business logic here — see app.services."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.league import League
from app.models.league_member import LeagueMember


def get_active(db: Session) -> League | None:
    """Return the single active league for this app (v1 supports only one)."""
    return db.execute(select(League).where(League.is_active.is_(True))).scalars().first()


def create(db: Session, *, name: str, season: int, owner_id: uuid.UUID, invite_code: str) -> League:
    league = League(name=name, season=season, owner_id=owner_id, invite_code=invite_code)
    db.add(league)
    db.flush()
    return league


def count_members(db: Session, league_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count()).select_from(LeagueMember).where(LeagueMember.league_id == league_id)
    ).scalar_one()
