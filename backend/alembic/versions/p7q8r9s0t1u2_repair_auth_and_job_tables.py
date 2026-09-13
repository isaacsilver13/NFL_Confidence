"""Repair auth and scheduler tables when migration history is ahead of schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "p7q8r9s0t1u2"
down_revision: str | None = "o6p7q8r9s0t1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_refresh_tokens(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    if not inspector.has_table("refresh_tokens"):
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    index_names = {index["name"] for index in inspector.get_indexes("refresh_tokens")}
    if "ix_refresh_tokens_user_id" not in index_names:
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    if "ix_refresh_tokens_token_hash" not in index_names:
        op.create_index(
            "ix_refresh_tokens_token_hash",
            "refresh_tokens",
            ["token_hash"],
            unique=True,
        )


def _ensure_job_executions(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    if not inspector.has_table("job_executions"):
        op.create_table(
            "job_executions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("job_name", sa.String(length=100), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("result_count", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.String(length=2000), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    index_names = {index["name"] for index in inspector.get_indexes("job_executions")}
    if "ix_job_executions_job_name_started_at" not in index_names:
        op.create_index(
            "ix_job_executions_job_name_started_at",
            "job_executions",
            ["job_name", "started_at"],
        )


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_refresh_tokens(bind)
    _ensure_job_executions(bind)


def downgrade() -> None:
    # These repairs may restore tables that contain production data.
    pass
