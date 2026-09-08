"""Repair drifted job_executions schema.

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-09-05 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "j1k2l3m4n5o6"
down_revision = "i0j1k2l3m4n5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
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
        op.create_index(
            "ix_job_executions_job_name_started_at",
            "job_executions",
            ["job_name", "started_at"],
        )
        return

    index_names = {index["name"] for index in inspector.get_indexes("job_executions")}
    if "ix_job_executions_job_name_started_at" not in index_names:
        op.create_index(
            "ix_job_executions_job_name_started_at",
            "job_executions",
            ["job_name", "started_at"],
        )


def downgrade() -> None:
    """The baseline migration owns this table; preserve it on downgrade."""
