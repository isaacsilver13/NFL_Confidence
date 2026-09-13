"""Create missing season-result rows for existing league members."""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "o6p7q8r9s0t1"
down_revision: str | None = "n5o6p7q8r9s0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    missing_rows = list(
        bind.execute(
            sa.text(
                """
                SELECT lm.league_id, lm.user_id, l.season
                FROM league_members AS lm
                JOIN leagues AS l ON l.id = lm.league_id
                LEFT JOIN season_results AS sr
                    ON sr.league_id = lm.league_id
                    AND sr.user_id = lm.user_id
                    AND sr.season = l.season
                WHERE sr.id IS NULL
                """
            )
        ).mappings()
    )

    for row in missing_rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO season_results (id, league_id, user_id, season)
                VALUES (:id, :league_id, :user_id, :season)
                """
            ),
            {
                "id": uuid.uuid4(),
                "league_id": row["league_id"],
                "user_id": row["user_id"],
                "season": row["season"],
            },
        )


def downgrade() -> None:
    # Backfilled rows may have received real scores after this migration.
    pass
