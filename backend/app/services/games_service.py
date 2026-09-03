"""Business logic for retrieving NFL games."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.nfl_game import NflGame
from app.repositories import nfl_game_repository, nfl_week_repository
from app.services import league_service, weeks_service


def get_current_week_games(db: Session) -> list[NflGame]:
    week = weeks_service.get_current_week(db)
    return nfl_game_repository.get_by_week_id(db, week.id)


def get_week_games(db: Session, *, week_number: int) -> list[NflGame]:
    league = league_service.get_active_league(db)
    week = nfl_week_repository.get_by_season_and_week(
        db, season=league.season, week_number=week_number
    )
    if week is None:
        raise NotFoundError(f"NFL week {week_number} is not available.")
    return nfl_game_repository.get_by_week_id(db, week.id)


def get_game(db: Session, game_id: uuid.UUID) -> NflGame:
    game = nfl_game_repository.get_by_id(db, game_id)
    if game is None:
        raise NotFoundError("NFL game not found.")
    return game
