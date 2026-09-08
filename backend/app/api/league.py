"""League routes: create/view league, list members, invite, join, and removal.

Routes stay thin: validate request -> call service -> return response.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_active_league_member,
    get_active_league_owner,
    get_current_user,
)
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
    LeagueMemberUpdateRequest,
    LeagueRead,
    MemberPaymentRead,
    MemberPaymentUpdateRequest,
    VoidUnpaidPicksRead,
    VoidUnpaidPicksRequest,
)
from app.services import league_service, member_payment_service

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
    league, _ = league_member
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
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_owner),
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


@router.patch("/members/{user_id}")
def update_member(
    user_id: uuid.UUID,
    body: LeagueMemberUpdateRequest,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_owner),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
    updated_member = league_service.update_member(
        db,
        league=league,
        commissioner=member.user,
        user_id=user_id,
        display_name=body.display_name,
        role=body.role,
    )
    return success(
        LeagueMemberRead(
            id=updated_member.id,
            user_id=updated_member.user_id,
            display_name=updated_member.user.display_name,
            email=updated_member.user.email,
            avatar_url=updated_member.user.avatar_url,
            role=updated_member.role.value,
            joined_at=updated_member.joined_at,
        ).model_dump(by_alias=True)
    )


@router.get("/payments")
def get_payment_statuses(
    week: int = Query(..., ge=1, le=22),
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_owner),
    db: Session = Depends(get_db),
) -> dict:
    league, _ = league_member
    week_number, statuses = member_payment_service.list_payment_statuses(
        db, league=league, week_number=week
    )
    return success(
        {
            "week": week_number,
            "members": [
                MemberPaymentRead(
                    user_id=payment_member.user_id,
                    display_name=payment_member.user.display_name,
                    email=payment_member.user.email,
                    role=payment_member.role,
                    is_paid=payment.is_paid if payment else False,
                    marked_at=payment.marked_at if payment else None,
                    voided_pick_count=voided_pick_count,
                ).model_dump(by_alias=True)
                for payment_member, payment, voided_pick_count in statuses
            ],
        }
    )


@router.patch("/payments/{user_id}")
def update_payment_status(
    user_id: uuid.UUID,
    body: MemberPaymentUpdateRequest,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_owner),
    db: Session = Depends(get_db),
) -> dict:
    league, commissioner = league_member
    member_payment_service.mark_payment(
        db,
        league=league,
        marked_by=commissioner.user_id,
        user_id=user_id,
        week_number=body.week,
        is_paid=body.is_paid,
    )
    return success(None, message="Payment status updated.")


@router.post("/payments/void-unpaid")
def void_unpaid_member_picks(
    body: VoidUnpaidPicksRequest,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_owner),
    db: Session = Depends(get_db),
) -> dict:
    league, commissioner = league_member
    voided_pick_count, affected_member_count = member_payment_service.void_unpaid_picks(
        db, league=league, week_number=body.week, voided_by=commissioner.user_id
    )
    return success(
        VoidUnpaidPicksRead(
            week=body.week,
            voided_pick_count=voided_pick_count,
            affected_member_count=affected_member_count,
        ).model_dump(by_alias=True),
        message="Unpaid picks were voided.",
    )


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: uuid.UUID,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_owner),
    db: Session = Depends(get_db),
) -> None:
    league, member = league_member
    league_service.remove_member(db, league=league, commissioner=member.user, user_id=user_id)


@router.post("/invite")
def create_invite(
    body: InviteCreateRequest,
    league_member: tuple[League, LeagueMember] = Depends(get_active_league_owner),
    db: Session = Depends(get_db),
) -> dict:
    league, member = league_member
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
