"""add persisted scoring tie-breaker fields

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "weekly_results",
        sa.Column("highest_confidence_win", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "season_results",
        sa.Column("highest_confidence_win", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("season_results", "highest_confidence_win")
    op.drop_column("weekly_results", "highest_confidence_win")
