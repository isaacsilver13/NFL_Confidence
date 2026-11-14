"""create usage_events table for client usage telemetry

Revision ID: t1v2w3x4y5z6
Revises: t2u3v4w5x6y7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "t1v2w3x4y5z6"
down_revision: str | None = "t2u3v4w5x6y7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=200), nullable=True),
        sa.Column("section", sa.String(length=32), nullable=True),
        sa.Column("device", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])
    op.create_index("ix_usage_events_user_id_created_at", "usage_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_user_id_created_at", table_name="usage_events")
    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_table("usage_events")
