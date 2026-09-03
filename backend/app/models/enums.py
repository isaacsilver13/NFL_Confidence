"""Shared enum types used across models."""

import enum


class LeagueRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class WeekStatus(str, enum.Enum):
    PRESEASON = "preseason"
    REGULAR = "regular"
    PLAYOFF = "playoff"
    SUPER_BOWL = "super_bowl"
    COMPLETE = "complete"


class GameStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINAL = "final"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
