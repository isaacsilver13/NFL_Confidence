"""Add unique constraint on weekly_results (league_id, week_id, user_id).

Revision ID: h9i0j1k2l3m4
Revises: g8a9b0c1d2e3
Create Date: 2026-09-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "h9i0j1k2l3m4"
down_revision = "g8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique index on (league_id, week_id, user_id) to weekly_results."""
    op.create_index(
        "uq_weekly_results_user_week",
        "weekly_results",
        ["league_id", "week_id", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove unique index from weekly_results."""
    op.drop_index("uq_weekly_results_user_week", table_name="weekly_results")
