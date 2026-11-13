"""NFL week, game, and confidence-pick API schemas."""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class WeekRead(CamelModel):
    id: uuid.UUID
    season: int
    week_number: int
    start_date: datetime
    end_date: datetime
    status: str
    locks_at: datetime | None = None
    is_locked: bool = False


class LastRefreshedRead(CamelModel):
    last_refreshed_at: datetime | None = None


class GameRead(CamelModel):
    id: uuid.UUID
    away_team: str
    home_team: str
    kickoff: datetime
    status: str
    venue_name: str | None = None
    venue_location: str | None = None
    spread_team: str | None = None
    spread: float | None = None
    away_score: int | None = None
    home_score: int | None = None
    winning_team: str | None = None
    is_tie: bool
    clock: str | None = None
    period: int | None = None
    away_record: str | None = None
    home_record: str | None = None


class PickRead(CamelModel):
    id: uuid.UUID
    game_id: uuid.UUID
    team: str
    confidence: int
    submitted_at: datetime
    voided_at: datetime | None = None
    is_voided: bool = False


class HistoricalPickRead(CamelModel):
    id: uuid.UUID
    game_id: uuid.UUID
    away_team: str
    home_team: str
    kickoff: datetime
    status: str
    team: str
    confidence: int
    submitted_at: datetime
    winning_team: str | None = None
    is_tie: bool
    points_earned: int | None = None
    outcome: str
    is_voided: bool = False


class HistoricalWeekRead(CamelModel):
    week_number: int
    picks: list[HistoricalPickRead]


class PickHistoryRead(CamelModel):
    season: int
    weeks: list[HistoricalWeekRead]


class PickCreate(CamelModel):
    game_id: uuid.UUID
    team: str
    confidence: int


class PicksCreateRequest(CamelModel):
    week: int
    picks: list[PickCreate]
    voided_game_ids: list[uuid.UUID] = Field(default_factory=list)


class PicksSubmitRequest(CamelModel):
    week: int
    # Required when the week has a Monday Night game (checked in the service).
    mnf_guess_points: int | None = Field(default=None, ge=0, le=300)
    mnf_guess_yards: int | None = Field(default=None, ge=0, le=2000)


class WeekSubmissionRead(CamelModel):
    submitted_at: datetime | None = None
    requires_mnf_guess: bool = False
    mnf_guess_points: int | None = None
    mnf_guess_yards: int | None = None


class MemberPicksRead(CamelModel):
    user_id: uuid.UUID
    display_name: str
    picks: list[PickRead]


class AllPicksRead(CamelModel):
    week: WeekRead
    games: list[GameRead]
    members: list[MemberPicksRead]
