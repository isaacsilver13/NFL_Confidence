"""Add Monday Night guesses table and total offense yards on games.

Revision ID: t2u3v4w5x6y7
Revises: s1u2v3w4x5y6
Create Date: 2026-11-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "t2u3v4w5x6y7"
down_revision: str | None = "s1u2v3w4x5y6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mnf_guesses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "week_id", sa.Uuid(), sa.ForeignKey("nfl_weeks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("yards", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "week_id", name="uq_mnf_guesses_user_week"),
    )
    op.create_index("ix_mnf_guesses_user_id", "mnf_guesses", ["user_id"])
    op.create_index("ix_mnf_guesses_week_id", "mnf_guesses", ["week_id"])
    op.add_column("nfl_games", sa.Column("total_offense_yards", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("nfl_games", "total_offense_yards")
    op.drop_table("mnf_guesses")
