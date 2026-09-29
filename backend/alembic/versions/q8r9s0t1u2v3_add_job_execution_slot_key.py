"""Add slot_key to job_executions so a schedule slot can only be claimed once.

The externally triggered tick claims a slot (job + local clock hour) by
inserting a row; the unique index turns a duplicate or late call into a no-op.
The column is nullable so existing rows and manual runs are unaffected
(Postgres treats NULLs as distinct in a unique index). Additive only.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "q8r9s0t1u2v3"
down_revision: str | None = "p7q8r9s0t1u2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_job_executions_job_slot"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("job_executions")}
    if "slot_key" not in columns:
        op.add_column("job_executions", sa.Column("slot_key", sa.String(length=100), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("job_executions")}
    if INDEX_NAME not in indexes:
        op.create_index(INDEX_NAME, "job_executions", ["job_name", "slot_key"], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="job_executions")
    op.drop_column("job_executions", "slot_key")
