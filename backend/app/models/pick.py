"""Pick model — a user's confidence pick for a single game."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.nfl_game import NflGame
    from app.models.user import User


class Pick(Base):
    __tablename__ = "picks"
    __table_args__ = (UniqueConstraint("user_id", "game_id", name="uq_picks_user_game"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nfl_games.id", ondelete="CASCADE"), index=True
    )
    picked_team: Mapped[str] = mapped_column(String(64))
    confidence_value: Mapped[int] = mapped_column(Integer)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    points_earned: Mapped[int | None] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="picks")
    game: Mapped["NflGame"] = relationship(back_populates="picks")

    def __repr__(self) -> str:
        return (
            f"<Pick user_id={self.user_id} game_id={self.game_id} "
            f"confidence={self.confidence_value}>"
        )
