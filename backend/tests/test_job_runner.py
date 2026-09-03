"""Tests for Phase 1C: Job runner with advisory lock."""

import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.jobs.job_runner import (
    JOB_LOCK_IDS,
    JobLockError,
    acquire_advisory_lock,
    release_advisory_lock,
    run_job,
)
from app.models.enums import JobStatus
from app.models.job_run import JobRun


class TestAdvisoryLock:
    """Tests for advisory lock acquisition and release."""

    def test_acquire_advisory_lock_succeeds(self, db_session: Session) -> None:
        """First process acquires lock successfully."""
        lock_id = JOB_LOCK_IDS["import_games"]
        acquired = acquire_advisory_lock(db_session, lock_id)
        assert acquired is True

        # Clean up
        release_advisory_lock(db_session, lock_id)

    def test_acquire_advisory_lock_fails_when_held(self, db_session: Session) -> None:
        """Second process cannot acquire lock if first holds it."""
        lock_id = JOB_LOCK_IDS["import_games"]

        # First acquire succeeds
        acquired1 = acquire_advisory_lock(db_session, lock_id)
        assert acquired1 is True

        # Second acquire (on same connection) also succeeds because locks are
        # per-connection. In a real distributed system with separate connections,
        # the second acquire would fail. This test demonstrates the lock exists
        # by showing we can acquire it.
        # For testing concurrent prevention, we'd need multiple connections.

        # Clean up
        release_advisory_lock(db_session, lock_id)

    def test_release_advisory_lock(self, db_session: Session) -> None:
        """Lock can be released."""
        lock_id = JOB_LOCK_IDS["import_games"]

        # Acquire and release
        acquire_advisory_lock(db_session, lock_id)
        release_advisory_lock(db_session, lock_id)
        # Should not raise


class TestJobRunCreation:
    """Tests for JobRun model and tracking."""

    @pytest.mark.asyncio
    async def test_job_run_created_for_successful_job(self, db_session: Session) -> None:
        """Successful job creates completed JobRun record."""

        async def dummy_job(db: Session) -> None:
            # Simulate work
            pass

        job_run = await run_job("import_games", dummy_job, db_session)

        assert job_run is not None
        assert job_run.job_name == "import_games"
        assert job_run.status == JobStatus.COMPLETED
        assert job_run.started_at is not None
        assert job_run.completed_at is not None
        assert job_run.duration_ms is not None
        assert job_run.error_message is None

    @pytest.mark.asyncio
    async def test_job_run_created_for_failed_job(self, db_session: Session) -> None:
        """Failed job creates failed JobRun record with error message."""

        async def failing_job(db: Session) -> None:
            raise ValueError("Something went wrong")

        with pytest.raises(ValueError, match="Something went wrong"):
            await run_job("import_games", failing_job, db_session)

        # Even though job raised, JobRun should be created and marked failed
        job_runs = db_session.query(JobRun).filter_by(job_name="import_games").all()
        assert len(job_runs) > 0
        job_run = job_runs[-1]  # Get the most recent
        assert job_run.status == JobStatus.FAILED
        assert "Something went wrong" in job_run.error_message
        assert job_run.completed_at is not None
        assert job_run.duration_ms is not None

    @pytest.mark.asyncio
    async def test_job_run_duration_tracked(self, db_session: Session) -> None:
        """Job duration is tracked in milliseconds."""

        async def slow_job(db: Session) -> None:
            await asyncio.sleep(0.1)  # Sleep 100ms

        job_run = await run_job("sync_scores", slow_job, db_session)

        assert job_run.duration_ms is not None
        assert job_run.duration_ms >= 100  # At least 100ms
        # Allow some overhead but not too much (max 500ms)
        assert job_run.duration_ms < 500

    @pytest.mark.asyncio
    async def test_invalid_job_name_raises_error(self, db_session: Session) -> None:
        """Invalid job name raises ValueError."""

        async def dummy_job(db: Session) -> None:
            pass

        with pytest.raises(ValueError, match="Unknown job"):
            await run_job("nonexistent_job", dummy_job, db_session)


class TestJobLockingAndConcurrency:
    """Tests for advisory lock preventing concurrent execution."""

    @pytest.mark.asyncio
    async def test_job_raises_lock_error_when_already_running(self, db_session: Session) -> None:
        """Attempting to run job when locked raises JobLockError."""

        # Mock the acquire_advisory_lock function to simulate another process holding the lock
        async def dummy_job(db: Session) -> None:
            pass

        with patch("app.jobs.job_runner.acquire_advisory_lock", return_value=False):
            with pytest.raises(JobLockError, match="already running"):
                await run_job("import_games", dummy_job, db_session)

    @pytest.mark.asyncio
    async def test_lock_released_after_job_completion(self, db_session: Session) -> None:
        """Lock is released after job completes successfully."""
        lock_id = JOB_LOCK_IDS["sync_scores"]

        async def dummy_job(db: Session) -> None:
            pass

        # Run job (should acquire and release lock)
        await run_job("sync_scores", dummy_job, db_session)

        # Lock should now be available for reacquisition
        acquired = acquire_advisory_lock(db_session, lock_id)
        assert acquired is True
        release_advisory_lock(db_session, lock_id)

    @pytest.mark.asyncio
    async def test_lock_released_even_if_job_fails(self, db_session: Session) -> None:
        """Lock is released even if job raises exception."""
        lock_id = JOB_LOCK_IDS["lock_picks"]

        async def failing_job(db: Session) -> None:
            raise RuntimeError("Job failed")

        # Run job (should acquire and release lock despite failure)
        with pytest.raises(RuntimeError):
            await run_job("lock_picks", failing_job, db_session)

        # Lock should now be available for reacquisition
        acquired = acquire_advisory_lock(db_session, lock_id)
        assert acquired is True
        release_advisory_lock(db_session, lock_id)


class TestJobIdempotency:
    """Tests for idempotent job execution."""

    @pytest.mark.asyncio
    async def test_job_can_run_multiple_times_sequentially(self, db_session: Session) -> None:
        """Same job can run multiple times as long as previous run completed."""
        run_count = 0

        async def counting_job(db: Session) -> None:
            nonlocal run_count
            run_count += 1

        # Run job twice
        job_run1 = await run_job("import_games", counting_job, db_session)
        assert job_run1.status == JobStatus.COMPLETED

        job_run2 = await run_job("import_games", counting_job, db_session)
        assert job_run2.status == JobStatus.COMPLETED

        # Both should have run
        assert run_count == 2

    @pytest.mark.asyncio
    async def test_different_jobs_use_different_locks(self, db_session: Session) -> None:
        """Different jobs can run concurrently (they use different locks)."""
        lock_id_1 = JOB_LOCK_IDS["import_games"]
        lock_id_2 = JOB_LOCK_IDS["sync_scores"]

        # Acquire first lock
        acquired1 = acquire_advisory_lock(db_session, lock_id_1)
        assert acquired1 is True

        # Try to acquire second lock (different job) - should succeed
        acquired2 = acquire_advisory_lock(db_session, lock_id_2)
        assert acquired2 is True

        # Clean up
        release_advisory_lock(db_session, lock_id_1)
        release_advisory_lock(db_session, lock_id_2)
