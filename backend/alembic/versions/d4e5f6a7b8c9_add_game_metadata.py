"""add venue and spread metadata to NFL games

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-08-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("nfl_games", sa.Column("venue_name", sa.String(length=255), nullable=True))
    op.add_column("nfl_games", sa.Column("venue_location", sa.String(length=255), nullable=True))
    op.add_column("nfl_games", sa.Column("spread_team", sa.String(length=64), nullable=True))
    op.add_column("nfl_games", sa.Column("spread", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("nfl_games", "spread")
    op.drop_column("nfl_games", "spread_team")
    op.drop_column("nfl_games", "venue_location")
    op.drop_column("nfl_games", "venue_name")
