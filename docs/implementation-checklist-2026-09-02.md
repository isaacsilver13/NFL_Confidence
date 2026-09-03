# Implementation Checklist

> Historical checklist. The completed implementation and current deployment
> gate are summarized in [release-readiness.md](release-readiness.md).


## Phase 1: Critical Blockers (Est. 1.5 hours)

### ✅ Blocker #1: Activate Production Job Runner

**Step 1.1: Enable Scheduler in fly.toml**
- [ ] Edit `backend/fly.toml` line 24
- [ ] Change `ENABLE_SCHEDULER = "false"` → `ENABLE_SCHEDULER = "true"`
- [ ] Verify no other instances in file
- [ ] Test locally with `ENABLE_SCHEDULER=true`

**Step 1.2: Deploy to Production**
- [ ] Run `fly deploy --app nfl-confidence-api`
- [ ] Wait for deployment to complete
- [ ] Check Fly dashboard for app status
- [ ] View app logs: `fly logs --app nfl-confidence-api`

**Step 1.3: Verify Scheduler Started**
- [ ] Check logs contain "APScheduler started" or similar
- [ ] Confirm no scheduler errors in logs
- [ ] Run `fly status --app nfl-confidence-api` (should show healthy)

**Step 1.4: Monitor First Job Execution**
- [ ] Wait for first scheduled job (check times in scheduler.py)
- [ ] Verify job log entry appears
- [ ] Check database: `nfl_games.last_synced` should be recent
- [ ] Confirm WeeklyResult records exist (no duplicates)

---

### ✅ Blocker #2: Fix Silent Exception in Session Bootstrap

**Step 2.1: Update Backend Error Handling**
- [ ] Open `backend/app/api/session.py`
- [ ] Locate lines 37-40 (bare `except Exception:`)
- [ ] Add logging: `logger.exception("Bootstrap endpoint failed", exc_info=e)`
- [ ] Change `pass` to `raise` (re-raise exception)
- [ ] Add import: `import logging` at top
- [ ] Create logger: `logger = logging.getLogger(__name__)`

**Step 2.2: Add Success Logging**
- [ ] Add log statement after successful league/week fetch
- [ ] Example: `logger.info("Bootstrap complete", extra={"user_id": user.id})`

**Step 2.3: Update Frontend Error Display**
- [ ] Open `frontend/src/features/auth/AuthContext.tsx`
- [ ] Check how bootstrap errors are handled
- [ ] Add user-visible error message if bootstrap returns 500
- [ ] Test: Temporarily break backend, verify frontend shows error

**Step 2.4: Test Error Path**
- [ ] Stop database connection to trigger error
- [ ] Verify 500 status returned (not silently returning null)
- [ ] Confirm error logged with stack trace
- [ ] Check frontend displays error gracefully

**Step 2.5: Add Monitoring**
- [ ] Configure error tracking (e.g., Sentry, or just log alerts)
- [ ] Set alert: Bootstrap endpoint 500 errors > threshold

---

### ✅ Blocker #3: Align Backend on All-Picks Locking

**Step 3.1: Update Pick Validation Logic**
- [ ] Open `backend/app/services/picks_service.py`
- [ ] Find `create_picks()` function around line 68
- [ ] Locate the per-game validation loop (lines 115+)
- [ ] Replace with:
  ```python
  # Check week-level lock: ALL picks lock when earliest game kicks off
  earliest_kickoff = min((g.kickoff_time for g in games), default=None)
  if earliest_kickoff and earliest_kickoff <= now:
      raise ValidationError("Picks are locked. The earliest game has already started.")
  ```
- [ ] Remove individual game kickoff checks
- [ ] Update error message to reference week lock

**Step 3.2: Verify Week Read Response**
- [ ] Open `backend/app/api/weeks.py` 
- [ ] Check `_week_read()` function
- [ ] Confirm `locks_at` is the earliest game time ✓
- [ ] Confirm `is_locked` checks against earliest game ✓

**Step 3.3: Update Test Suite**
- [ ] Open `backend/tests/test_picks_per_game_locking.py`
- [ ] Find test cases that expect per-game locking
- [ ] Update to expect week-level locking instead
- [ ] Rename tests: `test_per_game_locking` → `test_week_level_locking`
- [ ] Example new test:
  ```python
  def test_no_picks_after_earliest_game():
      # Thursday 8:20 PM game
      # Try submit at 8:21 PM
      # Should fail: earliest game already started
  ```

**Step 3.4: Verify Frontend Alignment**
- [ ] Open `frontend/src/pages/PicksPage.tsx` line 59
- [ ] Confirm frontend already implements week-level lock ✓
- [ ] No frontend changes needed (already correct)

**Step 3.5: Test End-to-End**
- [ ] Manually submit picks before first kickoff ✓
- [ ] Try to submit picks after first kickoff ✗ (should fail)
- [ ] Confirm error message: "Picks are locked"
- [ ] Run full test suite

---

## Phase 2: High-Priority Bugs (Est. 2 hours)

### ✅ Bug #1: Fix N+1 Query in GET /weeks

**Step 1.1: Update Repository**
- [ ] Open `backend/app/repositories/nfl_week_repository.py`
- [ ] Add import: `from sqlalchemy.orm import selectinload`
- [ ] Find `list_by_season()` function
- [ ] Add `.options(selectinload(NflWeek.games))` to query
- [ ] Full implementation:
  ```python
  from sqlalchemy import select
  from sqlalchemy.orm import Session, selectinload
  
  def list_by_season(db: Session, *, season: int) -> list[NflWeek]:
      return list(
          db.execute(
              select(NflWeek)
              .where(NflWeek.season == season)
              .options(selectinload(NflWeek.games))
              .order_by(NflWeek.week_number)
          ).scalars()
      )
  ```

**Step 1.2: Verify Usage**
- [ ] Check `backend/app/services/weeks_service.py`
- [ ] Confirm it calls `nfl_week_repository.list_by_season()`
- [ ] If calling elsewhere, update those too

**Step 1.3: Test Query Plan**
- [ ] Enable SQL logging: `export SQLALCHEMY_ECHO=true`
- [ ] Run: `curl http://localhost:8000/api/v1/weeks`
- [ ] Verify: Exactly 1 SQL query (SELECT ... JOIN games) not 19
- [ ] Disable logging after testing

**Step 1.4: Measure Performance**
- [ ] Time before: `GET /weeks` latency
- [ ] Time after: should be 5-10x faster
- [ ] Run test suite: no N+1 warnings

---

### ✅ Bug #2: Fix N+1 Query in lock_expired_picks()

**Step 2.1: Update Job Function**
- [ ] Open `backend/app/jobs/nfl_schedule.py`
- [ ] Find `lock_expired_picks()` around line 80
- [ ] Locate line 86: `games = nfl_game_repository.get_by_week_id(db, week.id)`
- [ ] Replace with eager-loading version:
  ```python
  from sqlalchemy import select
  from sqlalchemy.orm import selectinload
  
  games = list(
      db.execute(
          select(NflGame)
          .where(NflGame.week_id == week.id)
          .options(selectinload(NflGame.picks))
      ).scalars()
  )
  ```

**Step 2.2: Test Query Plan**
- [ ] Enable SQL logging
- [ ] Call `lock_expired_picks()` manually
- [ ] Verify: 1 query instead of 18
- [ ] Disable logging

**Step 2.3: Performance Validation**
- [ ] Measure job execution time before/after
- [ ] Target: < 500ms (was ~50ms)
- [ ] Run weekly - monitor job logs

---

### ✅ Bug #3: Configure Database Connection Pool

**Step 3.1: Update session.py**
- [ ] Open `backend/app/db/session.py`
- [ ] Find `create_engine()` call
- [ ] Replace single parameter with full config:
  ```python
  engine = create_engine(
      settings.database_url,
      pool_size=10,
      max_overflow=5,
      pool_pre_ping=True,
      pool_recycle=3600,
  )
  ```

**Step 3.2: Add Documentation**
- [ ] Add comment explaining pool sizing rationale
- [ ] Document: pool_size, max_overflow, pool_pre_ping, pool_recycle

**Step 3.3: Test Connection Pool**
- [ ] Start backend locally
- [ ] Run concurrent load test (20+ simultaneous requests)
- [ ] Monitor: No "too many connections" errors
- [ ] Verify: Requests complete without hanging

**Step 3.4: Production Verification**
- [ ] Deploy to production
- [ ] Monitor Fly database metrics
- [ ] Check pool utilization stays < 80%

---

### ✅ Bug #4: Improve Scheduled Job Logging

**Step 4.1: Create JobExecution Model**
- [ ] Create `backend/app/models/job_execution.py`:
  ```python
  import uuid
  from datetime import datetime
  from sqlalchemy import DateTime, String, Integer, Uuid, func
  from sqlalchemy.orm import Mapped, mapped_column
  from app.db.session import Base
  
  class JobExecution(Base):
      __tablename__ = "job_executions"
      
      id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
      job_name: Mapped[str]
      started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
      completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
      status: Mapped[str]  # "running", "success", "failed"
      result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
      error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
      created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
  ```

**Step 4.2: Create Database Migration**
- [ ] Generate migration: `alembic revision --autogenerate -m "Add job_executions table"`
- [ ] Verify migration file in `backend/alembic/versions/`
- [ ] Run migration: `alembic upgrade head`

**Step 4.3: Update Scheduler Logging**
- [ ] Open `backend/app/jobs/scheduler.py`
- [ ] Replace `_run_logged()` with enhanced version:
  ```python
  import logging
  import time
  from app.models.job_execution import JobExecution
  from app.db.session import SessionLocal
  
  logger = logging.getLogger(__name__)
  
  def _run_logged(job_name: str, job) -> None:
      start = time.time()
      logger.info(f"Job starting", extra={"job_name": job_name})
      
      with SessionLocal() as db:
          execution = JobExecution(
              job_name=job_name,
              started_at=datetime.now(timezone.utc),
              status="running"
          )
          db.add(execution)
          db.commit()
          
          try:
              result = job()
              elapsed = time.time() - start
              execution.status = "success"
              execution.completed_at = datetime.now(timezone.utc)
              execution.result_count = result if isinstance(result, int) else None
              logger.info(
                  f"Job completed",
                  extra={
                      "job_name": job_name,
                      "elapsed_seconds": f"{elapsed:.2f}",
                      "result": result
                  }
              )
          except Exception as e:
              elapsed = time.time() - start
              execution.status = "failed"
              execution.error_message = str(e)
              logger.exception(
                  f"Job failed",
                  extra={
                      "job_name": job_name,
                      "elapsed_seconds": f"{elapsed:.2f}"
                  },
                  exc_info=e
              )
          finally:
              db.commit()
  ```

**Step 4.4: Create Health Status Endpoint**
- [ ] Open or create `backend/app/api/health.py`
- [ ] Add endpoint:
  ```python
  from fastapi import APIRouter
  from sqlalchemy.orm import Session
  from app.db.session import get_db
  from app.models.job_execution import JobExecution
  from sqlalchemy import select, func, desc
  
  router = APIRouter(prefix="/health", tags=["health"])
  
  @router.get("/jobs")
  def job_status(db: Session = Depends(get_db)) -> dict:
      job_names = ["import_games", "score_week", "lock_picks", "send_reminders"]
      status = {}
      
      for job_name in job_names:
          # Get most recent execution
          latest = db.execute(
              select(JobExecution)
              .where(JobExecution.job_name == job_name)
              .order_by(desc(JobExecution.started_at))
              .limit(1)
          ).scalar_one_or_none()
          
          if latest:
              age_minutes = (datetime.now(timezone.utc) - latest.started_at).total_seconds() / 60
              status[job_name] = {
                  "last_run": latest.started_at.isoformat(),
                  "status": latest.status,
                  "result_count": latest.result_count,
                  "age_minutes": round(age_minutes, 1),
                  "error": latest.error_message
              }
          else:
              status[job_name] = {"status": "never_run"}
      
      return status
  ```

**Step 4.5: Test Job Logging**
- [ ] Deploy backend with changes
- [ ] Wait for next scheduled job
- [ ] Verify: JobExecution record created in database
- [ ] Call `GET /api/v1/health/jobs` → returns job status
- [ ] Trigger job failure (e.g., disconnect database)
- [ ] Verify: Error logged and stored in database

---

## Pre-Deployment Testing

### Unit Tests
- [ ] Run backend tests: `pytest backend/tests/`
- [ ] Run frontend tests: `npm test`
- [ ] Target: All tests passing

### Integration Tests
- [ ] Create or enable E2E test for pick submission
- [ ] Test: Submit before lock ✓
- [ ] Test: Submit after lock ✗
- [ ] Test: Query plan for /weeks (1 query)
- [ ] Test: Job execution logging

### Manual Testing
- [ ] Test pick submission flow (picks page)
- [ ] Test week listing (standings page if exists)
- [ ] Test bootstrap endpoint
- [ ] Monitor job execution in logs
- [ ] Trigger error conditions (database down, missing config)

---

## Deployment Sequence

1. **Database Migrations** (if any)
   - [ ] Run migrations in staging
   - [ ] Verify job_executions table created
   - [ ] Backup production database before applying

2. **Backend Deployment**
   - [ ] Deploy code to production
   - [ ] Monitor app logs for startup errors
   - [ ] Verify `/api/v1/health/ready` returns 200

3. **Frontend Deployment** (if UI changes)
   - [ ] Build and deploy frontend
   - [ ] Clear browser cache / hard refresh

4. **Scheduler Activation**
   - [ ] Enable scheduler: `ENABLE_SCHEDULER=true`
   - [ ] Deploy again
   - [ ] Monitor logs for APScheduler startup

5. **Post-Deployment Verification**
   - [ ] Check first scheduled job execution
   - [ ] Verify nfl_games.last_synced updated
   - [ ] Check job_executions table has records
   - [ ] Call `/api/v1/health/jobs` → see recent execution
   - [ ] Monitor error rate on bootstrap endpoint
   - [ ] Verify pick locking works correctly

---

## Success Criteria

| Criterion | How to Verify |
|-----------|---------------|
| **Scheduler running** | Job logs appear, database updated |
| **Errors logged** | Check app logs, no silent exceptions |
| **Picks locked at week level** | Submit before kickoff ✓, after ✗ |
| **No N+1 queries** | Enable query logging, count queries |
| **Pool configured** | Load test 20 concurrent users, no hangs |
| **Jobs monitored** | `/health/jobs` shows recent execution |

---

## Rollback Plan

If issues occur after deployment:

1. **Disable scheduler:** Set `ENABLE_SCHEDULER=false` → redeploy
2. **Revert backend:** Redeploy previous version
3. **Check database:** Verify no corrupted data
4. **Notify users:** If service was down > 5 minutes

**Contacts:**
- Database: CloudSQL dashboard
- Deployment: Fly.io dashboard
- Monitoring: [Your alert system]

---

## Time Estimates

| Phase | Items | Est. Time |
|-------|-------|-----------|
| **Blocker #1** | Enable scheduler, verify | 30m |
| **Blocker #2** | Fix errors, test frontend | 20m |
| **Blocker #3** | Update validation, tests | 45m |
| **Bug #1** | Fix N+1 in weeks | 30m |
| **Bug #2** | Fix N+1 in lock_picks | 30m |
| **Bug #3** | Configure pool | 15m |
| **Bug #4** | Job logging + model | 20m |
| **Testing & Deploy** | E2E tests, production deploy | 30m |
| **TOTAL** | | **~3.5 hours** |

---

## Notes

- Start with Phase 1 blockers; they're shorter and unblock everything else
- Test each blocker locally before deploying to production
- Phase 2 bugs can be deployed together (no dependencies)
- Monitor production for 24 hours after deployment
- Keep previous version available for quick rollback

