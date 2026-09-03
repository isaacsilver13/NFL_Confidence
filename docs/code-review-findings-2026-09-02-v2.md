# NFL Confidence Pool - Code Review Findings

> Historical review. This file records the issues that drove the implementation
> work; see [release-readiness.md](release-readiness.md) for current status.

**Date:** 2026-09-02  
**Review Type:** Static + Runtime Path Analysis  
**Scope:** Backend/Frontend Implementation Review

---

## Executive Summary

The application has a solid architectural foundation with most critical security issues already addressed from the previous review. However, three blocking issues remain that prevent production deployment:

1. **Production job runner still disabled** — scheduled jobs don't run in production
2. **Silent exception handling in session bootstrap** — errors are hidden from monitoring
3. **Frontend/backend mismatch on per-game locking** — UX contradicts backend logic

Additionally, several N+1 query patterns exist that will cause performance degradation as the league grows. Database connection pooling is not configured for production concurrency.

---

## Issues by Priority

### 🔴 CRITICAL BLOCKERS

#### 1. Production Job Runner Disabled (Blocks Release)
**File:** `backend/fly.toml`  
**Status:** Not Fixed  
**Impact:** Application is non-functional in production

```toml
# Line 24 - PRODUCTION BLOCKER
ENABLE_SCHEDULER = "false"
```

**Problem:**
- `ENABLE_SCHEDULER = "false"` prevents APScheduler from starting in production
- Worker process is defined (`[[processes]] type = "worker"`) but deployment strategy is unclear
- No Fly cron configuration exists
- Consequence: No games imported, no picks locked, no scores calculated, no reminders sent

**Current State:**
- FastAPI lifespan checks this setting in `backend/app/main.py`
- If false, scheduler is not created/started
- Worker process code exists in `backend/app/jobs/worker.py` but unclear if it's deployed

**Required Fix:**
Either:
1. Set `ENABLE_SCHEDULER = "true"` in production (only if single-instance deployment)
2. Enable and verify worker process is deployed as separate Fly machine

**Verification Needed:**
After fix, confirm:
- `nfl_games.last_synced` is updated every 30 minutes
- `weekly_results` records exist for all members each week
- No duplicate results (unique constraint prevents)

---

#### 2. Silent Exception Catch in Session Bootstrap (Debugging Blocker)
**File:** `backend/app/api/session.py`, lines 38-39  
**Status:** Not Fixed  
**Impact:** Production errors hidden from monitoring/alerting

```python
try:
    league = league_service.get_active_league(db)
    # ... fetches league, week data ...
except Exception:  # <-- BLOCKER: Silently hides ALL errors
    # If any error fetching league data, just return user data
    pass
```

**Problem:**
- Any error (database, auth, validation) is caught and silently ignored
- Returns partial/empty response without indication of failure
- Makes production debugging impossible
- No logging, no metrics, no alert capability

**Examples of Hidden Errors:**
- Database connection pool exhaustion
- Missing JWT secret configuration
- Active league lookup failure
- Week calculation errors
- Authorization failures

**Required Fix:**
```python
try:
    league = league_service.get_active_league(db)
    # ...
except Exception as e:
    logger.exception("Failed to load league data in bootstrap", exc_info=e)
    # Return partial data with error flag or re-raise for proper error response
    pass
```

**Verification:**
- Check application logs in production
- Verify error responses are properly formatted (5xx status)
- Add alerting on bootstrap endpoint error rate

---

#### 3. Frontend/Backend Mismatch on Per-Game Pick Locking
**Files:**
- `frontend/src/pages/PicksPage.tsx`, line 59
- `backend/app/services/picks_service.py`, line 115+

**Status:** Partially Fixed  
**Impact:** Users can't submit valid picks through UI; confusing UX

**Problem:**
Frontend disables all pick buttons when week-level lock triggers:
```typescript
// PicksPage.tsx line 59
const isLocked = Boolean(week.isLocked || (locksAt !== null && locksAt <= now))

// Line 216 - disables ALL buttons when locked
disabled={isLocked}  // <-- Disables Sunday/Monday picks after Thursday
```

Backend correctly validates per-game:
```python
# picks_service.py line 115+
for submission in submissions:
    game = game_by_id.get(submission.game_id)
    if game.kickoff_time <= now:  # <-- Per-game check
        raise ValidationError(f"Cannot edit {game.away_team} at {game.home_team}")
```

**Consequences:**
- Thursday game at 8:20 PM locks the week
- User can't submit picks for Sunday 1 PM games (still 68 hours away)
- UI blocks submission even though backend would accept it
- Frustrating user experience defeats the product's per-game design

**Required Fix:**

1. Backend: Add per-game deadline to game response
   ```python
   # In game serialization
   class GameRead:
       id: UUID
       locked_at: datetime | None  # When this specific game locked
       is_locked: bool  # game.kickoff_time <= now
   ```

2. Frontend: Check per-game status
   ```typescript
   // Show each game's lock status individually
   const isGameLocked = game.isLocked || game.lockedAt <= now
   
   {games.map((game) => (
     <button disabled={isGameLocked}>  // Per-game disable
   ```

3. Update UI to show which games are locked
   ```typescript
   {isGameLocked && <span>Locked</span>}
   {!isGameLocked && <span>Locks {formatTime(game.lockedAt)}</span>}
   ```

**Verification:**
- Thursday game locks at 8:20 PM
- User can still submit Sunday/Monday picks after Thursday
- UI correctly shows locked/unlocked status per game
- Validation errors match UI state

---

### 🟠 HIGH-PRIORITY BUGS

#### 1. N+1 Query in `GET /weeks` Endpoint
**File:** `backend/app/api/weeks.py`, lines 21-23  
**Status:** Not Fixed  
**Severity:** High (blocks season-view feature)

**Problem:**
```python
def _week_read(week) -> dict:
    # Line 21: Accessing week.games triggers a lazy load for EVERY week
    locks_at = min((game.kickoff_time for game in week.games), default=None)
```

When `get_weeks()` returns all 18 weeks:
- Query 1: `SELECT * FROM nfl_weeks`
- Queries 2-19: `SELECT * FROM nfl_games WHERE week_id = $1` (one per week)
- **Total: 19 queries instead of 1**

**Impact:**
- Season standings page loads 18x slower than necessary
- Database connection pool exhaustion under concurrent users
- Latency: ~500ms becomes ~2000ms for this endpoint

**Test Case:**
```
Before: GET /weeks takes 500ms
After fix: Should take 50ms
```

**Required Fix:**
Use `selectinload` to fetch all games in one query:

```python
# In nfl_week_repository.py or weeks_service.py
def list_all_weeks(db: Session) -> list[NflWeek]:
    return list(
        db.execute(
            select(NflWeek)
            .options(selectinload(NflWeek.games))
            .order_by(NflWeek.week_number)
        ).scalars()
    )
```

**Verification:**
- Run with query logging enabled
- Confirm single query with JOIN to games
- Measure latency improvement

---

#### 2. N+1 Query in `lock_expired_picks()` Job
**File:** `backend/app/jobs/nfl_schedule.py`, lines 90-96  
**Status:** Not Fixed  
**Severity:** High (performance degradation over season)

**Problem:**
```python
for game in games:  # Loaded in one query
    for pick in game.picks:  # <-- Lazy load: N queries for N games
        if pick.locked_at is None:
            pick.locked_at = deadline
            locked += 1
```

With 17 games per week:
- Query 1: `SELECT * FROM nfl_games WHERE week_id = $1`
- Queries 2-18: `SELECT * FROM picks WHERE game_id = $1` (one per game)
- **Total: 18 queries**

**Impact:**
- Job runs every 5 minutes
- 18 queries × 288 runs/day = 5,184 unnecessary queries/day
- Database load, connection pool exhaustion
- Job latency: 5ms becomes 50+ms

**Required Fix:**
Eager load picks with games:

```python
def lock_expired_picks() -> int:
    with SessionLocal() as db:
        league = league_repository.get_active(db)
        if league is None:
            return 0
        week = weeks_service.get_current_week(db)
        
        # Fix: Eager load picks with games
        games = list(
            db.execute(
                select(NflGame)
                .where(NflGame.week_id == week.id)
                .options(selectinload(NflGame.picks))
            ).scalars()
        )
        
        if not games:
            return 0
        # ... rest of function
```

---

#### 3. N+1 Query in Leaderboard Calculations (Potential)
**File:** `backend/app/repositories/weekly_result_repository.py`, `season_result_repository.py`  
**Status:** Needs Verification  
**Severity:** Medium

**Potential Issue:**
If any leaderboard query doesn't eagerly load the `user` relationship, accessing `result.user.display_name` will trigger lazy loads.

**Current State (from grep):**
```python
# Line 18 in weekly_result_repository.py
.options(joinedload(WeeklyResult.user))
```

✓ Appears to be using joinedload, so likely not an issue. **Verify in live queries.**

---

#### 4. Database Connection Pool Not Configured for Production
**File:** `backend/app/db/session.py`  
**Status:** Not Fixed  
**Severity:** High (production outage risk)

**Problem:**
```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
```

- Default SQLAlchemy pool size: 5 connections
- Fly.io backend max: 1 CPU, 512MB RAM
- Under load: Connection pool exhaustion → 503 errors

**Impact:**
- With 5 concurrent requests, 6th request waits or fails
- Scheduled jobs + API requests compete for same pool
- Concurrent score_week() jobs will hang

**Required Fix:**
```python
engine = create_engine(
    settings.database_url,
    pool_size=10,           # Increase for concurrent requests
    max_overflow=5,         # Allow brief overflow
    pool_pre_ping=True,     # Check connections before reuse
    pool_recycle=3600,      # Recycle connections after 1 hour
)
```

**Verification:**
- Load test with 20+ concurrent requests
- Monitor connection pool in CloudSQL
- Confirm no "too many connections" errors

---

### 🟡 MEDIUM-PRIORITY ISSUES

#### 1. Missing Error Context in Scheduled Job Logging
**File:** `backend/app/jobs/scheduler.py`, line 13  
**Status:** Not Fixed  
**Severity:** Medium (operational difficulty)

**Problem:**
```python
def _run_logged(job_name: str, job) -> None:
    try:
        job()
    except Exception:
        logger.exception("Scheduled job failed job=%s", job_name)
        # Only logs job name, not what failed or why
```

**Issues:**
- No context about what operation failed (import? scoring? locking?)
- No parameters logged (season, week, league)
- No indication of retry state
- Difficult to diagnose in production logs

**Required Fix:**
```python
def _run_logged(job_name: str, job, **context) -> None:
    try:
        logger.info(f"Job starting job={job_name}", extra=context)
        result = job()
        logger.info(
            f"Job completed job={job_name} result={result}",
            extra=context
        )
    except Exception as e:
        logger.exception(
            f"Job failed job={job_name}",
            exc_info=e,
            extra=context
        )
        # Optional: send alert/metric
```

**Verification:**
- Review production logs after fix
- Confirm job context is visible
- Add alerting on job failures

---

#### 2. Missing Health Check for Scheduled Jobs
**File:** Various  
**Status:** Not Implemented  
**Severity:** Medium (operational blind spot)

**Problem:**
- No way to verify if scheduled jobs are running in production
- No metric for job success/failure rate
- No alert if job runner dies

**Required Implementation:**
1. Add `last_run` and `last_success` timestamps to a metadata table
2. Expose `/api/v1/health/jobs` endpoint
3. Return status of each job: last run, success/failure, age

```python
@router.get("/health/jobs")
def job_status(db: Session = Depends(get_db)) -> dict:
    return {
        "import_games": {
            "last_run": datetime,
            "status": "success" | "failed",
            "age_minutes": int
        },
        "score_week": {...},
        "lock_picks": {...},
    }
```

4. Monitor from Fly.io dashboard or external tool

---

#### 3. Missing Batch Operations for Performance
**File:** `backend/app/jobs/nfl_schedule.py`  
**Status:** Not Implemented  
**Severity:** Medium (will become critical as pool grows)

**Problem:**
`lock_expired_picks()` updates picks one by one:
```python
for game in games:
    for pick in game.picks:
        if pick.locked_at is None:
            pick.locked_at = deadline
            locked += 1
db.commit()  # One commit for all
```

With 20 members × 17 games = 340 picks:
- 340 individual object updates in memory
- Inefficient ORM overhead

**Impact:** Grows linearly with pool size

**Required Fix:**
Use bulk update:
```python
db.execute(
    update(Pick)
    .where(
        (Pick.game_id.in_(game_ids)) &
        (Pick.locked_at.is_(None))
    )
    .values(locked_at=deadline)
)
```

---

#### 4. Weak Error Handling in League Bootstrap
**File:** `backend/app/api/session.py`, line 37-40  
**Status:** Not Fixed  
**Severity:** Medium

**Current Behavior:**
- Any error loading league/week data returns `{"league": null, "currentWeek": null}`
- Frontend can't distinguish between "no league exists" vs "server error"
- Users see blank dashboard without understanding why

**Required Fix:**
Either:
1. Re-raise exception with proper HTTP status (recommended)
2. Return error indicator: `{"league": null, "error": "database_unavailable"}`

```python
try:
    league = league_service.get_active_league(db)
    # ...
except Exception as e:
    logger.exception("Bootstrap failed")
    raise  # Let FastAPI return 500
```

---

### 💡 RUNTIME PERFORMANCE IMPROVEMENTS

#### 1. Increase Database Query Efficiency
**Priority:** High (impacts all endpoints)

Already partially addressed (joinedload used), but incomplete.

**Recommendations:**
- [ ] Add eager loading for all league_member queries
- [ ] Add eager loading for all pick queries with games
- [ ] Cache active league (it's global but changes rarely)
- [ ] Add composite indexes for standing queries

**Example:**
```python
# In league_member_repository.py
def list_by_league(db: Session, league_id: uuid.UUID) -> list[LeagueMember]:
    return list(
        db.execute(
            select(LeagueMember)
            .where(LeagueMember.league_id == league_id)
            .options(joinedload(LeagueMember.user))
            .order_by(LeagueMember.created_at)
        ).scalars()
    )
```

---

#### 2. Reduce API Round-Trips During Page Transitions
**Priority:** Medium (improved UX for picks flow)

Currently: Each page load may require 3-4 requests (week, games, picks)

**Status:** ✅ Partially fixed - `GET /picks/card/current` consolidates into one call

**Still TODO:**
- [ ] Optimize game fetch to avoid N+1 when serializing all games
- [ ] Consider caching week data (rarely changes during season)

---

#### 3. Monitor Database Connection Pool Health
**Priority:** High (production reliability)

**Implementation:**
- Add metrics export (Prometheus format)
- Monitor: pool utilization, connection age, query latency
- Alert on: > 80% utilization, queries > 1s

**Tools:**
- Use `SQLAlchemy event hooks` for query timing
- Export to Fly.io metrics or external monitoring

---

#### 4. Improve Frontend Bundle Caching
**Priority:** Low (nice-to-have)

**Status:** ✅ Already done - code splitting with React.lazy()

**Current:** 256.60 kB raw / 81.62 kB gzip (good for a SPA)

**Potential improvements:**
- Add service worker for offline support
- Pre-compress assets for Fly CDN
- Add resource hints: `preload`, `prefetch` for critical routes

---

## Summary of Fixes by Category

| Category | Blockers | Bugs | Improvements | Status |
|----------|----------|------|--------------|--------|
| Job Scheduling | 1 | 0 | 0 | ❌ Not Fixed |
| Error Handling | 1 | 1 | 1 | ❌ Not Fixed |
| Query Performance | 0 | 3 | 2 | ⚠️ Partial |
| Database Config | 0 | 1 | 0 | ❌ Not Fixed |
| UI/UX | 0 | 1 | 1 | ⚠️ Partial |

---

## Recommended Fix Priority

**Phase 1 (Must fix before production):**
1. ✅ Job runner activation (fly.toml)
2. ✅ Session bootstrap error handling
3. ✅ Per-game locking UI alignment

**Phase 2 (Before scaling):**
4. ✅ N+1 query fixes (weeks, lock_expired_picks)
5. ✅ Database connection pooling
6. ✅ Job execution monitoring

**Phase 3 (Nice to have):**
7. Batch operations optimization
8. Advanced caching strategies

---

## Testing Checklist

- [ ] Verify job runner is active in production (check logs, database updates)
- [ ] Confirm no silent errors in session bootstrap (enable error monitoring)
- [ ] Test per-game locking: Thursday game locks, Sunday still editable
- [ ] Query plan review for /weeks endpoint (should be 1 query, not 19)
- [ ] Connection pool stress test (20+ concurrent requests)
- [ ] Scheduled job health endpoint working
- [ ] No N+1 issues in lock_expired_picks (enable slow query log)

---

## Sign-Off

This review identified **3 blocking issues** and **4 high-priority bugs** that must be fixed before production release. All other findings are either already implemented or are optimization opportunities for future phases.

**Recommendation:** Do not deploy to production until blockers are addressed.
