"""Application scheduler for NFL imports, locks, scoring, and reminders."""

import logging
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.db.session import SessionLocal
from app.jobs.nfl_schedule import (
    get_next_lock_deadline,
    lock_expired_picks,
    run_current_week_sync,
    run_next_week_import,
    send_weekly_reminders,
    send_weekly_report,
)
from app.models.job_execution import JobExecution

LOCK_JOB_ID = "lock_expired_picks_once"

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


def _lock_and_rearm(scheduler: BackgroundScheduler) -> int | None:
    """Run the lock job, then re-arm it for whatever should lock next."""
    result = _run_logged("lock_expired_picks", lock_expired_picks)
    schedule_next_lock(scheduler)
    return result


def _import_and_rearm(scheduler: BackgroundScheduler, job_name: str, job_func) -> int | None:
    """Run an import/sync job, then re-arm the lock job since it may have
    changed which week/games are current."""
    result = _run_logged(job_name, job_func)
    schedule_next_lock(scheduler)
    return result


def schedule_next_lock(scheduler: BackgroundScheduler) -> None:
    """(Re)arm a one-time job at the current week's earliest unlocked kickoff.

    Replaces polling the database every minute: this only queries when
    scheduling state might have changed (startup, after an import/sync, or
    right after a lock fires), so the database can actually go idle and
    Neon's scale-to-zero can kick in between kickoffs.
    """
    with SessionLocal() as db:
        deadline = get_next_lock_deadline(db)

    if deadline is None:
        try:
            scheduler.remove_job(LOCK_JOB_ID)
        except JobLookupError:
            pass
        return

    run_date = max(deadline, datetime.now(timezone.utc))
    scheduler.add_job(
        lambda: _lock_and_rearm(scheduler),
        DateTrigger(run_date=run_date, timezone=timezone.utc),
        id=LOCK_JOB_ID,
        replace_existing=True,
    )


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(
        timezone=EASTERN,
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 900},
    )
    scheduler.add_job(
        lambda: _import_and_rearm(scheduler, "schedule_import", run_next_week_import),
        # Opens next week's picks on the Monday of the current week (e.g. week 3
        # opens Monday morning of week 2) rather than waiting until Tuesday.
        # import_games re-syncs spreads/kickoff times on every later sync, so
        # early-imported data self-corrects before that week's own lock.
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone=EASTERN),
        id="schedule_import",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _import_and_rearm(scheduler, "sunday_score_sync", run_current_week_sync),
        CronTrigger(day_of_week="sun", hour="8-21", minute=0, timezone=EASTERN),
        id="sunday_score_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _import_and_rearm(scheduler, "monday_thursday_score_sync", run_current_week_sync),
        CronTrigger(day_of_week="mon,thu", hour="20-23", minute=0, timezone=EASTERN),
        id="monday_thursday_score_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _import_and_rearm(scheduler, "overnight_score_sync", run_current_week_sync),
        # Primetime games (SNF/MNF/TNF) often finish after the day-specific
        # sync windows above have ended for the night. A single early-morning
        # pass, every day, catches whichever game finished late without
        # needing a separate cron entry per day it could happen on.
        CronTrigger(hour=3, minute=0, timezone=EASTERN),
        id="overnight_score_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_logged("weekly_picks_reminder", send_weekly_reminders),
        CronTrigger(day_of_week="wed", hour=18, minute=0, timezone=EASTERN),
        id="weekly_picks_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_logged("weekly_report", send_weekly_report),
        CronTrigger(day_of_week="tue", hour=9, minute=0, timezone=EASTERN),
        id="weekly_report",
        replace_existing=True,
    )
    # Safety net in case the one-time kickoff job above is ever lost (e.g. a
    # mid-week redeploy racing the in-memory DateTrigger). Six checks a day is
    # negligible DB load and nowhere near enough to block scale-to-zero.
    scheduler.add_job(
        lambda: _lock_and_rearm(scheduler),
        CronTrigger(hour="*/6", timezone=EASTERN),
        id="lock_expired_picks_safety_net",
        replace_existing=True,
    )
    return scheduler
