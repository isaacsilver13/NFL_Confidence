"""NFL week routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_active_league_member
from app.core.responses import success
from app.db.session import get_db
from app.models.league import League
from app.models.league_member import LeagueMember
from app.schemas.nfl import WeekRead
from app.services import weeks_service

router = APIRouter(prefix="/weeks", tags=["weeks"])


def _week_read(week) -> dict:
    locks_at = min((game.kickoff_time for game in week.games), default=None)
    return WeekRead(
        id=week.id,
        season=week.season,
        week_number=week.week_number,
        start_date=week.start_date,
        end_date=week.end_date,
        status=week.status.value,
        locks_at=locks_at,
        is_locked=locks_at is not None and locks_at <= datetime.now(timezone.utc),
    ).model_dump(by_alias=True)


@router.get("/current")
def get_current_week(
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    return success(_week_read(weeks_service.get_current_week(db)))


@router.get("")
def get_weeks(
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    return success([_week_read(week) for week in weeks_service.list_all_weeks(db)])
