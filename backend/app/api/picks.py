"""Authenticated confidence-pick routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.responses import success
from app.db.session import get_db
from app.models.pick import Pick
from app.models.user import User
from app.schemas.nfl import PickRead, PicksCreateRequest
from app.services import league_service, picks_service
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return success(
        [_pick_read(pick) for pick in picks_service.get_user_picks(db, user=current_user)]
    )


@router.get("/history")
def get_pick_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.get_active_league(db)
    result = picks_service.get_user_pick_history(db, user=current_user, league=league)
    return success(result.model_dump(mode="json", by_alias=True))


@router.post("")
def save_picks(
    body: PicksCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
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
