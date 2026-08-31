"""Queries for weekly leaderboard results."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.weekly_result import WeeklyResult


def list_by_league_and_week(
    db: Session, *, league_id: uuid.UUID, week_id: uuid.UUID
) -> list[WeeklyResult]:
    return list(
        db.execute(
            select(WeeklyResult)
            .where(WeeklyResult.league_id == league_id, WeeklyResult.week_id == week_id)
            .options(joinedload(WeeklyResult.user))
        )
        .scalars()
        .all()
    )


def get_by_league_week_user(
    db: Session, *, league_id: uuid.UUID, week_id: uuid.UUID, user_id: uuid.UUID
) -> WeeklyResult | None:
    return db.execute(
        select(WeeklyResult).where(
            WeeklyResult.league_id == league_id,
            WeeklyResult.week_id == week_id,
            WeeklyResult.user_id == user_id,
        )
    ).scalar_one_or_none()
