"""Add weekly payment tracking and pick void metadata.

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-09-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: str | None = "j1k2l3m4n5o6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("picks", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("picks", sa.Column("voided_by_user_id", sa.Uuid(), nullable=True))
    op.create_index("ix_picks_voided_by_user_id", "picks", ["voided_by_user_id"])
    op.create_foreign_key(
        "fk_picks_voided_by_user_id_users",
        "picks",
        "users",
        ["voided_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "member_weekly_payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("league_id", sa.Uuid(), nullable=False),
        sa.Column("week_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("marked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["week_id"], ["nfl_weeks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["marked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "league_id",
            "week_id",
            "user_id",
            name="uq_member_weekly_payments_league_week_user",
        ),
    )
    op.create_index(
        "ix_member_weekly_payments_league_id", "member_weekly_payments", ["league_id"]
    )
    op.create_index("ix_member_weekly_payments_week_id", "member_weekly_payments", ["week_id"])
    op.create_index("ix_member_weekly_payments_user_id", "member_weekly_payments", ["user_id"])
    op.create_index(
        "ix_member_weekly_payments_marked_by_user_id",
        "member_weekly_payments",
        ["marked_by_user_id"],
    )


def downgrade() -> None:
    op.drop_table("member_weekly_payments")
    op.drop_constraint("fk_picks_voided_by_user_id_users", "picks", type_="foreignkey")
    op.drop_index("ix_picks_voided_by_user_id", table_name="picks")
    op.drop_column("picks", "voided_by_user_id")
    op.drop_column("picks", "voided_at")