"""User model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.league import League
    from app.models.league_member import LeagueMember
    from app.models.pick import Pick
    from app.models.refresh_token import RefreshToken
    from app.models.reminder_preference import ReminderPreference


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(1024))

    owned_leagues: Mapped[list["League"]] = relationship(back_populates="owner")
    league_memberships: Mapped[list["LeagueMember"]] = relationship(back_populates="user")
    picks: Mapped[list["Pick"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reminder_preference: Mapped["ReminderPreference | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
