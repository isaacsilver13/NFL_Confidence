"""Remove the test label from the local league name.

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-09-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m4n5o6p7q8r9"
down_revision: str | None = "l3m4n5o6p7q8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE leagues SET name = :new_name WHERE name = :old_name").bindparams(
            new_name="Local NFL Confidence League",
            old_name="Local NFL Confidence Test League",
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE leagues SET name = :old_name WHERE name = :new_name").bindparams(
            new_name="Local NFL Confidence League",
            old_name="Local NFL Confidence Test League",
        )
    )
