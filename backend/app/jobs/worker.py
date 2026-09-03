"""Worker process for running background jobs on a schedule."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.jobs.job_runner import import_games, lock_picks, run_job, send_reminders, sync_scores

logger = logging.getLogger(__name__)


class JobSchedule(TypedDict):
    interval: int
    description: str


# Job schedule configuration (all times in minutes from hour start)
JOB_SCHEDULE: dict[str, JobSchedule] = {
    "import_games": {"interval": 15, "description": "Import NFL games every 15 minutes"},
    "sync_scores": {"interval": 30, "description": "Sync scores every 30 minutes"},
    "lock_picks": {"interval": 5, "description": "Lock picks every 5 minutes"},
    "send_reminders": {"interval": 60, "description": "Send reminders every hour"},
}

# Track last run time for each job
last_run_times: dict[str, datetime | None] = {job_name: None for job_name in JOB_SCHEDULE}


async def should_run_job(job_name: str) -> bool:
    """Check if enough time has passed since last run."""
    interval_minutes = int(JOB_SCHEDULE[job_name]["interval"])
    last_run = last_run_times[job_name]

    if last_run is None:
        return True

    elapsed = datetime.now(timezone.utc) - last_run
    return elapsed >= timedelta(minutes=interval_minutes)


async def run_job_with_retry(
    job_name: str, job_fn: Callable[[Session], Awaitable[None]], max_retries: int = 3
) -> None:
    """Run job with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            db_session = SessionLocal()
            try:
                job_run = await run_job(job_name, job_fn, db_session)
                logger.info(
                    f"Job {job_name} completed: status={job_run.status}, "
                    f"duration_ms={job_run.duration_ms}"
                )
                last_run_times[job_name] = datetime.now(timezone.utc)
                return
            finally:
                db_session.close()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_seconds = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Job {job_name} attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait_seconds}s..."
                )
                await asyncio.sleep(wait_seconds)
            else:
                logger.error(f"Job {job_name} failed after {max_retries} attempts: {e}")


async def worker_loop() -> None:
    """Main worker loop - run jobs on schedule."""
    logger.info("Background job worker started")
    logger.info(f"Job schedule: {JOB_SCHEDULE}")

    job_functions = {
        "import_games": import_games,
        "sync_scores": sync_scores,
        "lock_picks": lock_picks,
        "send_reminders": send_reminders,
    }

    while True:
        try:
            # Check each job
            for job_name, job_fn in job_functions.items():
                if await should_run_job(job_name):
                    logger.info(f"Running job: {job_name}")
                    await run_job_with_retry(job_name, job_fn)

            # Sleep for 1 minute before checking again
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            await asyncio.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(worker_loop())
