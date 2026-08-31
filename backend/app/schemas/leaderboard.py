"""Schemas for weekly, season, and pick breakdown leaderboard data."""

import uuid

from app.schemas.base import CamelModel


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


class WeekLabelRead(CamelModel):
    week_number: int
    season_number: int


class WeeklyLeaderboardRead(CamelModel):
    week: WeekLabelRead
    standings: list[LeaderboardMemberRead]


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
    median_confidence: float | None = None
    team_counts: list[TeamPickCountRead]


class WeeklyPickBreakdownRead(CamelModel):
    week_number: int
    games: list[GamePickBreakdownRead]


class PickBreakdownRead(CamelModel):
    season: int
    weeks: list[WeeklyPickBreakdownRead]
