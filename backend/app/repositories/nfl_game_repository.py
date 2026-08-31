"""CRUD and queries for NFL game records."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nfl_game import NflGame


def get_by_id(db: Session, game_id: uuid.UUID) -> NflGame | None:
    return db.get(NflGame, game_id)


def get_by_week_id(db: Session, week_id: uuid.UUID) -> list[NflGame]:
    return list(
        db.execute(
            select(NflGame).where(NflGame.week_id == week_id).order_by(NflGame.kickoff_time)
        ).scalars()
    )


def get_by_espn_game_id(db: Session, espn_game_id: str) -> NflGame | None:
    return db.execute(
        select(NflGame).where(NflGame.espn_game_id == espn_game_id)
    ).scalar_one_or_none()


def create(
    db: Session,
    *,
    week_id: uuid.UUID,
    espn_game_id: str,
    kickoff_time: datetime,
    home_team: str,
    away_team: str,
    venue_name: str | None = None,
    venue_location: str | None = None,
    spread_team: str | None = None,
    spread: float | None = None,
) -> NflGame:
    game = NflGame(
        week_id=week_id,
        espn_game_id=espn_game_id,
        kickoff_time=kickoff_time,
        home_team=home_team,
        away_team=away_team,
        venue_name=venue_name,
        venue_location=venue_location,
        spread_team=spread_team,
        spread=spread,
    )
    db.add(game)
    db.flush()
    return game
