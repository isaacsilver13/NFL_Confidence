"""MnfGuess model: a member's Monday Night total-points and total-offense guesses for a week.

Treated like one more pick: a card is not complete without them when the week has a
Monday game. Used only to break weekly ties.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class MnfGuess(Base):
    __tablename__ = "mnf_guesses"
    __table_args__ = (UniqueConstraint("user_id", "week_id", name="uq_mnf_guesses_user_week"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nfl_weeks.id", ondelete="CASCADE"), index=True
    )
    points: Mapped[int] = mapped_column(Integer)
    yards: Mapped[int] = mapped_column(Integer)
