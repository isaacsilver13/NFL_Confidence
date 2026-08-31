"""NflGame model — a single scheduled/played NFL game."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import GameStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.nfl_week import NflWeek
    from app.models.pick import Pick


class NflGame(TimestampMixin, Base):
    __tablename__ = "nfl_games"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nfl_weeks.id", ondelete="CASCADE"), index=True
    )
    espn_game_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    kickoff_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    home_team: Mapped[str] = mapped_column(String(64))
    away_team: Mapped[str] = mapped_column(String(64))
    venue_name: Mapped[str | None] = mapped_column(String(255))
    venue_location: Mapped[str | None] = mapped_column(String(255))
    spread_team: Mapped[str | None] = mapped_column(String(64))
    spread: Mapped[float | None] = mapped_column(Float)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    winning_team: Mapped[str | None] = mapped_column(String(64), index=True)
    game_status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus, name="game_status", values_callable=lambda e: [m.value for m in e]),
        default=GameStatus.SCHEDULED,
        index=True,
    )
    is_tie: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    week: Mapped["NflWeek"] = relationship(back_populates="games")
    picks: Mapped[list["Pick"]] = relationship(back_populates="game", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<NflGame espn_game_id={self.espn_game_id!r} {self.away_team}@{self.home_team}>"
