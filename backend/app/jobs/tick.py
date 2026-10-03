"""Run whichever scheduled jobs are due right now.

Called by `POST /api/v1/internal/tick`, which an external cron (GitHub Actions)
hits on a fixed cadence. The Fly machine sleeps between calls; the request
itself wakes it. Each job slot (see `app.jobs.schedule`) is claimed by inserting
a `job_executions` row with a unique `(job_name, slot_key)`, so a duplicate or
late call in the same hour is a no-op and results are never double-counted. A failed or
abandoned (stale `running`) slot can be re-claimed by a later call.
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs.nfl_schedule import (
    lock_expired_picks,
    run_current_week_sync,
    run_next_week_import,
    send_weekly_reminders,
    send_weekly_report,
)
from app.jobs.schedule import ScheduleConfig, due_slots
from app.models.job_execution import JobExecution

logger = logging.getLogger(__name__)

# A process younger than this when a tick arrives was (almost certainly) started
# by that tick's request, i.e. the machine was asleep.
COLD_START_WINDOW_SECONDS = 120
# A `running` row older than this belongs to a run that died (machine stopped mid-job).
STALE_RUNNING_AFTER = timedelta(minutes=10)
_PROCESS_STARTED = time.monotonic()

# Resolved at call time (not import time) so tests can swap entries.
JOB_FUNCTIONS: dict[str, Callable[[], Any]] = {
    "schedule_import": run_next_week_import,
    "sunday_score_sync": run_current_week_sync,
    "monday_thursday_score_sync": run_current_week_sync,
    "overnight_score_sync": run_current_week_sync,
    "weekly_picks_reminder": send_weekly_reminders,
    "weekly_report": send_weekly_report,
    "lock_expired_picks": lock_expired_picks,
}


def _claim_slot(job_name: str, slot_key: str, started_at: datetime) -> Any | None:
    """Claim a slot for this run. Returns the row id, or None if it is taken.

    A slot is taken by a `success` row or a recent `running` row. A `failed` row or a
    stale `running` row (the run died) is re-claimed so the slot gets another attempt.
    """
    with SessionLocal() as db:
        stmt = pg_insert(JobExecution).values(
            job_name=job_name, slot_key=slot_key, started_at=started_at, status="running"
        )
        claimed = db.execute(
            stmt.on_conflict_do_update(
                index_elements=["job_name", "slot_key"],
                set_={
                    "started_at": started_at,
                    "status": "running",
                    "completed_at": None,
                    "result_count": None,
                    "error_message": None,
                },
                where=or_(
                    JobExecution.status == "failed",
                    and_(
                        JobExecution.status == "running",
                        JobExecution.started_at < started_at - STALE_RUNNING_AFTER,
                    ),
                ),
            ).returning(JobExecution.id)
        ).scalar_one_or_none()
        db.commit()
        return claimed


def _finish(execution_id: Any, *, status: str, result: Any, error: str | None) -> None:
    with SessionLocal() as db:
        execution = db.get(JobExecution, execution_id)
        if execution is None:  # pragma: no cover - row was just inserted
            return
        execution.status = status
        execution.completed_at = datetime.now(timezone.utc)
        execution.result_count = result if isinstance(result, int) else None
        execution.error_message = error[:2000] if error else None
        db.commit()


def run_tick(now: datetime | None = None) -> dict[str, Any]:
    """Claim and run every due slot; return a JSON-serializable summary."""
    started = time.monotonic()
    now = now or datetime.now(timezone.utc)
    cfg = ScheduleConfig.from_settings(get_settings())
    uptime = time.monotonic() - _PROCESS_STARTED
    cold_start = uptime < COLD_START_WINDOW_SECONDS

    slots = due_slots(now, cfg)
    logger.info(
        "Tick started",
        extra={"cold_start": cold_start, "uptime_seconds": round(uptime, 1), "due": len(slots)},
    )

    results: list[dict[str, Any]] = []
    for slot in slots:
        entry: dict[str, Any] = {"job": slot.job_name, "slot": slot.key}
        execution_id = _claim_slot(slot.job_name, slot.key, datetime.now(timezone.utc))
        if execution_id is None:
            entry["status"] = "skipped"
            logger.info("Job slot already claimed", extra={"job_name": slot.job_name})
            results.append(entry)
            continue

        job_started = time.monotonic()
        try:
            result = JOB_FUNCTIONS[slot.job_name]()
        except Exception as exc:  # a failed job must not fail the whole tick
            logger.exception("Job failed", extra={"job_name": slot.job_name})
            _finish(execution_id, status="failed", result=None, error=str(exc))
            entry.update(status="failed", error=str(exc)[:200])
        else:
            _finish(execution_id, status="success", result=result, error=None)
            entry.update(status="success", result_count=result if isinstance(result, int) else None)
            logger.info(
                "Job completed",
                extra={
                    "job_name": slot.job_name,
                    "result_count": entry["result_count"],
                    "elapsed_seconds": round(time.monotonic() - job_started, 2),
                },
            )
        results.append(entry)

    summary = {
        "ran_at": now.isoformat(),
        "timezone": cfg.timezone,
        "cold_start": cold_start,
        "uptime_seconds": round(uptime, 1),
        "jobs": results,
        "duration_seconds": round(time.monotonic() - started, 2),
    }
    logger.info(
        "Tick finished",
        extra={
            "ran": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
        },
    )
    return summary
