"""SQLAlchemy models package.

Importing this module registers all models on `Base.metadata`, which is required
before running Alembic autogenerate or creating tables directly.
"""

from app.models.audit_log import AuditLog
from app.models.invite import Invite
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.models.refresh_token import RefreshToken
from app.models.reminder_preference import ReminderPreference
from app.models.season_result import SeasonResult
from app.models.user import User
from app.models.weekly_result import WeeklyResult

__all__ = [
    "AuditLog",
    "Invite",
    "League",
    "LeagueMember",
    "NflGame",
    "NflWeek",
    "Pick",
    "RefreshToken",
    "ReminderPreference",
    "SeasonResult",
    "User",
    "WeeklyResult",
]
