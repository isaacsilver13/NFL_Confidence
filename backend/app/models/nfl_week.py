"""NflWeek model — a single week of the NFL season."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import WeekStatus

if TYPE_CHECKING:
    from app.models.nfl_game import NflGame
    from app.models.weekly_result import WeeklyResult


class NflWeek(Base):
    __tablename__ = "nfl_weeks"
    __table_args__ = (UniqueConstraint("season", "week_number", name="uq_nfl_weeks_season_week"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week_number: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[WeekStatus] = mapped_column(
        Enum(WeekStatus, name="week_status", values_callable=lambda e: [m.value for m in e]),
        default=WeekStatus.PRESEASON,
    )

    games: Mapped[list["NflGame"]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
    weekly_results: Mapped[list["WeeklyResult"]] = relationship(back_populates="week")

    def __repr__(self) -> str:
        return f"<NflWeek season={self.season} week_number={self.week_number}>"
