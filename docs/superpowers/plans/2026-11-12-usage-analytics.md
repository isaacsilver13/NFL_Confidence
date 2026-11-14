# Usage Analytics and On-Demand Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record logins, page views, dashboard-section opens and active-time heartbeats in the existing `audit_log` table, and add a `usage-report` skill that turns them into an HTML report with DAU/WAU and per-user login charts.

**Architecture:** Backend writes a `login` row in the Google/dev login path and exposes `POST /api/v1/events` for client events. A frontend hook mounted in `AppLayout` sends `session_start`, `page_view`, `heartbeat` and `section_open`. The report skill runs SELECT-only SQL through the Neon MCP `run_sql` inside a Claude session, saves the JSON, and a stdlib Python script renders a self-contained HTML file with inline SVG charts.

**Tech Stack:** FastAPI, SQLAlchemy, slowapi, pytest; React, react-router, vitest, `apiFetch`; Python stdlib for the renderer.

**Spec:** `docs/superpowers/specs/2026-11-12-usage-analytics-design.md`

## Global Constraints

- No new table and no Alembic migration; reuse `audit_log` (`action` String(128), `entity` String(128), JSONB `metadata`, nullable `user_id`).
- Event actions are exactly: `login`, `session_start`, `page_view`, `section_open`, `heartbeat`. `entity` is `"auth"` for `login`, `"usage"` for the rest.
- Metadata: `page_view`/`heartbeat` `{path}` (path only, no query string or hash); `section_open` `{section}`; `session_start` `{device: "phone"|"desktop"}`; `login` none.
- Heartbeat every 30 s only while the tab is visible AND the user interacted in the last 2 minutes. No polling, cron, or keep-alive anywhere (Fly machines scale to zero).
- `/events` rate limit about 600/hour per user (keyed by user id, falling back to IP); over-limit is 429 and the client swallows it. Event failures must never break a page or a login.
- Report is SELECT-only, uses the Neon MCP, stores no credential, excludes test accounts, keeps the league admin.
- Active time = distinct 30 s heartbeat buckets x 30 s (a floor). "Never returned" = tracked activity (`login`, `session_start` or `page_view`) on a single day only; users with no tracked activity are "no data yet".
- Backend changes under `backend/`, frontend under `frontend/`. Gates: `ruff check .`, `black --check .`, `isort --check-only .`, `mypy app`, `pytest --cov=app --cov-fail-under=77`; `npm run lint`, `npm run format:check`, `npm run test`, `npm run build`.
- Never commit secrets or database URLs. Do not push, merge, or deploy.

## Review Focus

- Invite codes in the URL: `/join?code=...` must never be stored; client strips query/hash and the server rejects any `path` containing `?` or `#`.
- Tracking must not trigger auth side effects: an event sent with an expired token must not kick off a token refresh (use `skipAuthRetry`) and a 401 is swallowed.
- Oversized or unknown input: unknown `action`, extra metadata keys, bad `section`/`device` values, or more than 5 events in a batch return 422 and write nothing.
- Cleanup: after sign-out or unmount no timers or listeners remain and no events are sent.
- Users with `user_id` NULL (deleted accounts) and test accounts must not appear in the report; an empty database must still render a valid report.

---

### Task 0: Branch

**Files:** none

- [ ] **Step 1:** `git fetch origin`, then `git switch -c feat/usage-analytics origin/develop` (untracked spec and plan files carry over; if develop is missing, branch from `main` and say so).
- [ ] **Step 2:** `git status` shows only the two docs files untracked; commit them: `docs: usage analytics design and plan`.

---

### Task 1: Events endpoint

**Files:**
- Create: `backend/app/schemas/usage.py`, `backend/app/repositories/audit_log_repository.py`, `backend/app/services/usage_service.py`, `backend/app/api/events.py`
- Modify: `backend/app/core/limiter.py` (add `user_rate_key`), `backend/app/main.py:112-121` (register `events_router` with prefix `/api/v1`)
- Test: `backend/tests/test_events.py`

**Interfaces:**
- Produces: `schemas.usage.EventIn(action: Literal[...], metadata: dict[str, str] | None)`, `EventsIn(events: list[EventIn])` (1 to 20), validators enforcing the metadata rules in Global Constraints. `audit_log_repository.create(db, *, user_id: uuid.UUID | None, action: str, entity: str, event_metadata: dict[str, str] | None) -> AuditLog` (flush only). `usage_service.record_events(db, user_id: uuid.UUID, events: list[EventIn]) -> None` (adds rows, one commit). `limiter.user_rate_key(request: Request) -> str` (decodes the Bearer JWT `sub`, else `get_remote_address`). `POST /api/v1/events` returns 204.
- Consumes: `get_current_user`, `get_db`, `limiter`.

- [ ] **Step 1: Write failing tests** in `backend/tests/test_events.py` (auth header helper as in `test_league.py:18`): `test_requires_auth` (401 without token), `test_records_events` (batch of `session_start{device:"phone"}`, `page_view{path:"/picks"}`, `heartbeat{path:"/"}`, `section_open{section:"standings"}` returns 204 and four `audit_log` rows with that user id, entity `"usage"`), `test_rejects_unknown_action` (422, zero rows), `test_rejects_query_string_in_path` (`/join?code=ABC` and `/#x` both 422), `test_rejects_bad_section_device_and_extra_keys` (422), `test_rejects_more_than_20_events` (422), `test_login_action_not_accepted_from_client` (422, since `login` is server-only).
- [ ] **Step 2:** `pytest backend/tests/test_events.py -v` (from `backend/`). Expected: FAIL (404/import errors).
- [ ] **Step 3:** Implement schemas, repository, service and route per Interfaces. Route is thin: validate, call service, return 204. Decorate with `@limiter.limit("600/hour", key_func=user_rate_key)`. The valid `section` set is `leaderboard|breakdown|standings|profile`.
- [ ] **Step 4:** Run the file again. Expected: all PASS. Then `ruff check .`, `black --check .`, `isort --check-only .`, `mypy app`.
- [ ] **Step 5:** Commit `feat(api): add usage events endpoint`.

---

### Task 2: Server-side login event

**Files:**
- Modify: `backend/app/services/usage_service.py` (add `record_login`), `backend/app/api/auth.py:146-154` (`google_callback`) and `:189-191` (`dev_login`)
- Test: `backend/tests/test_auth.py` (add cases, reusing its existing dev-login fixtures)

**Interfaces:**
- Produces: `usage_service.record_login(db, user_id: uuid.UUID) -> None` writes `action="login"`, `entity="auth"`, no metadata, in its own commit; catches `SQLAlchemyError`, rolls back, logs a warning, never raises.
- Consumes: `audit_log_repository.create`.

- [ ] **Step 1: Write failing tests:** `test_dev_login_records_login_event` (one `login` row for the dev user after `POST /api/v1/auth/dev-login`), `test_refresh_does_not_record_login` (zero `login` rows after `POST /api/v1/auth/refresh`), `test_record_login_swallows_db_errors` (monkeypatch the repository to raise `SQLAlchemyError`; call returns without raising).
- [ ] **Step 2:** Run `pytest tests/test_auth.py -v`. Expected: the new tests FAIL.
- [ ] **Step 3:** Implement `record_login` and call it after `issue_tokens` in both login paths, never in `refresh`.
- [ ] **Step 4:** Run the file. Expected: PASS. Run `pytest --cov=app --cov-fail-under=77` for the full backend gate.
- [ ] **Step 5:** Commit `feat(auth): record login events`.

---

### Task 3: Frontend tracking

**Files:**
- Create: `frontend/src/api/events.ts`, `frontend/src/features/usage/useUsageTracking.ts`
- Modify: `frontend/src/layouts/AppLayout.tsx` (call `useUsageTracking()` once, inside the component), `frontend/src/pages/DashboardPage.tsx` (call `trackSectionOpen` in `toggleSection` when `opening`, and in `handleHashChange` when the hash maps to a section)
- Test: `frontend/src/api/events.test.ts`, `frontend/src/features/usage/useUsageTracking.test.tsx`

**Interfaces:**
- Produces: `sendEvent(action: EventAction, metadata?: Record<string, string>): void` (fire-and-forget `apiFetch('/events', { method: 'POST', body, skipAuthRetry: true })`, swallows every error). `trackSectionOpen(section: string): void` calls `sendEvent('section_open', { section })`. `shouldHeartbeat(now: number, lastInteractionAt: number, hidden: boolean): boolean` is true only when not hidden and `now - lastInteractionAt <= 120_000`. `useUsageTracking(): void`.
- Consumes: `apiFetch` (`client.ts:107`), `useAuth()` (only track when `user` is set), react-router `useLocation`.

- [ ] **Step 1: Write failing tests.** `events.test.ts`: `sendEvent` posts `/events` with `skipAuthRetry`, and a rejected fetch does not throw or reject. `useUsageTracking.test.tsx` (fake timers): `sends session_start once with a device value`, `sends page_view with pathname only on route change (query and hash stripped)`, `sends heartbeat every 30s while interacting`, `stops heartbeats 2 minutes after the last interaction and sends none after that (idle tab)`, `resumes after the next interaction`, `sends nothing while document.hidden`, `sends nothing and registers no listeners after unmount`. Also `shouldHeartbeat` boundary cases at exactly 120_000 and 120_001.
- [ ] **Step 2:** `npm run test -- events useUsageTracking` (from `frontend/`). Expected: FAIL (modules missing).
- [ ] **Step 3:** Implement. Device is `"phone"` when `window.matchMedia('(max-width: 639px)').matches`, else `"desktop"`. Interaction events: `pointerdown`, `keydown`, `scroll`, `touchstart` (passive listeners, `lastInteractionAt` kept in a ref). One `setInterval(30_000)` created in an effect, cleared on cleanup and on logout.
- [ ] **Step 4:** Run the two test files, then `npm run lint`, `npm run format:check`, `npm run test`, `npm run build`. Expected: all pass.
- [ ] **Step 5:** Commit `feat(ui): track page views, sections and active time`.

---

### Task 4: Report skill

**Files:**
- Create: `.claude/skills/usage-report/SKILL.md`, `.claude/skills/usage-report/queries.sql`, `.claude/skills/usage-report/render_report.py`, `.claude/skills/usage-report/exclude.txt`, `.claude/skills/usage-report/test_render.py`
- Verify first: `git check-ignore .claude/skills/usage-report/SKILL.md`. If ignored, report that to the user and ask whether to store the skill user-globally instead; do not force-add.

**Interfaces:**
- Produces: `queries.sql` named queries (`-- name: logins_per_user`, `active_buckets_per_user`, `page_views`, `section_opens`, `dau`, `wau`, `login_series`, `device_split`, `feature_adoption`, `never_returned`), all SELECT, days bucketed with `AT TIME ZONE 'America/Chicago'` (my call; change in one place if wrong), each excluding `user_id IS NULL` and users listed in `exclude.txt`. `render_report.py`: `render(data: dict, out_path: str) -> None` where `data` maps query name to a list of row dicts; CLI `python render_report.py data.json report.html`. Charts are inline SVG polylines (DAU, WAU, one login line per user); no network, no dependencies.
- `SKILL.md` instructs Claude: (1) read `exclude.txt`; on first run list users via `run_sql` and confirm with the user which are test accounts, then write them (emails, one per line); (2) run each query with the Neon MCP `run_sql` against project `nfl-confidence-pool-26`, SELECT only; (3) save results to a temp JSON, run the renderer, give the user the HTML path; (4) summarize adoption (used vs ignored features, including picks and submissions from `picks`/`week_submissions`), top and quiet users, and any caveats (active time is a floor, no pre-tracking history).

- [ ] **Step 1: Write failing test** `test_render.py` using only `assert` and a `main()` self-check: `test_renders_with_empty_data` (all lists empty, output contains "No data yet"), `test_renders_sample` (two users, three days; output contains each display name, an `<svg`, and active time computed as buckets x 30 s), `test_no_external_requests` (output has no `http://` or `https://` URLs).
- [ ] **Step 2:** `python .claude/skills/usage-report/test_render.py`. Expected: FAIL (renderer missing).
- [ ] **Step 3:** Implement `render_report.py` and `queries.sql`; write `SKILL.md` and an empty `exclude.txt` with a header comment.
- [ ] **Step 4:** Run the test. Expected: PASS. Then run `queries.sql` statements against the local Postgres (`backend/scripts/prepare_local.ps1` seed data plus a few rows from the Task 1 endpoint) to confirm each parses and returns rows; do NOT run anything against production in this task.
- [ ] **Step 5:** Commit `feat(skill): add usage-report skill`.

---

### Task 5: Verification

**Files:** none

- [ ] **Step 1:** Run the full backend and frontend gates from Global Constraints (or `backend/scripts/verify.ps1`). Expected: all green; report any pre-existing failures separately.
- [ ] **Step 2:** Start the local stack, sign in with dev login, click through Dashboard, Picks and each dashboard section in the built-in browser, then query local `audit_log`: expect one `login`, one `session_start`, `page_view` rows per route, and `section_open` rows.
- [ ] **Step 3 (cost check):** In the browser, leave the tab visible and untouched for 3 minutes; confirm in the network panel that requests to `/events` stop about 2 minutes after the last interaction.
- [ ] **Step 4:** Report what was verified and what was not. Production data and a real Neon run are NOT verified until the change is deployed (needs the user's approval) and people have used it. After deploy, the first `usage-report` run populates `exclude.txt` with the user.
- [ ] **Step 5:** Write the left-off note per the workspace `AGENTS.md`.

Out of scope: pushing the branch, opening a PR, deploying.
