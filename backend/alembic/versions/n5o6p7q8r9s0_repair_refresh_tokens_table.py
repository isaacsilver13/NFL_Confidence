"""Repair databases stamped past the refresh-token migration without the table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n5o6p7q8r9s0"
down_revision: str | None = "m4n5o6p7q8r9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "refresh_tokens" not in table_names:
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


def downgrade() -> None:
    # This repair may have restored a table that already held production data.
    pass
