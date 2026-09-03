"""NFL week, game, and confidence-pick API schemas."""

import uuid
from datetime import datetime

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


class PickRead(CamelModel):
    id: uuid.UUID
    game_id: uuid.UUID
    team: str
    confidence: int
    submitted_at: datetime


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
