"""SeasonResult model — a user's cumulative scoring summary for a season within a league."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.league import League
    from app.models.user import User


class SeasonResult(Base):
    __tablename__ = "season_results"
    __table_args__ = (
        UniqueConstraint(
            "league_id", "user_id", "season", name="uq_season_results_league_user_season"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    league_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    season: Mapped[int] = mapped_column(Integer)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    weekly_wins: Mapped[int] = mapped_column(Integer, default=0)
    first_place_finishes: Mapped[int] = mapped_column(Integer, default=0)
    second_place_finishes: Mapped[int] = mapped_column(Integer, default=0)
    third_place_finishes: Mapped[int] = mapped_column(Integer, default=0)
    current_rank: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    league: Mapped["League"] = relationship(back_populates="season_results")
    user: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<SeasonResult league_id={self.league_id} user_id={self.user_id} season={self.season}>"
        )
