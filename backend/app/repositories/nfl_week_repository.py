"""CRUD and queries for NFL week records."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nfl_week import NflWeek


def get_by_season_and_week(db: Session, *, season: int, week_number: int) -> NflWeek | None:
    return db.execute(
        select(NflWeek).where(
            NflWeek.season == season,
            NflWeek.week_number == week_number,
        )
    ).scalar_one_or_none()


def get_current(db: Session, *, season: int, at: datetime) -> NflWeek | None:
    return (
        db.execute(
            select(NflWeek)
            .where(
                NflWeek.season == season,
                NflWeek.start_date <= at,
                NflWeek.end_date >= at,
            )
            .order_by(NflWeek.week_number)
        )
        .scalars()
        .first()
    )


def list_by_season(db: Session, *, season: int) -> list[NflWeek]:
    return list(
        db.execute(
            select(NflWeek).where(NflWeek.season == season).order_by(NflWeek.week_number)
        ).scalars()
    )


def create(
    db: Session,
    *,
    season: int,
    week_number: int,
    start_date: datetime,
    end_date: datetime,
) -> NflWeek:
    week = NflWeek(
        season=season,
        week_number=week_number,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(week)
    db.flush()
    return week
