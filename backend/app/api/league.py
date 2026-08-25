"""League routes: create/view league, list members, invite, join.

Routes stay thin: validate request -> call service -> return response.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.responses import success
from app.db.session import get_db
from app.models.user import User
from app.schemas.league import (
    InviteCreateRequest,
    InviteRead,
    LeagueCreateRequest,
    LeagueJoinRequest,
    LeagueMemberRead,
    LeagueRead,
)
from app.services import league_service

router = APIRouter(prefix="/league", tags=["league"])


@router.post("")
def create_league(
    body: LeagueCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.create_league(
        db, owner=current_user, name=body.name, season=body.season
    )
    return success(
        LeagueRead(
            id=league.id,
            name=league.name,
            season=league.season,
            member_count=league_service.get_member_count(db, league),
            commissioner_name=current_user.display_name,
            invite_code=league.invite_code,
            is_active=league.is_active,
        ).model_dump(by_alias=True)
    )


@router.get("")
def get_league(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.get_active_league(db)
    return success(
        LeagueRead(
            id=league.id,
            name=league.name,
            season=league.season,
            member_count=league_service.get_member_count(db, league),
            commissioner_name=league.owner.display_name,
            invite_code=league.invite_code,
            is_active=league.is_active,
        ).model_dump(by_alias=True)
    )


@router.get("/members")
def get_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.get_active_league(db)
    members = league_service.list_members(db, league)
    return success(
        [
            LeagueMemberRead(
                id=member.id,
                user_id=member.user_id,
                display_name=member.user.display_name,
                email=member.user.email,
                avatar_url=member.user.avatar_url,
                role=member.role.value,
                joined_at=member.joined_at,
            ).model_dump(by_alias=True)
            for member in members
        ]
    )


@router.post("/invite")
def create_invite(
    body: InviteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league = league_service.get_active_league(db)
    invite = league_service.create_invite(db, league=league, inviter=current_user, email=body.email)
    return success(
        InviteRead(id=invite.id, email=invite.email, expires_at=invite.expires_at).model_dump(
            by_alias=True
        )
    )


@router.post("/join")
def join_league(
    body: LeagueJoinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league_service.join_league(db, user=current_user, token=body.token)
    return success(None, message="Joined league successfully.")
