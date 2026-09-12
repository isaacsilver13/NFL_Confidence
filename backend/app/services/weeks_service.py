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
        # A week's `end_date` is derived from its last game's kickoff time, so
        # the strict date-range match above can stop matching before that
        # game (or the week's scoring) has actually finished — e.g. the
        # instant Monday Night Football kicks off. Fall back to the earliest
        # week that hasn't finished scoring yet, so it stays reachable for
        # sync/display instead of being permanently orphaned once its date
        # window closes.
        week = nfl_week_repository.get_earliest_incomplete(db, season=league.season)
    if week is None:
        raise NotFoundError("No current NFL week is available.")
    return week


def list_all_weeks(db: Session) -> list[NflWeek]:
    league = league_service.get_active_league(db)
    return nfl_week_repository.list_by_season(db, season=league.season)
