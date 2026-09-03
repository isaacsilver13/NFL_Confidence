"""JobExecution model — audit log for scheduled job runs."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class JobExecution(Base):
    """Records each execution of a scheduled job for monitoring and debugging."""

    __tablename__ = "job_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_name: Mapped[str] = mapped_column(String(100))  # "import_games", "score_week", etc.
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # "running", "success", "failed"
    result_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Games imported, picks locked, results scored, etc.
    error_message: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )  # Truncated exception message
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<JobExecution job_name={self.job_name} status={self.status} "
            f"started_at={self.started_at}>"
        )
