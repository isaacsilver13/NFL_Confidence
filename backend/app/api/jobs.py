"""Admin API for job management and monitoring."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.responses import success
from app.db.session import get_db
from app.jobs.job_runner import (
    JOB_LOCK_IDS,
    import_games,
    lock_picks,
    run_job,
    send_reminders,
    sync_scores,
)
from app.models.enums import JobStatus
from app.models.job_run import JobRun
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["admin"])
logger = logging.getLogger(__name__)

# Job function mapping
JOB_FUNCTIONS = {
    "import_games": import_games,
    "sync_scores": sync_scores,
    "lock_picks": lock_picks,
    "send_reminders": send_reminders,
}


class JobRunResponse:
    """Serializable response for a JobRun."""

    def __init__(self, job_run: JobRun):
        self.id = str(job_run.id)
        self.job_name = job_run.job_name
        self.status = job_run.status.value
        self.started_at = job_run.started_at.isoformat() if job_run.started_at else None
        self.completed_at = job_run.completed_at.isoformat() if job_run.completed_at else None
        self.duration_ms = job_run.duration_ms
        self.error_message = job_run.error_message


@router.get("/admin/jobs/status")
def get_job_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get status of all background jobs - recent runs and health.

    Returns the last run status for each job and alerts if any are stuck.
    Admin-only endpoint.
    """
    _verify_admin(current_user, db)

    # Get the last run for each job
    job_status: dict[str, Any] = {}
    for job_name in JOB_LOCK_IDS.keys():
        last_run = db.execute(
            select(JobRun)
            .where(JobRun.job_name == job_name)
            .order_by(JobRun.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if last_run is None:
            job_status[job_name] = {
                "last_run": None,
                "status": "never_run",
                "is_overdue": True,
            }
        else:
            is_running = last_run.status == JobStatus.RUNNING
            last_run_time = last_run.completed_at or last_run.started_at
            elapsed = datetime.now(timezone.utc) - last_run_time if last_run_time else None

            # Alert if job is stuck (running for >1 hour) or hasn't completed in expected time
            is_overdue = False
            if is_running and elapsed and elapsed > timedelta(hours=1):
                is_overdue = True
            elif (
                last_run.status == JobStatus.COMPLETED and elapsed and elapsed > timedelta(hours=4)
            ):
                is_overdue = True

            job_status[job_name] = {
                "last_run": JobRunResponse(last_run).__dict__,
                "status": last_run.status.value,
                "is_overdue": is_overdue,
                "elapsed_minutes": int(elapsed.total_seconds() / 60) if elapsed else None,
            }

    return success(job_status)


@router.get("/admin/jobs/runs")
def list_job_runs(
    job_name: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List recent job runs with optional filtering.

    Query parameters:
    - job_name: Filter by job name (import_games, sync_scores, lock_picks, send_reminders)
    - status: Filter by status (pending, running, completed, failed)
    - limit: Number of results (1-100, default 20)
    """
    _verify_admin(current_user, db)

    query = select(JobRun).order_by(JobRun.created_at.desc()).limit(limit)

    if job_name:
        if job_name not in JOB_LOCK_IDS:
            raise HTTPException(status_code=400, detail=f"Invalid job name: {job_name}")
        query = query.where(JobRun.job_name == job_name)

    if status:
        try:
            status_enum = JobStatus(status)
            query = query.where(JobRun.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}") from None

    runs = db.execute(query).scalars().all()

    return success(
        {
            "runs": [JobRunResponse(run).__dict__ for run in runs],
            "count": len(runs),
        }
    )


@router.get("/admin/jobs/runs/{run_id}")
def get_job_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get details for a specific job run."""
    _verify_admin(current_user, db)

    try:
        import uuid

        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format") from None

    run = db.get(JobRun, run_uuid)
    if run is None:
        raise HTTPException(status_code=404, detail="Job run not found")

    return success(JobRunResponse(run).__dict__)


@router.post("/admin/jobs/{job_name}/trigger")
async def trigger_job(
    job_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Manually trigger a background job.

    WARNING: Use with caution. Some jobs (import_games, sync_scores) perform
    external API calls and expensive database operations. Lock protection ensures
    only one instance runs at a time.

    Returns the JobRun record for tracking completion.
    """
    _verify_admin(current_user, db)

    if job_name not in JOB_FUNCTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown job: {job_name}. Valid jobs: {list(JOB_LOCK_IDS.keys())}",
        )

    try:
        job_fn = JOB_FUNCTIONS[job_name]
        job_run = await run_job(job_name, job_fn, db)
        logger.info(f"Manually triggered job {job_name}: {job_run.status.value}")
        return success(
            {
                "job_run": JobRunResponse(job_run).__dict__,
                "message": f"Job {job_name} completed with status {job_run.status.value}",
            }
        )
    except Exception as e:
        from app.jobs.job_runner import JobLockError

        if isinstance(e, JobLockError):
            raise HTTPException(
                status_code=409,
                detail=f"Job {job_name} is already running. Please wait for it to complete.",
            ) from e
        logger.error(f"Job {job_name} failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Job {job_name} failed: {str(e)[:100]}",
        ) from e


def _verify_admin(current_user: User, db: Session) -> None:
    """Verify that the current user is an admin (league owner).

    In v1 single-league mode, the league owner is the only admin.
    """
    from app.services import league_service

    try:
        league = league_service.get_active_league(db)
        if league.owner_id != current_user.id:
            raise ForbiddenError("Only the league owner can access admin endpoints")
    except Exception as e:
        raise ForbiddenError(f"Admin access denied: {e}") from e
