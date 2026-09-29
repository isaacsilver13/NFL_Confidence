"""add game clock and period

Revision ID: 8e14dad570d9
Revises: p7q8r9s0t1u2
Create Date: 2026-09-13 21:12:03.533145

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8e14dad570d9"
down_revision: str | None = "p7q8r9s0t1u2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("nfl_games", sa.Column("clock", sa.String(), nullable=True))
    op.add_column("nfl_games", sa.Column("period", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("nfl_games", "period")
    op.drop_column("nfl_games", "clock")
