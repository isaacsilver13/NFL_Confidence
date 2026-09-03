"""Add job_executions table for scheduled job monitoring.

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-09-02 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create job_executions table for audit trail of scheduled job runs."""
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
    # Create index for efficient queries by job_name and started_at
    op.create_index(
        "ix_job_executions_job_name_started_at",
        "job_executions",
        ["job_name", "started_at"],
    )


def downgrade() -> None:
    """Drop job_executions table."""
    op.drop_index("ix_job_executions_job_name_started_at", table_name="job_executions")
    op.drop_table("job_executions")
