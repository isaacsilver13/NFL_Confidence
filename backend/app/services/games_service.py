"""Business logic for retrieving NFL games."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.nfl_game import NflGame
from app.repositories import nfl_game_repository
from app.services import weeks_service


def get_current_week_games(db: Session) -> list[NflGame]:
    week = weeks_service.get_current_week(db)
    return nfl_game_repository.get_by_week_id(db, week.id)


def get_game(db: Session, game_id: uuid.UUID) -> NflGame:
    game = nfl_game_repository.get_by_id(db, game_id)
    if game is None:
        raise NotFoundError("NFL game not found.")
    return game
