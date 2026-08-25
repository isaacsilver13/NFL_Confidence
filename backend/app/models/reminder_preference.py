"""ReminderPreference model — a user's email notification preferences."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class ReminderPreference(Base):
    __tablename__ = "reminder_preferences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    thursday_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    sunday_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    kickoff_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="reminder_preference")

    def __repr__(self) -> str:
        return f"<ReminderPreference user_id={self.user_id}>"
