"""drop job_runs table

The manual admin-trigger path that wrote it (app.jobs.job_runner) is gone: manual runs now go
through app.jobs.tick.run_slot and are logged to job_executions like scheduled ones.

Revision ID: u2w3x4y5z6a7
Revises: t1v2w3x4y5z6
Create Date: 2026-11-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "u2w3x4y5z6a7"
down_revision: str | None = "t1v2w3x4y5z6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS job_runs")  # its two indexes go with it


def downgrade() -> None:
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_runs_job_name"), "job_runs", ["job_name"], unique=False)
    op.create_index(op.f("ix_job_runs_status"), "job_runs", ["status"], unique=False)
