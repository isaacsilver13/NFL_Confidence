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

- No third-party analytics service. No new database table. No real-time dashboard.
- No backfill: there is no usage history before tracking ships. First reports will be thin.
- No tracking of anonymous (logged-out) visitors.

## Anti-goals (failure even if it "works")

- Tracking that slows the app, fails a user action when the event call fails, or
  floods the database.
- Logging raw tokens, emails, or free text in event metadata.
- A report that mistakes silent token refreshes for real logins.

## Findings that shape the design (from reading the code)

- `audit_log` (user_id, action, entity, JSONB `metadata`, created_at; indexed on
  user_id and action) exists in the schema but nothing writes to it. It is the home for
  events, so no migration is needed.
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

### Events (stored in `audit_log`)

| action | written by | metadata |
|---|---|---|
| `login` | backend, in `google_callback` / `dev_login` after tokens are issued | none |
| `session_start` | frontend, once per app load after auth bootstrap | `{device: "phone"|"desktop"}` |
| `page_view` | frontend, on route change | `{path}` (path only, no query string) |
| `section_open` | frontend, when a dashboard section is opened by the user | `{section}` |
| `heartbeat` | frontend, every 30 s while the tab is visible and the user interacted in the last 2 min | `{path}` |

`entity` is set to `"usage"` for client events and `"auth"` for `login`.

### Backend

- `POST /api/v1/events`: authenticated, accepts one event or a small batch, validates
  `action` against a fixed allow-list and `metadata` keys/length, rate-limited like other
  routes. Follows routes -> services -> repositories. Failure returns quietly; it must
  never break the page.
- Event writes use the existing `audit_log` model through a small repository function.
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
- No migration. No deploy, no production writes by this work. Report queries are SELECT only.
- Follow the repo's lint, type, and coverage gates (`pytest --cov-fail-under=77`, ruff,
  black, isort, mypy; eslint, prettier, vitest, `tsc`).

## Decided by the user

- Report covers logins, time on app, pages and tabs, feature use, plus DAU/WAU and
  per-user login time series.
- Tracking is added to the app (backend + frontend) as proposed.

## My calls (the user has not confirmed these)

- Reuse `audit_log` instead of a new table.
- 30 s heartbeat as the time-on-app measure.
- Skill lives in the repo (`.claude/skills/usage-report/`) rather than user-global.
- HTML report file as output.
- Device split and never-returned users are included as extras.
- `audit_log` verified to fit: `user_id` nullable FK (ON DELETE SET NULL), `action`
  String(128) with no check constraint, JSONB metadata, nothing else reads or writes it.
  No migration needed.
- `/events` rate limit: the existing `30/hour` auth pattern and IP keying would reject
  heartbeats (120/hour/user) and merge users behind shared IPs. Use a user-id key
  function and about 300/hour per user; over-limit returns 429 and the client swallows it.
- No retention or pruning in this change; revisit if the table grows (see open questions).
- "Never returned" = user with a `login` event but no `session_start` on any later day.
  Users with no events at all (signed up before tracking) are labelled "no data yet",
  not "never returned".

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
- League is about 20 people: plain rows, no batching, no pruning.
- Exclude test accounts from the report; keep the league admin. The builder lists users
  on the first run and confirms with the user which are test accounts, then stores that
  exclusion list in the skill.

## Open questions for the user

None blocking.

## Weakest assumption / biggest risk

Heartbeats are a fair proxy for time on the app. If people mostly glance at the app on
a phone and background it, reported time will be low. A secondary risk is event volume:
30 s heartbeats across a league are small, but retention is not designed here.
