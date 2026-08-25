"""create initial schema

Revision ID: 20cbf41ac7a2
Revises:
Create Date: 2026-07-30 20:48:00.413530

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20cbf41ac7a2"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEAGUE_ROLE = postgresql.ENUM("owner", "member", name="league_role")
WEEK_STATUS = postgresql.ENUM(
    "preseason", "regular", "playoff", "super_bowl", "complete", name="week_status"
)
GAME_STATUS = postgresql.ENUM(
    "scheduled", "live", "final", "postponed", "cancelled", name="game_status"
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("google_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "leagues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("invite_code", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leagues_invite_code", "leagues", ["invite_code"], unique=True)

    op.create_table(
        "league_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("league_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", LEAGUE_ROLE, nullable=False, server_default="member"),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("league_id", "user_id", name="uq_league_members_league_user"),
    )
    op.create_index("ix_league_members_league_id", "league_members", ["league_id"])
    op.create_index("ix_league_members_user_id", "league_members", ["user_id"])

    op.create_table(
        "nfl_weeks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", WEEK_STATUS, nullable=False, server_default="preseason"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season", "week_number", name="uq_nfl_weeks_season_week"),
    )
    op.create_index("ix_nfl_weeks_season", "nfl_weeks", ["season"])

    op.create_table(
        "nfl_games",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("week_id", sa.Uuid(), nullable=False),
        sa.Column("espn_game_id", sa.String(length=64), nullable=False),
        sa.Column("kickoff_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("home_team", sa.String(length=64), nullable=False),
        sa.Column("away_team", sa.String(length=64), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("winning_team", sa.String(length=64), nullable=True),
        sa.Column("game_status", GAME_STATUS, nullable=False, server_default="scheduled"),
        sa.Column("is_tie", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["week_id"], ["nfl_weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nfl_games_week_id", "nfl_games", ["week_id"])
    op.create_index("ix_nfl_games_espn_game_id", "nfl_games", ["espn_game_id"], unique=True)
    op.create_index("ix_nfl_games_kickoff_time", "nfl_games", ["kickoff_time"])
    op.create_index("ix_nfl_games_winning_team", "nfl_games", ["winning_team"])
    op.create_index("ix_nfl_games_game_status", "nfl_games", ["game_status"])

    op.create_table(
        "picks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.Uuid(), nullable=False),
        sa.Column("picked_team", sa.String(length=64), nullable=False),
        sa.Column("confidence_value", sa.Integer(), nullable=False),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("points_earned", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["nfl_games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "game_id", name="uq_picks_user_game"),
    )
    op.create_index("ix_picks_user_id", "picks", ["user_id"])
    op.create_index("ix_picks_game_id", "picks", ["game_id"])

    op.create_table(
        "weekly_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("league_id", sa.Uuid(), nullable=False),
        sa.Column("week_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_picks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_picks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weekly_rank", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["week_id"], ["nfl_weeks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weekly_results_league_id", "weekly_results", ["league_id"])
    op.create_index("ix_weekly_results_week_id", "weekly_results", ["week_id"])
    op.create_index("ix_weekly_results_user_id", "weekly_results", ["user_id"])
    op.create_index("ix_weekly_results_weekly_rank", "weekly_results", ["weekly_rank"])

    op.create_table(
        "season_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("league_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weekly_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_place_finishes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("second_place_finishes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("third_place_finishes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_rank", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "league_id", "user_id", "season", name="uq_season_results_league_user_season"
        ),
    )
    op.create_index("ix_season_results_league_id", "season_results", ["league_id"])
    op.create_index("ix_season_results_user_id", "season_results", ["user_id"])

    op.create_table(
        "invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("league_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invites_league_id", "invites", ["league_id"])
    op.create_index("ix_invites_email", "invites", ["email"])
    op.create_index("ix_invites_token", "invites", ["token"], unique=True)

    op.create_table(
        "reminder_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("thursday_reminder", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sunday_reminder", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("kickoff_reminder", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reminder_preferences_user_id", "reminder_preferences", ["user_id"], unique=True
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("reminder_preferences")
    op.drop_table("invites")
    op.drop_table("season_results")
    op.drop_table("weekly_results")
    op.drop_table("picks")
    op.drop_table("nfl_games")
    op.drop_table("nfl_weeks")
    op.drop_table("league_members")
    op.drop_table("leagues")
    op.drop_table("users")

    bind = op.get_bind()
    GAME_STATUS.drop(bind, checkfirst=True)
    WEEK_STATUS.drop(bind, checkfirst=True)
    LEAGUE_ROLE.drop(bind, checkfirst=True)
