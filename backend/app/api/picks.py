"""Authenticated confidence-pick routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_active_league_member, get_current_user
from app.core.responses import success
from app.db.session import get_db
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.pick import Pick
from app.models.user import User
from app.repositories import nfl_game_repository
from app.schemas.nfl import GameRead, PickRead, PicksCreateRequest, WeekRead
from app.services import picks_service, weeks_service
from app.services.picks_service import PickSubmission

router = APIRouter(prefix="/picks", tags=["picks"])


def _pick_read(pick: Pick) -> dict:
    return PickRead(
        id=pick.id,
        game_id=pick.game_id,
        team=pick.picked_team,
        confidence=pick.confidence_value,
        submitted_at=pick.submitted_at,
    ).model_dump(by_alias=True)


@router.get("/current")
def get_current_picks(
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    return success(
        [_pick_read(pick) for pick in picks_service.get_user_picks(db, user=current_user)]
    )


@router.get("/history")
def get_pick_history(
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    result = picks_service.get_user_pick_history(db, user=current_user, league=league)
    return success(result.model_dump(mode="json", by_alias=True))


@router.post("")
def save_picks(
    body: PicksCreateRequest,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    submissions = [
        PickSubmission(
            game_id=pick.game_id,
            team=pick.team,
            confidence=pick.confidence,
        )
        for pick in body.picks
    ]
    saved_picks = picks_service.create_picks(
        db,
        user=current_user,
        week_number=body.week,
        submissions=submissions,
    )
    return success([_pick_read(pick) for pick in saved_picks])


@router.get("/card/current")
def get_current_card(
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get the current week's picks card: week + games + user's picks.

    Combines three separate queries into one round-trip to reduce latency
    on the picks page load.

    Returns:
        {
            week: Current NFL week,
            games: List of games for the current week,
            picks: User's picks for the current week
        }
    """
    league, member = league_member

    # Get current week
    week = weeks_service.get_current_week(db)
    week_data = WeekRead(
        id=week.id,
        season=week.season,
        week_number=week.week_number,
        start_date=week.start_date,
        end_date=week.end_date,
        status=week.status,
    ).model_dump(by_alias=True)

    # Get games for current week
    games = nfl_game_repository.get_by_week_id(db, week.id)
    games_data = [
        GameRead(
            id=game.id,
            away_team=game.away_team,
            home_team=game.home_team,
            kickoff=game.kickoff_time,
            status=game.game_status,
            venue_name=game.venue_name,
            venue_location=game.venue_location,
            spread_team=game.spread_team,
            spread=game.spread,
            away_score=game.away_score,
            home_score=game.home_score,
            winning_team=game.winning_team,
            is_tie=game.is_tie,
        ).model_dump(by_alias=True)
        for game in games
    ]

    # Get user's picks for current week
    user_picks = picks_service.get_user_picks(db, user=current_user)
    picks_data = [_pick_read(pick) for pick in user_picks]

    return success(
        {
            "week": week_data,
            "games": games_data,
            "picks": picks_data,
        }
    )
