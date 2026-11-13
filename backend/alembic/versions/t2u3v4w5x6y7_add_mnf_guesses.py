"""Add Monday Night guesses to week_submissions.

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
    op.add_column("week_submissions", sa.Column("mnf_guess_points", sa.Integer(), nullable=True))
    op.add_column("week_submissions", sa.Column("mnf_guess_yards", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("week_submissions", "mnf_guess_yards")
    op.drop_column("week_submissions", "mnf_guess_points")
