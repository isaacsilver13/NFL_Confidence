"""backfill week submissions for existing picks

The weekly leaderboard now only shows members who have a WeekSubmission row for
that week (see app/services/leaderboard_service.py). Without this backfill,
every week completed before the Submit feature shipped would suddenly show an
empty leaderboard, since nobody could have formally "submitted" under a
concept that didn't exist yet. Synthesize a submission for every user/week
that already has at least one active (non-voided) pick, timestamped at their
latest pick for that week, so historical leaderboards keep working exactly as
before. Going forward, only an explicit Submit records a real submission.

Revision ID: df1839c59f00
Revises: 236e478e4f67
Create Date: 2026-09-21 15:40:10.647702

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "df1839c59f00"
down_revision: str | None = "236e478e4f67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT p.user_id, g.week_id, max(p.submitted_at) AS submitted_at
            FROM picks p
            JOIN nfl_games g ON g.id = p.game_id
            WHERE p.voided_at IS NULL
            GROUP BY p.user_id, g.week_id
            """
        )
    ).fetchall()
    if not rows:
        return
    bind.execute(
        sa.text(
            """
            INSERT INTO week_submissions (id, user_id, week_id, submitted_at)
            VALUES (:id, :user_id, :week_id, :submitted_at)
            ON CONFLICT (user_id, week_id) DO NOTHING
            """
        ),
        [
            {
                "id": str(uuid.uuid4()),
                "user_id": row.user_id,
                "week_id": row.week_id,
                "submitted_at": row.submitted_at,
            }
            for row in rows
        ],
    )


def downgrade() -> None:
    # Data backfill only; nothing to structurally reverse. Leaving the
    # synthesized rows in place on downgrade is intentional -- removing them
    # would re-break historical leaderboards for anyone still on the old code.
    pass
