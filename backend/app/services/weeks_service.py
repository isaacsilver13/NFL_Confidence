"""Business logic for resolving NFL weeks for the active league."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import WeekStatus
from app.models.job_execution import JobExecution
from app.models.league import League
from app.models.nfl_week import NflWeek
from app.repositories import nfl_game_repository, nfl_week_repository
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


def _has_kicked_off(db: Session, week: NflWeek, at: datetime) -> bool:
    games = nfl_game_repository.get_by_week_id(db, week.id)
    return any(game.kickoff_time <= at for game in games)


def get_pick_week(db: Session) -> NflWeek:
    """The week members should be making picks for right now.

    Usually the current week. But the schedule import creates week N+1 on Monday morning
    while week N is still being played, and `get_current_week` keeps returning N until
    N's window closes. Once N's first game has kicked off its picks are locked, so if N+1
    exists, has been released and hasn't started, that is the week to pick for.
    """
    current = get_current_week(db)
    now = datetime.now(timezone.utc)
    if not _has_kicked_off(db, current, now):
        return current
    next_week = nfl_week_repository.get_by_season_and_week(
        db, season=current.season, week_number=current.week_number + 1
    )
    if next_week is None or next_week.start_date > now or _has_kicked_off(db, next_week, now):
        return current
    return next_week


SCORE_SYNC_JOBS = (
    "sunday_score_sync",
    "monday_thursday_score_sync",
    "overnight_score_sync",
    "manual_score_sync",
)


def get_last_refreshed_at(db: Session) -> datetime | None:
    """When a scheduled score sync last finished successfully (None if none has yet)."""
    return db.execute(
        select(func.max(JobExecution.completed_at)).where(
            JobExecution.job_name.in_(SCORE_SYNC_JOBS), JobExecution.status == "success"
        )
    ).scalar_one()


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
