"""NFL game routes."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_active_league_member
from app.core.responses import success
from app.db.session import get_db
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
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
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    return success([_game_read(game) for game in games_service.get_current_week_games(db)])


@router.get("")
def get_week_games(
    week: int = Query(..., ge=1, le=18),
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    return success(
        [_game_read(game) for game in games_service.get_week_games(db, week_number=week)]
    )


@router.get("/{game_id}")
def get_game(
    game_id: uuid.UUID,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    return success(_game_read(games_service.get_game(db, game_id)))
