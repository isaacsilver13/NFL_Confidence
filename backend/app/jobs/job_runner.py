"""Job runner with PostgreSQL advisory lock for background scheduled jobs.

This module implements a production-grade job runner that uses PostgreSQL advisory
locks to ensure only one instance of each job runs at a time across the entire
distributed system (e.g., all Fly.io worker processes).

Jobs are:
- import_games: Fetch and store upcoming/live NFL games
- sync_scores: Update scores from completed games
- lock_picks: Lock all picks for games that have started
- send_reminders: Send weekly reminder emails to users with incomplete picks

Each job function is a thin async wrapper around the equivalent synchronous
implementation in `app.jobs.nfl_schedule` — the same code the scheduler's
cron triggers call directly. Keeping a single implementation per job means
a manual admin trigger and a scheduled run can never disagree on behavior,
and combining that with the advisory lock here means they can never race
each other either.
"""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import JobStatus
from app.models.job_run import JobRun

logger = logging.getLogger(__name__)

# PostgreSQL advisory lock IDs for each job (arbitrary unique integers)
JOB_LOCK_IDS = {
    "import_games": 1001,
    "sync_scores": 1002,
    "lock_picks": 1003,
    "send_reminders": 1004,
}


class JobLockError(Exception):
    """Raised when unable to acquire job lock."""

    pass


def acquire_advisory_lock(db: Session, lock_id: int) -> bool:
    """Acquire a PostgreSQL advisory lock for a job.

    Advisory locks are application-level locks that can be used to coordinate
    between multiple processes. They're perfect for ensuring only one job runs
    at a time across all application instances.

    Args:
        db: Database session
        lock_id: Unique lock identifier for the job

    Returns:
        True if lock was acquired, False if another process holds it
    """
    result = db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id})
    acquired = bool(result.scalar())
    logger.info(f"Advisory lock {lock_id}: acquired={acquired}")
    return acquired


def release_advisory_lock(db: Session, lock_id: int) -> None:
    """Release a PostgreSQL advisory lock.

    Args:
        db: Database session
        lock_id: Unique lock identifier for the job
    """
    db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
    logger.info(f"Advisory lock {lock_id}: released")


async def run_job(
    job_name: str,
    job_fn: Callable[[Session], Awaitable[None]],
    db_session: Session | None = None,
) -> JobRun:
    """Run a job with advisory locking and observability tracking.

    This is the main entry point for executing a job. It:
    1. Acquires an advisory lock to prevent concurrent execution
    2. Creates a JobRun record to track execution
    3. Runs the job function
    4. Updates JobRun with status, duration, and any errors
    5. Releases the lock

    Args:
        job_name: Name of the job (e.g., "import_games")
        job_fn: Async callable that performs the job work
        db_session: Optional existing database session (creates one if not provided)

    Returns:
        JobRun model instance with execution results

    Raises:
        JobLockError: If unable to acquire lock (another instance running)
    """
    if job_name not in JOB_LOCK_IDS:
        raise ValueError(f"Unknown job: {job_name}")

    # Use provided session or create new one
    if db_session is None:
        db_session = SessionLocal()

    lock_id = JOB_LOCK_IDS[job_name]
    job_run = None

    try:
        # Try to acquire the lock
        if not acquire_advisory_lock(db_session, lock_id):
            logger.warning(f"Job {job_name} is already running (lock held by another process)")
            raise JobLockError(f"Job {job_name} is already running")

        # Create JobRun record
        job_run = JobRun(
            id=uuid.uuid4(),
            job_name=job_name,
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(job_run)
        db_session.commit()
        logger.info(f"Job {job_name} ({job_run.id}): started")

        # Run the job
        start_time = datetime.now(timezone.utc)
        try:
            await job_fn(db_session)
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Mark as completed
            job_run.status = JobStatus.COMPLETED
            job_run.completed_at = end_time
            job_run.duration_ms = duration_ms
            db_session.commit()
            logger.info(f"Job {job_name} ({job_run.id}): completed in {duration_ms}ms")

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Mark as failed
            error_msg = str(e)[:1024]  # Truncate to fit in database
            job_run.status = JobStatus.FAILED
            job_run.completed_at = end_time
            job_run.duration_ms = duration_ms
            job_run.error_message = error_msg
            db_session.commit()
            logger.error(
                f"Job {job_name} ({job_run.id}): failed after {duration_ms}ms: {error_msg}",
                exc_info=True,
            )
            # Re-raise to caller
            raise

    finally:
        # Always release the lock
        try:
            release_advisory_lock(db_session, lock_id)
        except Exception as e:
            logger.error(f"Failed to release advisory lock {lock_id}: {e}", exc_info=True)
        finally:
            # Close session if we created it
            if db_session is not None:
                db_session.close()

    return job_run


async def import_games(db: Session) -> None:
    """Import the next unimported week for the active league.

    Delegates to `nfl_schedule.run_next_week_import`, the same implementation
    the scheduler's cron trigger uses, so a manual admin trigger cannot drift
    from (or race against) the scheduled behavior. Runs in a thread since the
    underlying call is synchronous and does network I/O.
    """
    from app.jobs import nfl_schedule

    logger.info("Starting import_games job")
    imported = await asyncio.to_thread(nfl_schedule.run_next_week_import)
    logger.info(f"import_games job complete: {imported} games imported")


async def sync_scores(db: Session) -> None:
    """Import the active week's games and recompute finalized scores.

    Delegates to `nfl_schedule.run_current_week_sync`, the same implementation
    the scheduler's cron triggers use.
    """
    from app.jobs import nfl_schedule

    logger.info("Starting sync_scores job")
    imported = await asyncio.to_thread(nfl_schedule.run_current_week_sync)
    logger.info(f"sync_scores job complete: {imported} games imported")


async def lock_picks(db: Session) -> None:
    """Lock the active week's picks once its earliest kickoff has passed.

    Delegates to `nfl_schedule.lock_expired_picks`, the same week-level lock
    semantics the scheduler applies every minute, instead of the previous
    per-game locking logic that disagreed with the documented design.
    """
    from app.jobs import nfl_schedule

    logger.info("Starting lock_picks job")
    locked = await asyncio.to_thread(nfl_schedule.lock_expired_picks)
    logger.info(f"lock_picks job complete: {locked} picks locked")


async def send_reminders(db: Session) -> None:
    """Send weekly reminder emails for incomplete picks.

    Delegates to `nfl_schedule.send_weekly_reminders`, which records each
    delivery in `NotificationDelivery` so repeated or concurrent runs cannot
    re-send to a member who was already reminded for the week.
    """
    from app.jobs import nfl_schedule

    logger.info("Starting send_reminders job")
    sent = await asyncio.to_thread(nfl_schedule.send_weekly_reminders)
    logger.info(f"send_reminders job complete: {sent} reminders sent")
