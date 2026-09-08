"""League-facing request and response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr

from app.models.enums import LeagueRole
from app.schemas.base import CamelModel


class LeagueRead(CamelModel):
    id: uuid.UUID
    name: str
    season: int
    member_count: int
    commissioner_name: str
    invite_code: str
    is_active: bool


class LeagueMemberRead(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    email: str
    avatar_url: str | None
    role: str
    joined_at: datetime


class LeagueMemberUpdateRequest(CamelModel):
    display_name: str | None = None
    role: LeagueRole | None = None


class MemberPaymentRead(CamelModel):
    user_id: uuid.UUID
    display_name: str
    email: str
    role: LeagueRole
    is_paid: bool
    marked_at: datetime | None = None
    voided_pick_count: int = 0


class MemberPaymentUpdateRequest(CamelModel):
    week: int
    is_paid: bool


class VoidUnpaidPicksRequest(CamelModel):
    week: int


class VoidUnpaidPicksRead(CamelModel):
    week: int
    voided_pick_count: int
    affected_member_count: int


class SessionMembershipRead(CamelModel):
    status: Literal["no_league", "not_member", "member"]
    role: LeagueRole | None = None


class LeagueCreateRequest(CamelModel):
    name: str
    season: int


class InviteCreateRequest(CamelModel):
    email: EmailStr


class InviteRead(CamelModel):
    id: uuid.UUID
    email: str
    expires_at: datetime


class LeagueJoinRequest(CamelModel):
    token: str


class LeagueJoinCodeRequest(CamelModel):
    code: str
