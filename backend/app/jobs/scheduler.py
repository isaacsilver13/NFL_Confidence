"""Application scheduler for NFL imports, locks, scoring, and reminders."""

import logging
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import SessionLocal
from app.jobs.job_runner import JOB_LOCK_IDS, acquire_advisory_lock, release_advisory_lock
from app.jobs.nfl_schedule import (
    lock_expired_picks,
    run_current_week_sync,
    run_next_week_import,
    send_weekly_reminders,
)
from app.models.job_execution import JobExecution

logger = logging.getLogger(__name__)
EASTERN = ZoneInfo("America/New_York")

# Maps each scheduler job id to the advisory lock used by the admin-triggered
# job of the same underlying work (see app.jobs.job_runner.JOB_LOCK_IDS). Two
# scheduler jobs (Sunday and Monday/Thursday score sync) intentionally share
# a lock since they call the same underlying sync.
_SCHEDULER_LOCK_NAMES = {
    "schedule_import": "import_games",
    "sunday_score_sync": "sync_scores",
    "monday_thursday_score_sync": "sync_scores",
    "lock_expired_picks": "lock_picks",
    "weekly_picks_reminder": "send_reminders",
}


def _run_logged(job_name: str, job_func) -> int | None:
    """Run a scheduled job with comprehensive logging and audit trail.

    Acquires the same PostgreSQL advisory lock used by the admin-triggered
    job runner (see app.jobs.job_runner) before running, so a manually
    triggered job and this cron trigger can never execute the same work
    concurrently. If the lock is already held, the run is skipped rather
    than queued.

    Args:
        job_name: Identifier for this job (e.g., "import_games")
        job_func: Callable that runs the job

    Returns:
        Job result (usually count of items processed), or None if skipped
        or failed.
    """
    start_time = time.time()
    start_datetime = datetime.now(timezone.utc)

    lock_id = JOB_LOCK_IDS[_SCHEDULER_LOCK_NAMES[job_name]]

    logger.info("Job starting", extra={"job_name": job_name})

    with SessionLocal() as db:
        if not acquire_advisory_lock(db, lock_id):
            logger.warning(
                "Skipping job because its lock is held by another run",
                extra={"job_name": job_name},
            )
            return None

        try:
            # Create audit record
            execution = JobExecution(
                job_name=job_name,
                started_at=start_datetime,
                status="running",
            )
            db.add(execution)
            db.commit()

            try:
                # Run the job
                result = job_func()

                # Mark success
                elapsed = time.time() - start_time
                execution.status = "success"
                execution.completed_at = datetime.now(timezone.utc)
                execution.result_count = result if isinstance(result, int) else None

                logger.info(
                    "Job completed successfully",
                    extra={
                        "job_name": job_name,
                        "elapsed_seconds": f"{elapsed:.2f}",
                        "result_count": result,
                    },
                )

                return result

            except Exception as e:
                # Mark failure
                elapsed = time.time() - start_time
                execution.status = "failed"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = str(e)[:2000]  # Truncate to fit schema

                logger.exception(
                    "Job failed",
                    extra={"job_name": job_name, "elapsed_seconds": f"{elapsed:.2f}"},
                    exc_info=e,
                )

                return None

            finally:
                # Always save audit record
                db.commit()
        finally:
            release_advisory_lock(db, lock_id)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(
        timezone=EASTERN,
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 900},
    )
    scheduler.add_job(
        lambda: _run_logged("schedule_import", run_next_week_import),
        CronTrigger(day_of_week="tue", hour=10, minute=0, timezone=EASTERN),
        id="schedule_import",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_logged("lock_expired_picks", lock_expired_picks),
        IntervalTrigger(minutes=1, timezone=EASTERN),
        id="lock_expired_picks",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_logged("sunday_score_sync", run_current_week_sync),
        CronTrigger(day_of_week="sun", hour="8-21", minute=0, timezone=EASTERN),
        id="sunday_score_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_logged("monday_thursday_score_sync", run_current_week_sync),
        CronTrigger(day_of_week="mon,thu", hour="20-22", minute=0, timezone=EASTERN),
        id="monday_thursday_score_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_logged("weekly_picks_reminder", send_weekly_reminders),
        CronTrigger(day_of_week="wed", hour=18, minute=0, timezone=EASTERN),
        id="weekly_picks_reminder",
        replace_existing=True,
    )
    return scheduler
