"""Business logic for resolving NFL weeks for the active league."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import WeekStatus
from app.models.league import League
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


def list_incomplete_weeks(db: Session, *, league: League) -> list[NflWeek]:
    """All weeks for the league's season that haven't finished scoring yet.

    `get_current_week` only ever resolves to a single week, so once a week's
    date range closes and the next week's begins, an unfinished prior week
    (e.g. one game's result didn't land before the next week rolled in) is
    never revisited by the calendar-based lookup. Sync jobs should iterate
    this list instead of just the current week, so every week keeps getting
    re-checked until it actually completes.
    """
    weeks = nfl_week_repository.list_by_season(db, season=league.season)
    return [week for week in weeks if week.status != WeekStatus.COMPLETE]
