"""League model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.invite import Invite
    from app.models.league_member import LeagueMember
    from app.models.season_result import SeasonResult
    from app.models.user import User
    from app.models.weekly_result import WeeklyResult


class League(TimestampMixin, Base):
    __tablename__ = "leagues"
    __table_args__ = (
        Index(
            "uq_leagues_one_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active IS TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    season: Mapped[int] = mapped_column(Integer)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped["User"] = relationship(back_populates="owned_leagues")
    members: Mapped[list["LeagueMember"]] = relationship(
        back_populates="league", cascade="all, delete-orphan"
    )
    invites: Mapped[list["Invite"]] = relationship(
        back_populates="league", cascade="all, delete-orphan"
    )
    weekly_results: Mapped[list["WeeklyResult"]] = relationship(back_populates="league")
    season_results: Mapped[list["SeasonResult"]] = relationship(back_populates="league")

    def __repr__(self) -> str:
        return f"<League id={self.id} name={self.name!r}>"
