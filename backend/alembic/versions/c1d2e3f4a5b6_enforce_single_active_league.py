"""enforce a single active league

Revision ID: c1d2e3f4a5b6
Revises: b7e8f9a0c1d2
Create Date: 2026-08-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b7e8f9a0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id, row_number() OVER (ORDER BY created_at, id) AS row_number
                FROM leagues
                WHERE is_active IS TRUE
            )
            UPDATE leagues
            SET is_active = FALSE
            FROM ranked
            WHERE leagues.id = ranked.id AND ranked.row_number > 1
            """
        )
    )
    op.create_index(
        "uq_leagues_one_active",
        "leagues",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_leagues_one_active", table_name="leagues")
