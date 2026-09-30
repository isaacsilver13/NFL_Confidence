"""Commissioner-triggered refresh of game outcomes, pick outcomes and weekly standings."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import UpstreamError
from app.integrations.espn import fetch_schedule
from app.models.job_execution import JobExecution
from app.models.league import League
from app.services import scoring_service, weeks_service
from app.services.nfl_schedule_service import import_games

logger = logging.getLogger(__name__)

# Recorded in `job_executions` so the shared "Last refreshed" time reflects manual runs.
# `slot_key` stays NULL, which never collides with the tick's unique (job_name, slot_key) claims.
MANUAL_SCORE_SYNC_JOB = "manual_score_sync"


@dataclass(frozen=True)
class RefreshResult:
    weeks_refreshed: int
    games_final: int


def refresh_league_scores(db: Session, *, league: League) -> RefreshResult:
    """Re-import ESPN results and re-score every incomplete week for the league.

    Mirrors the scheduled `run_current_week_sync` (import games, then `score_week`) but runs on
    the caller's session and league. Both steps are idempotent, so repeat runs are safe.
    """

    execution = JobExecution(
        job_name=MANUAL_SCORE_SYNC_JOB,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db.add(execution)
    db.commit()

    try:
        weeks = weeks_service.list_incomplete_weeks(db, league=league)
        games_final = 0
        for week in weeks:
            import_games(db, fetch_schedule(league.season, week.week_number))
            games_final += scoring_service.score_week(db, league=league, week_id=week.id)
    except (httpx.HTTPError, ValueError) as exc:
        db.rollback()
        _finish(db, execution, status="failed", result_count=None, error=str(exc))
        logger.warning("Manual score refresh failed league=%s error=%s", league.id, exc)
        raise UpstreamError(
            "Could not reach the NFL data provider. Please try again in a moment."
        ) from exc
    except Exception as exc:
        db.rollback()
        _finish(db, execution, status="failed", result_count=None, error=str(exc))
        raise

    _finish(db, execution, status="success", result_count=games_final, error=None)
    return RefreshResult(weeks_refreshed=len(weeks), games_final=games_final)


def _finish(
    db: Session,
    execution: JobExecution,
    *,
    status: str,
    result_count: int | None,
    error: str | None,
) -> None:
    execution.status = status
    execution.completed_at = datetime.now(timezone.utc)
    execution.result_count = result_count
    execution.error_message = error[:2000] if error else None
    db.add(execution)
    db.commit()
