"""Business logic for resolving NFL weeks for the active league."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.nfl_week import NflWeek
from app.repositories import nfl_week_repository
from app.services import league_service


def get_current_week(db: Session) -> NflWeek:
    league = league_service.get_active_league(db)
    week = nfl_week_repository.get_current(db, season=league.season, at=datetime.now(timezone.utc))
    if week is None:
        raise NotFoundError("No current NFL week is available.")
    return week


def list_all_weeks(db: Session) -> list[NflWeek]:
    league = league_service.get_active_league(db)
    return nfl_week_repository.list_by_season(db, season=league.season)
