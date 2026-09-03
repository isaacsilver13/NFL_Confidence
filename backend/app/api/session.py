"""Session bootstrap API: get all data needed to initialize the app in one call."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.core.responses import success
from app.db.session import get_db
from app.models.user import User
from app.repositories import league_member_repository
from app.schemas.auth import UserRead
from app.schemas.league import LeagueRead
from app.schemas.nfl import WeekRead
from app.services import league_service, weeks_service

router = APIRouter(tags=["session"])
logger = logging.getLogger(__name__)


@router.get("/bootstrap")
def bootstrap_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get all data needed to initialize the app: user + league + current week.

    This endpoint combines multiple queries into one round-trip to reduce
    latency during app startup and page load.

    Returns:
        {
            user: User info,
            league: Current active league (or null if none),
            currentWeek: Current NFL week (or null if no league)
        }
    """
    user_data = UserRead(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
    ).model_dump(by_alias=True)

    # Get active league if it exists
    league_data = None
    current_week_data = None

    try:
        league = league_service.get_active_league(db)
        if league and league_member_repository.get_by_league_and_user(
            db, league.id, current_user.id
        ):
            member_count = league_service.get_member_count(db, league)
            league_data = LeagueRead(
                id=league.id,
                name=league.name,
                season=league.season,
                member_count=member_count,
                commissioner_name=league.owner.display_name,
                invite_code=league.invite_code,
                is_active=league.is_active,
            ).model_dump(by_alias=True)

            # Get current week if league exists
            current_week = weeks_service.get_current_week(db)
            if current_week:
                current_week_data = WeekRead(
                    id=current_week.id,
                    season=current_week.season,
                    week_number=current_week.week_number,
                    start_date=current_week.start_date,
                    end_date=current_week.end_date,
                    status=current_week.status,
                ).model_dump(by_alias=True)
    except NotFoundError:
        # A first-time user has no league yet; return the documented null fields.
        pass
    except Exception:
        # Log all errors to enable production debugging and monitoring
        logger.exception("Bootstrap endpoint failed to load league data")
        raise  # Re-raise to return proper 500 error

    return success(
        {
            "user": user_data,
            "league": league_data,
            "currentWeek": current_week_data,
        }
    )
