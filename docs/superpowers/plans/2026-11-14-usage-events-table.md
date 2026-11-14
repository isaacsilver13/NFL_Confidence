# Usage Events Table and Retention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move client-reported usage telemetry out of `audit_log` into a dedicated `usage_events` table and prune it automatically after 180 days.

**Architecture:** Add a typed `usage_events` table (no free-form JSON), write client events there in one batched insert, keep `login` events in `audit_log` (low volume, security-relevant), and delete old usage rows with a daily job that rides the existing tick/slot machinery. The usage-report SQL reads logins from `audit_log` and everything else from `usage_events`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (Neon), pytest.

**Spec:** `docs/superpowers/specs/2026-11-12-usage-analytics-design.md`. This plan supersedes two of its decisions: "No migration needed" (audit_log reuse) and "No retention or pruning in this change". Task 5 updates the spec to match.

## Global Constraints

- Backend changes stay under `backend/`; Python 3.10 (3.14 is not a supported substitute).
- Alembic migrations are the schema source of truth; never edit an applied migration. `fly.toml` runs `alembic upgrade head` as the release command, so the migration executes on the next prod deploy.
- Gates, run from `backend/`: `ruff check .`, `black --check .`, `isort --check-only .`, `mypy app`, `pytest --cov=app --cov-fail-under=77`.
- Backend tests need Postgres: start it with `backend/scripts/prepare_local.ps1` (Docker Compose) first.
- Do not push, merge, deploy, or touch production data unless the user explicitly asks. The report skill stays SELECT-only.
- Never commit secrets, database URLs, or `exclude.txt`.
- Retention is **180 days** (decided here: it covers a full season Sep-Feb; the user should confirm).
- Heartbeat interval stays 30 s; `/events` keeps 600/hour per user and at most 5 events per request.

## Review Focus

- Existing `audit_log` rows with `entity = 'usage'` (only if PR #85 was deployed before this lands): their history disappears from the report unless backfilled. Task 5 checks the count before deploy.
- A member who is deleted: their `usage_events` must go too (privacy), not linger with a NULL user. Task 1 pins this.
- The prune job run twice in a day, or on a late tick: deletes nothing the second time and never touches `audit_log`, `picks`, or other tables. Task 4 pins this.
- A failing prune must not fail the tick or block the other jobs: Task 4 relies on the existing per-job isolation and adds a test that the tick still reports the other jobs as `success`.
- A batch holding all four action kinds must land in the right typed columns (a `heartbeat` has `path` only, `section_open` has `section` only, `session_start` has `device` only). Task 2 pins this.

---

### Task 1: `usage_events` model and migration

**Files:**
- Create: `backend/app/models/usage_event.py`
- Create: `backend/alembic/versions/<new_rev>_create_usage_events_table.py`
- Modify: `backend/app/models/__init__.py` (import and `__all__`)
- Test: `backend/tests/test_usage_event_model.py`

**Interfaces:**
- Produces: `class UsageEvent(Base)`, `__tablename__ = "usage_events"`, columns `id: uuid (pk, default uuid4)`, `user_id: uuid` (FK `users.id`, `ondelete="CASCADE"`, not null), `action: String(16)`, `path: String(200) | None`, `section: String(32) | None`, `device: String(16) | None`, `created_at: timestamptz` (`server_default=func.now()`); indexes `ix_usage_events_created_at (created_at)` and `ix_usage_events_user_id_created_at (user_id, created_at)`.

- [ ] **Step 1: Write the failing tests** in `test_usage_event_model.py`: `test_usage_event_round_trip` (insert a `UsageEvent(user_id=..., action="page_view", path="/picks")`, flush, reload, assert fields and a non-null `created_at`); `test_deleting_user_deletes_their_usage_events` (insert user + two events, delete user, assert zero `UsageEvent` rows remain).
- [ ] **Step 2: Run** `pytest tests/test_usage_event_model.py -v`. Expected: FAIL (`ImportError: UsageEvent`).
- [ ] **Step 3: Implement the model** following `app/models/audit_log.py` style; register it in `models/__init__.py`.
- [ ] **Step 4: Write the migration.** Run `alembic heads` first and set `down_revision` to the single head it prints (the repo has 22 revisions; do not guess). `upgrade()` creates the table and both indexes; `downgrade()` drops the indexes then the table. Create-only: no change to `audit_log`.
- [ ] **Step 5: Verify.** Run `pytest tests/test_usage_event_model.py tests/test_schema_validator.py tests/test_models.py -v` (expect PASS), then against the local database `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head` (expect no errors).
- [ ] **Step 6: Commit** `feat(usage): add usage_events table`.

### Task 2: Write client events to `usage_events`

**Files:**
- Create: `backend/app/repositories/usage_event_repository.py`
- Modify: `backend/app/services/usage_service.py` (`record_events` only; `record_login` stays on `audit_log`)
- Modify: `backend/tests/test_events.py` (assertions currently read `AuditLog`)
- Test: `backend/tests/test_events.py`

**Interfaces:**
- Consumes: `UsageEvent` (Task 1); `EventIn` from `app.schemas.usage`.
- Produces: `usage_event_repository.create_many(db: Session, user_id: uuid.UUID, rows: Sequence[Mapping[str, str | None]]) -> None` (keys `action`, `path`, `section`, `device`; one `add_all` and one flush). `usage_service.record_events(db, user_id, events: list[EventIn]) -> None` keeps its signature and maps `event.metadata` onto the typed keys.

- [ ] **Step 1: Update tests first.** In `test_events.py`, change the row helper to read `UsageEvent`, and add `test_batch_maps_each_action_to_typed_columns` (post one request with a `session_start`, `page_view`, `heartbeat` and `section_open`; assert `device="phone"` only on the first, `path` on the second and third, `section` on the last, the others `None`) and `test_client_events_do_not_write_audit_log` (assert no `AuditLog` row with `entity == "usage"`).
- [ ] **Step 2: Run** `pytest tests/test_events.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the repository and switch `record_events` to build one dict per event and call `create_many`, then `db.commit()` once.
- [ ] **Step 4: Run** `pytest tests/test_events.py tests/test_auth.py -v`. Expected: PASS (login tests still read `audit_log`).
- [ ] **Step 5: Commit** `feat(usage): store client events in usage_events`.

### Task 3: Point the report queries at the new table

**Files:**
- Modify: `.claude/skills/usage-report/queries.sql`
- Modify: `backend/tests/test_usage_report_queries.py` (seed non-login events as `UsageEvent`, keep logins as `AuditLog`)
- Modify: `.claude/skills/usage-report/SKILL.md` (one line: logins come from `audit_log`, activity from `usage_events`)

**Interfaces:**
- Consumes: `UsageEvent` columns from Task 1 (`action`, `path`, `section`, `device`, `created_at`); `metadata->>'path'` and friends become the typed columns.
- Produces: the same named queries and result columns as today, so `render_report.py` is unchanged.

- [ ] **Step 1: Update the seeding helper** so `_event(...)` builds `AuditLog` for `login` and `UsageEvent` for every other action. Add `test_activity_without_login_rows_still_counts_in_dau` if `test_dau_*` does not already cover it.
- [ ] **Step 2: Run** `pytest tests/test_usage_report_queries.py -v`. Expected: FAIL (queries still read `audit_log`).
- [ ] **Step 3: Rewrite the queries.** `login`-based queries stay on `audit_log`; `heartbeat`, `page_view`, `section_open`, `session_start` read `usage_events`. In `dau`, `wau` and `never_returned`, build the activity set as `login` rows from `audit_log` `UNION ALL` the three activity actions from `usage_events`. Keep `{{EXCLUDE}}` handling and the `users` join exactly as is.
- [ ] **Step 4: Run** `pytest tests/test_usage_report_queries.py -v`. Expected: PASS; also run `python .claude/skills/usage-report/test_render.py`.
- [ ] **Step 5: Commit** `feat(usage): read report data from usage_events`.

### Task 4: Daily retention job

**Files:**
- Create: `backend/app/jobs/usage_retention.py`
- Modify: `backend/app/repositories/usage_event_repository.py` (add `delete_older_than`)
- Modify: `backend/app/jobs/tick.py` (`JOB_FUNCTIONS`)
- Modify: `backend/app/jobs/schedule.py` (`due_slots`: daily list and the `order` list)
- Modify (pinned expectations): `backend/tests/test_schedule.py` (exact slot lists near the `overnight_score_sync` assertions) and `backend/tests/test_internal_tick.py` (the `calls ==` dicts and the fixture that swaps `JOB_FUNCTIONS`; find it with `grep -n JOB_FUNCTIONS tests/`)
- Test: `backend/tests/test_usage_retention.py`

**Interfaces:**
- Consumes: `UsageEvent`.
- Produces: `usage_event_repository.delete_older_than(db: Session, cutoff: datetime) -> int`; `usage_retention.USAGE_RETENTION_DAYS = 180`; `usage_retention.prune_usage_events() -> int` (opens `SessionLocal`, deletes rows older than the cutoff, commits, returns the deleted count); job name `"prune_usage_events"`.

- [ ] **Step 1: Write failing tests.** `test_usage_retention.py`: rows at 179 and 181 days old, run `prune_usage_events()`, assert the 181-day row is gone and the 179-day row stays, the return value is 1, a second run returns 0, and an old `audit_log` row is untouched. `test_schedule.py`: `prune_usage_events` is absent at 01:59 local and present once from the overnight hour, with a single slot key per local day (`prune_usage_events:YYYY-MM-DD`) that is stable across a late tick.
- [ ] **Step 2: Run** `pytest tests/test_usage_retention.py tests/test_schedule.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** The job joins the existing daily bucket (`hour >= cfg.overnight_sync_hour`), so no new setting. Add `"prune_usage_events"` to the `order` list in `due_slots` (it raises on an unknown name) and to `JOB_FUNCTIONS`.
- [ ] **Step 4: Fix the pinned tests.** Update the exact-equality slot lists in `test_schedule.py` and the call-count dicts in `test_internal_tick.py`, and add a fake `prune_usage_events` to the fixture that swaps `JOB_FUNCTIONS` so tick tests never run the real job. Add `test_failing_prune_does_not_fail_other_jobs` (fake raises; assert the other jobs report `success` and the tick returns 200).
- [ ] **Step 5: Run the whole backend suite** `pytest --cov=app --cov-fail-under=77`, then `ruff check .`, `black --check .`, `isort --check-only .`, `mypy app`. Expected: all pass.
- [ ] **Step 6: Commit** `feat(usage): prune usage_events after 180 days`.

### Task 5: Docs and the pre-deploy check

**Files:**
- Modify: `docs/superpowers/specs/2026-11-12-usage-analytics-design.md` (replace "No migration needed" and "No retention or pruning in this change" with the decisions above)
- Modify: `docs/superpowers/plans/2026-11-12-usage-analytics.md` (one note pointing at this plan)

- [ ] **Step 1: Update both docs** to describe `usage_events`, `login` staying in `audit_log`, and 180-day retention.
- [ ] **Step 2: Pre-deploy check (read-only).** Using the Neon MCP `run_sql` against the prod project, run `SELECT count(*) FROM audit_log WHERE entity = 'usage'`. If the count is 0, no data migration is needed. If it is above 0, stop and add a one-off backfill (`INSERT INTO usage_events ... SELECT ... FROM audit_log WHERE entity = 'usage'`, mapping `metadata->>'path'|'section'|'device'`) as its own reviewed migration before deploying.
- [ ] **Step 3: Stop.** Do not merge or deploy. Report the check result and the exact PR state, and wait for the user's go-ahead.
- [ ] **Step 4: Commit** `docs(usage): record usage_events and retention decisions`.

## Weakest assumption and biggest risk

- **Weakest assumption:** PR #85 has not been deployed, so there is no usage data in `audit_log` yet. Task 5 checks it with one read-only query and is the only thing standing between "no backfill" and silent history loss.
- **Biggest risk:** the retention job is a new slot in a scheduler whose tests pin exact slot lists. If Task 4's test updates miss a fixture, tick tests start running the real job against the wrong schema. Run the full suite, not just the new files.
