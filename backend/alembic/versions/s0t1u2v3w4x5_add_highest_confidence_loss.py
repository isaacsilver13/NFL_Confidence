"""add weekly highest_confidence_loss tie-breaker (lower is better)

Revision ID: s0t1u2v3w4x5
Revises: r9s0t1u2v3w4
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "s0t1u2v3w4x5"
down_revision: str | None = "r9s0t1u2v3w4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "weekly_results",
        sa.Column("highest_confidence_loss", sa.Integer(), nullable=False, server_default="0"),
    )
    # Backfill from scored picks so past weeks don't read as "never lost".
    op.execute(
        """
        UPDATE weekly_results wr
        SET highest_confidence_loss = sub.loss
        FROM (
            SELECT p.user_id, g.week_id, MAX(p.confidence_value) AS loss
            FROM picks p JOIN nfl_games g ON g.id = p.game_id
            WHERE p.voided_at IS NULL AND p.points_earned = 0
            GROUP BY p.user_id, g.week_id
        ) sub
        WHERE sub.user_id = wr.user_id AND sub.week_id = wr.week_id
        """
    )


def downgrade() -> None:
    op.drop_column("weekly_results", "highest_confidence_loss")
