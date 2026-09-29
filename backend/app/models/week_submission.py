"""WeekSubmission model — records that a user has formally submitted their confidence
picks for a week, distinct from the autosaved draft picks themselves."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.nfl_week import NflWeek
    from app.models.user import User


class WeekSubmission(Base):
    __tablename__ = "week_submissions"
    __table_args__ = (UniqueConstraint("user_id", "week_id", name="uq_week_submissions_user_week"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nfl_weeks.id", ondelete="CASCADE"), index=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship()
    week: Mapped["NflWeek"] = relationship()

    def __repr__(self) -> str:
        return f"<WeekSubmission user_id={self.user_id} week_id={self.week_id}>"
