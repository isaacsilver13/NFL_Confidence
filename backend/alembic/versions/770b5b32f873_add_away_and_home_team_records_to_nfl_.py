"""add away and home team records to nfl_games

Revision ID: 770b5b32f873
Revises: df1839c59f00
Create Date: 2026-09-24 11:40:05.399173

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "770b5b32f873"
down_revision: str | None = "df1839c59f00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("nfl_games", sa.Column("away_record", sa.String(length=16), nullable=True))
    op.add_column("nfl_games", sa.Column("home_record", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("nfl_games", "home_record")
    op.drop_column("nfl_games", "away_record")
