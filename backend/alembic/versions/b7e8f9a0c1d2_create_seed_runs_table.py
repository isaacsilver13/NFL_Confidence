"""create seed runs table

Revision ID: b7e8f9a0c1d2
Revises: 85501d6bd76f
Create Date: 2026-08-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e8f9a0c1d2"
down_revision: str | None = "85501d6bd76f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("seed_runs"):
        return
    op.create_table(
        "seed_runs",
        sa.Column("fixture_key", sa.String(length=100), nullable=False),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Uuid(), nullable=False),
        sa.Column("week_count", sa.Integer(), nullable=False),
        sa.Column("game_count", sa.Integer(), nullable=False),
        sa.Column("pick_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("fixture_key"),
    )


def downgrade() -> None:
    op.drop_table("seed_runs")
