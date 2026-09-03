"""WeeklyResult model — a user's scoring summary for a single week within a league."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.league import League
    from app.models.nfl_week import NflWeek
    from app.models.user import User


class WeeklyResult(Base):
    __tablename__ = "weekly_results"
    __table_args__ = (
        Index("uq_weekly_results_user_week", "league_id", "week_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    league_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), index=True
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nfl_weeks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    correct_picks: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_picks: Mapped[int] = mapped_column(Integer, default=0)
    highest_confidence_win: Mapped[int] = mapped_column(Integer, default=0)
    weekly_rank: Mapped[int | None] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    league: Mapped["League"] = relationship(back_populates="weekly_results")
    week: Mapped["NflWeek"] = relationship(back_populates="weekly_results")
    user: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<WeeklyResult league_id={self.league_id} week_id={self.week_id} "
            f"user_id={self.user_id}>"
        )
