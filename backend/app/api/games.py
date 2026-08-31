"""NFL game routes."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.responses import success
from app.db.session import get_db
from app.models.nfl_game import NflGame
from app.models.user import User
from app.schemas.nfl import GameRead
from app.services import games_service

router = APIRouter(prefix="/games", tags=["games"])


def _game_read(game: NflGame) -> dict:
    return GameRead(
        id=game.id,
        away_team=game.away_team,
        home_team=game.home_team,
        kickoff=game.kickoff_time,
        status=game.game_status.value,
        venue_name=game.venue_name,
        venue_location=game.venue_location,
        spread_team=game.spread_team,
        spread=game.spread,
        away_score=game.away_score,
        home_score=game.home_score,
        winning_team=game.winning_team,
        is_tie=game.is_tie,
    ).model_dump(by_alias=True)


@router.get("/current")
def get_current_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return success([_game_read(game) for game in games_service.get_current_week_games(db)])


@router.get("/{game_id}")
def get_game(
    game_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return success(_game_read(games_service.get_game(db, game_id)))
