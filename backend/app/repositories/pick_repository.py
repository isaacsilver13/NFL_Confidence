"""CRUD and queries for user confidence picks."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import WeekStatus
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.models.user import User


def lock_user(db: Session, *, user_id: uuid.UUID) -> None:
    db.execute(select(User.id).where(User.id == user_id).with_for_update()).scalar_one()


def get_by_user_and_game(db: Session, *, user_id: uuid.UUID, game_id: uuid.UUID) -> Pick | None:
    return db.execute(
        select(Pick).where(Pick.user_id == user_id, Pick.game_id == game_id)
    ).scalar_one_or_none()


def list_by_user_and_week(db: Session, *, user_id: uuid.UUID, week_id: uuid.UUID) -> list[Pick]:
    return list(
        db.execute(
            select(Pick)
            .join(NflGame, Pick.game_id == NflGame.id)
            .where(Pick.user_id == user_id, NflGame.week_id == week_id)
            .order_by(Pick.confidence_value.desc())
        ).scalars()
    )


def list_by_user_and_completed_season(
    db: Session, *, user_id: uuid.UUID, league_id: uuid.UUID, season: int
) -> list[Pick]:
    return list(
        db.execute(
            select(Pick)
            .join(NflGame, Pick.game_id == NflGame.id)
            .join(NflWeek, NflGame.week_id == NflWeek.id)
            .join(LeagueMember, LeagueMember.user_id == Pick.user_id)
            .where(
                Pick.user_id == user_id,
                LeagueMember.league_id == league_id,
                NflWeek.season == season,
                NflWeek.status == WeekStatus.COMPLETE,
            )
            .options(joinedload(Pick.game).joinedload(NflGame.week))
            .order_by(NflWeek.week_number, NflGame.kickoff_time)
        ).scalars()
    )


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    game_id: uuid.UUID,
    picked_team: str,
    confidence_value: int,
) -> Pick:
    pick = Pick(
        user_id=user_id,
        game_id=game_id,
        picked_team=picked_team,
        confidence_value=confidence_value,
    )
    db.add(pick)
    db.flush()
    return pick
