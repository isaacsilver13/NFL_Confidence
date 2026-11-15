"""Admin API for job monitoring and manual runs.

Every job run, scheduled or manual, goes through `app.jobs.tick.run_slot`, so it is claimed and
logged to `job_executions` exactly like the cron tick's runs. There is no second job system.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_active_league_owner
from app.core.responses import success
from app.db.session import get_db
from app.jobs import tick
from app.models.job_execution import JobExecution

# Commissioners only (the league owner role, which co-commissioners share).
router = APIRouter(
    prefix="/api/v1", tags=["admin"], dependencies=[Depends(get_active_league_owner)]
)
logger = logging.getLogger(__name__)

# `is_overdue` is only meaningful for jobs with a tight, predictable cadence; jobs that only run on
# specific days of the week are reported without one rather than guessing a threshold that would
# false-positive on every other day. Every tick job is listed.
_OVERDUE_AFTER: dict[str, timedelta | None] = {
    "overnight_score_sync": timedelta(hours=36),
}


def _execution(row: JobExecution) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "job_name": row.job_name,
        "slot_key": row.slot_key,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "result_count": row.result_count,
        "error_message": row.error_message,
    }


@router.get("/admin/jobs/status")
def get_job_status(db: Session = Depends(get_db)) -> dict:
    """Latest run and health of every scheduled job."""
    job_status: dict[str, Any] = {}
    for job_name in tick.JOB_FUNCTIONS:
        last_run = db.execute(
            select(JobExecution)
            .where(JobExecution.job_name == job_name)
            .order_by(JobExecution.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if last_run is None:
            job_status[job_name] = {"last_run": None, "status": "never_run", "is_overdue": True}
            continue

        last_run_time = last_run.completed_at or last_run.started_at
        elapsed = datetime.now(timezone.utc) - last_run_time if last_run_time else None
        overdue_after = _OVERDUE_AFTER.get(job_name)
        is_overdue = bool(
            elapsed
            and (
                (last_run.status == "running" and elapsed > timedelta(hours=1))
                or (overdue_after is not None and elapsed > overdue_after)
            )
        )
        job_status[job_name] = {
            "last_run": _execution(last_run),
            "status": last_run.status,
            "is_overdue": is_overdue,
            "elapsed_minutes": int(elapsed.total_seconds() / 60) if elapsed else None,
        }
    return success(job_status)


@router.get("/admin/jobs/runs")
def list_job_runs(
    job_name: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query(pattern="^(running|success|failed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
) -> dict:
    """Recent runs (scheduled and manual), newest first."""
    query = select(JobExecution).order_by(JobExecution.created_at.desc()).limit(limit)
    if job_name:
        if job_name not in tick.JOB_FUNCTIONS:
            raise HTTPException(status_code=400, detail=f"Invalid job name: {job_name}")
        query = query.where(JobExecution.job_name == job_name)
    if status:
        query = query.where(JobExecution.status == status)
    runs = db.execute(query).scalars().all()
    return success({"runs": [_execution(run) for run in runs], "count": len(runs)})


@router.get("/admin/jobs/runs/{run_id}")
def get_job_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    run = db.get(JobExecution, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Job run not found")
    return success(_execution(run))


@router.post("/admin/jobs/{job_name}/trigger")
def trigger_job(job_name: str) -> dict:
    """Run a scheduled job now. The slot is per minute, so a double click runs it once; the job
    bodies keep their own guarantees (reminders are de-duplicated per member, score syncs are
    atomic). Runs in the threadpool: the jobs do blocking database and HTTP work."""
    if job_name not in tick.JOB_FUNCTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown job: {job_name}. Valid jobs: {sorted(tick.JOB_FUNCTIONS)}",
        )
    slot = "manual:" + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    entry = tick.run_slot(job_name, slot)
    logger.info("Manually triggered job %s: %s", job_name, entry["status"])
    if entry["status"] == "skipped":
        raise HTTPException(status_code=409, detail=f"Job {job_name} already ran this minute.")
    return success(entry)
