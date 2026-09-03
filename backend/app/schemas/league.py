"""League-facing request and response schemas."""

import uuid
from datetime import datetime

from pydantic import EmailStr

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
