"""JobRun model — tracks execution of scheduled background jobs for observability."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import JobStatus
from app.models.mixins import TimestampMixin


class JobRun(Base, TimestampMixin):
    __tablename__ = "job_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_name: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[JobStatus] = mapped_column(String(32), default=JobStatus.PENDING, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(String(1024))

    def __repr__(self) -> str:
        return (
            f"<JobRun job_name={self.job_name!r} status={self.status!r} "
            f"duration_ms={self.duration_ms}>"
        )
