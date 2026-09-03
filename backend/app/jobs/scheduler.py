"""Application scheduler for NFL imports, locks, scoring, and reminders."""

import logging
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import SessionLocal
from app.jobs.nfl_schedule import (
    lock_expired_picks,
    run_current_week_sync,
    run_next_week_import,
    send_weekly_reminders,
)
from app.models.job_execution import JobExecution

logger = logging.getLogger(__name__)
EASTERN = ZoneInfo("America/New_York")


def _run_logged(job_name: str, job_func) -> int | None:
    """Run a scheduled job with comprehensive logging and audit trail.

    Args:
        job_name: Identifier for this job (e.g., "import_games")
        job_func: Callable that runs the job

    Returns:
        Job result (usually count of items processed)
    """
    start_time = time.time()
    start_datetime = datetime.now(timezone.utc)

    logger.info("Job starting", extra={"job_name": job_name})

    with SessionLocal() as db:
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
