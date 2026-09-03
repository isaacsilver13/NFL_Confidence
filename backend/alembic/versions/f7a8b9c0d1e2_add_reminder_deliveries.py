"""add weekly reminder preference and delivery idempotency

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reminder_preferences",
        sa.Column("weekly_reminder", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("week_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["week_id"], ["nfl_weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "week_id", "notification_type", name="uq_notification_delivery"
        ),
    )
    op.create_index("ix_notification_deliveries_user_id", "notification_deliveries", ["user_id"])
    op.create_index("ix_notification_deliveries_week_id", "notification_deliveries", ["week_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_week_id", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_user_id", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    op.drop_column("reminder_preferences", "weekly_reminder")
