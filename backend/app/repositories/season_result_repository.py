"""Queries for season standings results."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.season_result import SeasonResult


def list_by_league_and_season(
    db: Session, *, league_id: uuid.UUID, season: int
) -> list[SeasonResult]:
    return list(
        db.execute(
            select(SeasonResult)
            .where(SeasonResult.league_id == league_id, SeasonResult.season == season)
            .options(joinedload(SeasonResult.user))
        )
        .scalars()
        .all()
    )


def get_by_league_user_season(
    db: Session, *, league_id: uuid.UUID, user_id: uuid.UUID, season: int
) -> SeasonResult | None:
    return db.execute(
        select(SeasonResult).where(
            SeasonResult.league_id == league_id,
            SeasonResult.user_id == user_id,
            SeasonResult.season == season,
        )
    ).scalar_one_or_none()
