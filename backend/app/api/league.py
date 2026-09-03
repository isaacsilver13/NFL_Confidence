"""League routes: create/view league, list members, invite, join, and removal.

Routes stay thin: validate request -> call service -> return response.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_active_league_member, get_current_user
from app.core.exceptions import ForbiddenError
from app.core.responses import success
from app.db.session import get_db
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.user import User
from app.schemas.league import (
    InviteCreateRequest,
    InviteRead,
    LeagueCreateRequest,
    LeagueJoinCodeRequest,
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
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
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
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
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


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: uuid.UUID,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> None:
    league, member = league_member
    league_service.remove_member(db, league=league, commissioner=member.user, user_id=user_id)


@router.post("/invite")
def create_invite(
    body: InviteCreateRequest,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_member),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    # Only the league commissioner (owner) can create invitations
    if league.owner_id != member.user_id:
        raise ForbiddenError("Only the league commissioner can create invitations.")

    invite = league_service.create_invite(db, league=league, inviter=member.user, email=body.email)
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


@router.post("/join-with-code")
def join_league_with_code(
    body: LeagueJoinCodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    league_service.join_league_with_code(db, user=current_user, code=body.code)
    return success(None, message="Joined league successfully.")
