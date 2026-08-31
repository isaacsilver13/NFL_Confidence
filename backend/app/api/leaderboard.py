"""Authenticated leaderboard, standings, and pick breakdown routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.responses import success
from app.db.session import get_db
from app.models.user import User
from app.services import leaderboard_service, league_service

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/week")
def get_weekly_leaderboard(
    week: int | None = Query(None, ge=1, le=18),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.get_active_league(db)
    result = leaderboard_service.get_weekly_leaderboard(db, league=league, week_number=week)
    return success(result.model_dump(mode="json", by_alias=True))


@router.get("/season")
def get_season_standings(
    season: int | None = Query(None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.get_active_league(db)
    result = leaderboard_service.get_season_standings(db, league=league, season=season)
    return success(result.model_dump(mode="json", by_alias=True))


@router.get("/pick-breakdown")
def get_pick_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.get_active_league(db)
    result = leaderboard_service.get_pick_breakdown(db, league=league, viewer_id=current_user.id)
    return success(result.model_dump(mode="json", by_alias=True))
