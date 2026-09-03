"""Job runner with PostgreSQL advisory lock for background scheduled jobs.

This module implements a production-grade job runner that uses PostgreSQL advisory
locks to ensure only one instance of each job runs at a time across the entire
distributed system (e.g., all Fly.io worker processes).

Jobs are:
- import_games: Fetch and store upcoming/live NFL games
- sync_scores: Update scores from completed games
- lock_picks: Lock all picks for games that have started
- send_reminders: Send weekly reminder emails to users with incomplete picks
"""

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
    """Import upcoming and live NFL games from external API.

    Fetches current week's schedule from ESPN and stores it in the database.
    Skips if no active league is configured (single-league v1).
    """
    from app.integrations.espn import fetch_schedule
    from app.services import league_service, weeks_service
    from app.services.nfl_schedule_service import import_games as import_games_service

    logger.info("Starting import_games job")

    try:
        league = league_service.get_active_league(db)
        logger.info(f"Active league: {league.name} (season {league.season})")
    except Exception as e:
        logger.info(f"No active league configured: {e}")
        return

    try:
        current_week = weeks_service.get_current_week(db)
        logger.info(f"Current week: {current_week.week_number}")
    except Exception as e:
        logger.error(f"Failed to get current week: {e}")
        return

    try:
        # Fetch this week's schedule from ESPN
        espn_games = fetch_schedule(league.season, current_week.week_number)
        logger.info(f"Fetched {len(espn_games)} games from ESPN")

        # Import into database
        imported = import_games_service(db, espn_games)
        logger.info(f"Successfully imported {imported} games")
    except Exception as e:
        logger.error(f"Failed to import games: {e}", exc_info=True)
        raise


async def sync_scores(db: Session) -> None:
    """Update scores from completed games.

    Fetches current week's game scores from ESPN and updates the database,
    then recomputes all league standings for the week.
    """
    from app.integrations.espn import fetch_schedule
    from app.services import league_service, scoring_service, weeks_service
    from app.services.nfl_schedule_service import import_games as import_games_service

    logger.info("Starting sync_scores job")

    try:
        league = league_service.get_active_league(db)
        logger.info(f"Active league: {league.name} (season {league.season})")
    except Exception as e:
        logger.info(f"No active league configured: {e}")
        return

    try:
        current_week = weeks_service.get_current_week(db)
        logger.info(f"Current week: {current_week.week_number}")
    except Exception as e:
        logger.error(f"Failed to get current week: {e}")
        return

    try:
        # Fetch current scores from ESPN
        espn_games = fetch_schedule(league.season, current_week.week_number)
        logger.info(f"Fetched {len(espn_games)} games from ESPN")

        # Update database with latest scores
        updated = import_games_service(db, espn_games)
        logger.info(f"Updated {updated} games with latest scores")

        # Recompute standings for this week
        final_count = scoring_service.score_week(db, league=league, week_id=current_week.id)
        logger.info(f"Scored week {current_week.week_number}, {final_count} finalized games")

    except Exception as e:
        logger.error(f"Failed to sync scores: {e}", exc_info=True)
        raise


async def lock_picks(db: Session) -> None:
    """Lock picks for games that have started.

    Finds all games with kickoff_time <= now and marks their picks as locked.
    Locks are idempotent - setting locked_at multiple times is safe.
    """
    from datetime import timezone

    from sqlalchemy import select, update

    logger.info("Starting lock_picks job")

    try:
        from app.models.nfl_game import NflGame
        from app.models.pick import Pick

        now = datetime.now(timezone.utc)

        # Find all games that have started
        started_games = (
            db.execute(select(NflGame).where(NflGame.kickoff_time <= now)).scalars().all()
        )

        if not started_games:
            logger.info("No games have started yet")
            return

        logger.info(f"Found {len(started_games)} games that have started")

        # Lock all picks for these games (set locked_at if not already set)
        game_ids = [game.id for game in started_games]
        stmt = (
            update(Pick)
            .where(
                Pick.game_id.in_(game_ids),
                Pick.locked_at.is_(None),  # Only lock if not already locked
            )
            .values(locked_at=now)
        )
        result = db.execute(stmt)
        db.commit()

        locked_count = result.rowcount
        logger.info(f"Locked {locked_count} picks")

    except Exception as e:
        logger.error(f"Failed to lock picks: {e}", exc_info=True)
        raise


async def send_reminders(db: Session) -> None:
    """Send weekly reminder emails for incomplete picks.

    Sends reminders to league members who have not submitted all their picks
    for the current week. Only sends during the week (not after all games complete).
    """
    from sqlalchemy import func, select

    logger.info("Starting send_reminders job")

    try:
        from app.models.league_member import LeagueMember
        from app.models.nfl_game import NflGame
        from app.models.pick import Pick
        from app.services import email_service, league_service, weeks_service

        league = league_service.get_active_league(db)
        logger.info(f"Active league: {league.name}")

    except Exception as e:
        logger.info(f"No active league configured: {e}")
        return

    try:
        current_week = weeks_service.get_current_week(db)
        logger.info(f"Current week: {current_week.week_number}")
    except Exception as e:
        logger.error(f"Failed to get current week: {e}")
        return

    try:
        # Get all league members
        members = (
            db.execute(select(LeagueMember).where(LeagueMember.league_id == league.id))
            .scalars()
            .all()
        )

        # Count total games in the week
        total_games = (
            db.execute(
                select(func.count(NflGame.id)).where(NflGame.week_id == current_week.id)
            ).scalar()
            or 0
        )

        logger.info(f"Week has {total_games} games, {len(members)} league members")

        sent_count = 0
        for member in members:
            # Count submitted picks for this member
            submitted_picks = (
                db.execute(
                    select(func.count(Pick.id))
                    .join(NflGame, Pick.game_id == NflGame.id)
                    .where(NflGame.week_id == current_week.id, Pick.user_id == member.user_id)
                ).scalar()
                or 0
            )

            remaining_picks = total_games - submitted_picks

            if remaining_picks > 0:
                # Send reminder email
                try:
                    deadline = current_week.start_date.strftime("%I:%M %p ET")
                    from app.core.config import get_settings

                    picks_link = f"{get_settings().app_url}/#/picks"

                    email_service.send_weekly_reminder(
                        to=member.user.email,
                        season=league.season,
                        week_number=current_week.week_number,
                        remaining_picks=remaining_picks,
                        deadline=deadline,
                        picks_link=picks_link,
                    )
                    sent_count += 1
                    logger.info(
                        f"Sent reminder to {member.user.email}: {remaining_picks} picks remaining"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send reminder to {member.user.email}: {e}", exc_info=True
                    )

        logger.info(f"Sent {sent_count} weekly reminders")

    except Exception as e:
        logger.error(f"Failed to send reminders: {e}", exc_info=True)
        raise
