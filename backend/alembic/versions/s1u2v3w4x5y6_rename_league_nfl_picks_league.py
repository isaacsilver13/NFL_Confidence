"""Rename the local league to "NFL Picks League".

Revision ID: s1u2v3w4x5y6
Revises: s0t1u2v3w4x5
Create Date: 2026-10-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "s1u2v3w4x5y6"
down_revision: str | None = "s0t1u2v3w4x5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_NAMES = ("Local NFL Confidence League", "2026 NFL Confidence League")
NEW_NAME = "NFL Picks League"


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE leagues SET name = :new WHERE name IN :olds").bindparams(
            sa.bindparam("olds", value=OLD_NAMES, expanding=True), new=NEW_NAME
        )
    )


def downgrade() -> None:
    # Lossy by design: restores only the original local name.
    op.execute(
        sa.text("UPDATE leagues SET name = :old WHERE name = :new").bindparams(
            new=NEW_NAME, old=OLD_NAMES[0]
        )
    )
