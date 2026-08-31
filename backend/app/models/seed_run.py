"""Database marker for completed one-time demo data fixtures."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SeedRun(Base):
    __tablename__ = "seed_runs"

    fixture_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    league_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    week_count: Mapped[int] = mapped_column(Integer, nullable=False)
    game_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pick_count: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<SeedRun fixture_key={self.fixture_key!r} season={self.season}>"
