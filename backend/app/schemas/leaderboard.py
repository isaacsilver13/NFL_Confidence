"""Schemas for weekly, season, and pick breakdown leaderboard data."""

import uuid

from app.schemas.base import CamelModel


class MemberGamePickRead(CamelModel):
    game_id: uuid.UUID
    team: str | None = None
    confidence: int | None = None


class LeaderboardMemberRead(CamelModel):
    rank: int
    member_id: uuid.UUID
    member_name: str
    total_points: int
    correct_picks: int = 0
    incorrect_picks: int = 0
    weekly_wins: int = 0
    first_place_finishes: int = 0
    second_place_finishes: int = 0
    third_place_finishes: int = 0
    payout_cents: int = 0
    points_remaining: int = 0
    last_two_game_picks: list[MemberGamePickRead] = []


class WeekLabelRead(CamelModel):
    week_number: int
    season_number: int


class GameLabelRead(CamelModel):
    game_id: uuid.UUID
    away_team: str
    home_team: str


class WeeklyLeaderboardRead(CamelModel):
    week: WeekLabelRead
    standings: list[LeaderboardMemberRead]
    last_two_games: list[GameLabelRead] = []


class SeasonStandingsRead(CamelModel):
    season: int
    standings: list[LeaderboardMemberRead]


class TeamPickCountRead(CamelModel):
    team: str
    user_count: int


class GamePickBreakdownRead(CamelModel):
    game_id: uuid.UUID
    away_team: str
    home_team: str
    away_record: str | None = None
    home_record: str | None = None
    median_confidence: float | None = None
    team_counts: list[TeamPickCountRead]


class WeeklyPickBreakdownRead(CamelModel):
    week_number: int
    games: list[GamePickBreakdownRead]


class PickBreakdownRead(CamelModel):
    season: int
    weeks: list[WeeklyPickBreakdownRead]


class GamePickDetailRead(CamelModel):
    member_name: str
    team: str
    confidence: int
    is_correct: bool | None = None


class GamePicksRead(CamelModel):
    game_id: uuid.UUID
    away_team: str
    home_team: str
    picks: list[GamePickDetailRead]
