"""Merge the job_executions.slot_key migration with the dev-only migration chain.

Prod's history ends at p7q8r9s0t1u2 -> q8r9s0t1u2v3 (slot_key). Dev additionally has
8e14dad570d9 -> 236e478e4f67 -> df1839c59f00 -> 770b5b32f873. This empty revision joins
the two so `alembic upgrade head` has a single head; each branch applies whichever side
the database is missing. No schema changes.
"""

from collections.abc import Sequence

revision: str = "r9s0t1u2v3w4"
down_revision: str | Sequence[str] | None = ("770b5b32f873", "q8r9s0t1u2v3")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
