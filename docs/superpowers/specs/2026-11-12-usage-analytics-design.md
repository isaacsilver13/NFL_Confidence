# Usage analytics and on-demand usage report — design

Date: 2026-11-12. Status: draft for approval.

## Intent

The league admin wants to know how people actually use the app: how often each person
signs in, how long they stay, what they do, which features get used and which get
ignored. Today the app records none of this, so this project adds lightweight event
tracking and a read-only report, run on demand as a skill.

## Goals

- Per person: login count and last login, active time, pages and sections viewed.
- Whole league: daily and weekly active users over time (time-series charts), and a
  login time series per user.
- Feature adoption: which features are used and which are ignored.
- Run on demand, read-only, safe to run against production.

## Non-goals

- No third-party analytics service. No real-time dashboard.
- No backfill: there is no usage history before tracking ships. First reports will be thin.
- No tracking of anonymous (logged-out) visitors.

## Anti-goals (failure even if it "works")

- Tracking that slows the app, fails a user action when the event call fails, or
  floods the database.
- Logging raw tokens, emails, or free text in event metadata.
- A report that mistakes silent token refreshes for real logins.

## Findings that shape the design (from reading the code)

- `audit_log` (user_id, action, entity, JSONB `metadata`, created_at; indexed on
  user_id and action) existed in the schema but nothing wrote to it. It stays the home
  for `login` events. Client events (heartbeats especially) would dominate it, so they
  go to a dedicated `usage_events` table instead (see Design).
- `refresh_tokens.created_at` is written at login AND on every `/auth/refresh`, so it
  cannot separate real logins. Real logins happen in `auth.py` `google_callback`
  (and `dev_login` locally) after `issue_tokens`.
- Pages are routes: `/`, `/picks`, `/league-settings`, `/join` (App.tsx).
- The dashboard "tabs" are accordion sections (leaderboard, breakdown, standings,
  profile) in `DashboardPage.tsx`. They are toggled by `toggleSection`, which uses
  `history.replaceState` and so does NOT fire `hashchange`. Several can be open at
  once and open state is persisted in localStorage. Tracking must hook
  `toggleSection` and the initial open state, not `hashchange`.
- Picks and week submissions are already in `picks` / `week_submissions`, so "made
  picks" can be counted from existing tables with no new events.

## Design

### Events (`login` in `audit_log`, client events in `usage_events`)

| action | written by | metadata |
|---|---|---|
| `login` | backend, in `google_callback` / `dev_login` after tokens are issued | none |
| `session_start` | frontend, once per app load after auth bootstrap | `{device: "phone"|"desktop"}` |
| `page_view` | frontend, on route change | `{path}` (path only, no query string) |
| `section_open` | frontend, when a dashboard section is opened by the user | `{section}` |
| `heartbeat` | frontend, every 30 s while the tab is visible and the user interacted in the last 2 min | `{path}` |

`login` is stored in `audit_log` with `entity = "auth"`. Client events (`session_start`,
`page_view`, `section_open`, `heartbeat`) are stored in `usage_events`, with typed columns
instead of JSONB metadata: `user_id` (FK users, ON DELETE CASCADE), `action` String(16),
`path` String(200) nullable, `section` String(32) nullable, `device` String(16) nullable,
`created_at`; indexed on `created_at` and on `(user_id, created_at)`.

### Backend

- `POST /api/v1/events`: authenticated, accepts one event or a small batch (at most 5 events per request), validates
  `action` against a fixed allow-list and `metadata` keys/length, rate-limited like other
  routes. Follows routes -> services -> repositories. Failure returns quietly; it must
  never break the page.
- Client events are written to `usage_events` in one batched insert through
  `usage_event_repository.create_many`; `login` rows keep using the `audit_log` model.
- Tests for the allow-list, auth requirement, and the login event being written.

### Frontend

- One hook (e.g. `useUsageTracking`) mounted once inside the authenticated layout.
  It sends `session_start`, `page_view` on route change, a heartbeat on a 30 s timer
  paused when `document.hidden`, and exposes a function that `toggleSection` calls to
  send `section_open`. Sends are fire-and-forget; errors are swallowed.
- Tests: hook sends the expected events; no events when logged out.

### Report skill

- A skill (`usage-report`) that runs a script against the database read-only and writes
  an HTML report to a file the user opens.
- Contents: per-user table (logins, last login, active time, pages, sections), feature
  adoption (used vs ignored, using events plus `picks`/`week_submissions`), DAU and WAU
  line charts over time, a login-per-day series per user, device split, and users who
  signed up but never returned.
- Active time = number of distinct 30 s heartbeat buckets x 30 s. Documented as a floor:
  backgrounded phone tabs undercount.
- Takes an optional date range; default is all time.

## Constraints

- Backend changes under `backend/`, frontend under `frontend/`; the skill is separate.
- One Alembic migration creates `usage_events`. No deploy, no production writes by this work. Report queries are SELECT only.
- Follow the repo's lint, type, and coverage gates (`pytest --cov-fail-under=77`, ruff,
  black, isort, mypy; eslint, prettier, vitest, `tsc`).

## Decided by the user

- Report covers logins, time on app, pages and tabs, feature use, plus DAU/WAU and
  per-user login time series.
- Tracking is added to the app (backend + frontend) as proposed.

## My calls (the user has not confirmed these)

- Keep `login` in `audit_log`; store client events in a new `usage_events` table (changed from the original call to reuse `audit_log` for everything).
- 30 s heartbeat as the time-on-app measure.
- Skill lives in the repo (`.claude/skills/usage-report/`) rather than user-global.
- HTML report file as output.
- Device split and never-returned users are included as extras.
- `audit_log` fits `login` as is: `user_id` nullable FK (ON DELETE SET NULL), `action`
  String(128) with no check constraint, JSONB metadata. The `usage_events` table needs a
  migration.
- `/events` rate limit: the existing `30/hour` auth pattern and IP keying would reject
  heartbeats (120/hour/user) and merge users behind shared IPs. Use a user-id key
  function and about 600/hour per user (one visible tab is 120/hour, so several tabs and
  devices fit); over-limit returns 429 and the client swallows it.
- Retention: job `prune_usage_events` (`backend/app/jobs/usage_retention.py`,
  `USAGE_RETENTION_DAYS = 180`) deletes `usage_events` rows older than 180 days. It runs
  through the normal tick/slot machinery as a daily job due from `overnight_sync_hour`,
  slot key `prune_usage_events:YYYY-MM-DD`; no new setting.
- "Never returned" = user whose tracked activity (`login`, `session_start` or `page_view`)
  falls on a single day only. Login rows alone are not enough: members who stay signed in
  through the refresh cookie have none. Users with no tracked activity at all (signed up
  before tracking) are labelled "no data yet", not "never returned".

## Left to the builder

- Event payload batching details, hook naming, chart library for the HTML report
  (prefer a single inline-able option), and how the script obtains read-only database access.

## Cost: do not keep the Fly machine awake

Both `fly.toml` and `fly.dev.toml` use `auto_stop_machines = "stop"` and
`min_machines_running = 0`, so the machine sleeps when idle and every request can wake it
(and Neon compute). In scope, because heartbeats are the one new thing that could defeat that.

- Heartbeat only while the tab is visible AND the user has interacted (pointer, key, scroll,
  touch) in the last 2 minutes. Past that, stop sending until the next interaction. A
  visible but abandoned tab therefore costs nothing after 2 minutes.
- This also makes "active time" mean real activity rather than an open tab.
- No server-side polling, cron, or keep-alive is added. The report never touches Fly.
- Verification must include: a tab left idle past 2 minutes sends no further events.
- Residual cost: each active user generates up to ~2 requests/minute while active, which
  occur while the machine is already awake serving that user.

## Decisions from the user (round 2)

- The report reaches production through the Neon MCP `run_sql` (SELECT only) inside a
  Claude session. No credential stored. The skill is therefore not a standalone script:
  it holds the SQL and the HTML rendering step, and Claude runs the queries.
- League is about 20 people: plain rows (superseded: client events are batch-inserted and pruned at 180 days, see My calls).
- Exclude test accounts from the report; keep the league admin. The builder lists users
  on the first run and confirms with the user which are test accounts, then stores that
  exclusion list in the skill.

## Open questions for the user

None blocking.

## Weakest assumption / biggest risk

Heartbeats are a fair proxy for time on the app. If people mostly glance at the app on
a phone and background it, reported time will be low. A secondary risk is event volume:
30 s heartbeats across a league are small, and `usage_events` is pruned at 180 days.
