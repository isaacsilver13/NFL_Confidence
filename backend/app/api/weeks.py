"""NFL week routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.responses import success
from app.db.session import get_db
from app.models.user import User
from app.schemas.nfl import WeekRead
from app.services import weeks_service

router = APIRouter(prefix="/weeks", tags=["weeks"])


def _week_read(week) -> dict:
    return WeekRead(
        id=week.id,
        season=week.season,
        week_number=week.week_number,
        start_date=week.start_date,
        end_date=week.end_date,
        status=week.status.value,
    ).model_dump(by_alias=True)


@router.get("/current")
def get_current_week(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return success(_week_read(weeks_service.get_current_week(db)))


@router.get("")
def get_weeks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return success([_week_read(week) for week in weeks_service.list_all_weeks(db)])
