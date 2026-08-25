"""CRUD operations for the LeagueMember model. No business logic here — see app.services."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import LeagueRole
from app.models.league_member import LeagueMember
from app.models.user import User


def get_by_league_and_user(
    db: Session, league_id: uuid.UUID, user_id: uuid.UUID
) -> LeagueMember | None:
    return db.execute(
        select(LeagueMember).where(
            LeagueMember.league_id == league_id, LeagueMember.user_id == user_id
        )
    ).scalar_one_or_none()


def list_by_league(db: Session, league_id: uuid.UUID) -> list[LeagueMember]:
    return list(
        db.execute(
            select(LeagueMember)
            .where(LeagueMember.league_id == league_id)
            .join(User)
            .options(joinedload(LeagueMember.user))
            .order_by(User.display_name)
        )
        .scalars()
        .all()
    )


def create(
    db: Session, *, league_id: uuid.UUID, user_id: uuid.UUID, role: LeagueRole
) -> LeagueMember:
    member = LeagueMember(league_id=league_id, user_id=user_id, role=role)
    db.add(member)
    db.flush()
    return member
