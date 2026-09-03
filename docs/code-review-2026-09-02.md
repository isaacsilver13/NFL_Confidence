# NFL Confidence Pool code review

> Historical review. The findings below describe the pre-fix worktree. Current
> implementation status and validation are recorded in
> [release-readiness.md](release-readiness.md).

Reviewed: 2026-09-02  
Scope: the React/Vite frontend, FastAPI backend, PostgreSQL schema/migrations, deployment and CI configuration. This was a static review with frontend lint, tests, and production build validation. Backend tests could not run locally because `backend/.venv` points at a missing Python 3.10 installation; this is recorded below rather than treated as a passing test run.

## What the application does

NFL Confidence Pool is a private, Google-authenticated web app for running one NFL confidence-pool league. A commissioner creates the league and emails single-use invites. Members pick a winner for every game in the current week and must use each confidence value exactly once. The system imports schedule, venue, spread, score, and status data from ESPN, then derives weekly and season standings from finalized games. The app also exposes a dashboard, pick history, league-member administration, weekly leaderboards, season standings, and aggregate pick breakdowns.

The intended architecture is sound and easy to follow:

```text
React + TanStack Query SPA
          |
FastAPI routes -> services -> repositories -> PostgreSQL
          |
     ESPN data / email / scheduled jobs
```

The frontend is a TypeScript React 19 application built with Vite, Tailwind, React Router, and TanStack Query. The backend uses FastAPI, SQLAlchemy, Alembic, Google OAuth, short-lived JWT access tokens, rotating opaque refresh tokens, and APScheduler.

## Overall assessment

The codebase has a strong foundation for an early private-pool product. Boundaries are generally clear: routes are thin, business rules live in services, persistence is separated into repositories, and database constraints prevent several important duplicate-write races. The frontend is typed and small enough to navigate comfortably. The test suite covers core scoring, schedule normalization, authentication token rotation, and several concurrency cases.

It is not production-ready for the stated product promise yet. The most important work is authorization and reliable operations, not visual polish. In its current Fly configuration, the automated part of the product does not run in production. Separately, the API authenticates users but usually does not verify that they belong to the private league before returning league data or accepting picks.

## Findings, ordered by priority

### Critical — production has no active job runner

`backend/fly.toml` sets `ENABLE_SCHEDULER = "false"`. The FastAPI lifespan only starts APScheduler when that setting is true (`backend/app/main.py`), and this repository contains no Fly worker process, Fly cron configuration, or external scheduler deployment. Consequently production will not automatically import schedules/results, lock picks, calculate scores, or send reminders.

This blocks the core weekly flow. A manual script can run individual jobs, but it is not a replacement for scheduled production execution.

Recommended fix: deploy a dedicated worker/cron process that invokes the existing job functions, with scheduler disabled in all API web instances. Add a database-backed distributed lock or an idempotent job-run table so retries and multiple machines cannot run the same job twice. Add an operational check/alert for the freshness of `nfl_games.last_synced` and for failed job executions. Only enable the in-process scheduler for a deliberately single-instance development environment.

### Critical — “invite-only” authorization is not enforced

Most league routes require only a valid bearer token. For example, `backend/app/api/league.py`, `games.py`, `weeks.py`, `picks.py`, and the weekly/season leaderboard endpoints resolve `current_user` but do not confirm active-league membership. `picks_service.create_picks` also permits any authenticated user to create picks; scoring later excludes non-members, leaving orphaned picks. The pick-breakdown endpoint is the exception and does perform a membership check.

Any Google-authenticated user can therefore view league information and member email addresses, standings, games, and potentially create unusable picks. That is inconsistent with the product requirement for a private, invite-only league.

Recommended fix: add one reusable dependency/service such as `get_active_league_member`, returning `(league, membership)` or raising 403. Use it on every league-scoped read/write endpoint, including current games/weeks, picks, member lists, leaderboards, and history. Keep invitation join as the narrowly scoped exception. Add API tests that prove non-members receive 403 and that members retain access.

### High — an invitation can be accepted by the wrong Google account

`league_service.join_league` validates the token, expiry, and single use, but never compares `Invite.email` with `User.email`. Anyone who obtains a valid invitation link can use it after signing in with a different Google account.

Recommended fix: compare canonicalized email addresses before creating membership and return a non-revealing 403/validation error on mismatch. Consider making invite tokens single-use only after this check, and add tests for a matching email, a mismatching email, and concurrent attempts.

### High — pick-lock behavior contradicts the product requirements

The product requirements say games lock individually at kickoff. The backend computes one deadline from the earliest game and forbids all updates after it (`backend/app/services/picks_service.py`); the UI repeats that behavior in `frontend/src/pages/PicksPage.tsx`. This means a Thursday kickoff prevents a member from finishing Sunday/Monday picks, defeating the expected weekly flow.

Recommended fix: model locking per game. Allow partial upserts only for games whose kickoff is still in the future, preserve already locked picks, and validate confidence uniqueness across the complete card. The UI should disable only started-game controls and clearly distinguish incomplete editable picks. This needs focused tests for Thursday/Sunday/Monday scenarios and concurrent last-second submissions.

### High — scoring result rows lack a database uniqueness guarantee

`score_week` uses query-then-insert helpers for `WeeklyResult` (`backend/app/services/scoring_service.py`), but the `weekly_results` model/migration has no unique constraint on `(league_id, week_id, user_id)`. Concurrent score jobs can both observe no row and insert duplicates. The currently disabled production scheduler masks the risk, but retrying a future worker or operating more than one instance will reintroduce it.

Recommended fix: add a unique constraint for `(league_id, week_id, user_id)`, migrate existing duplicates safely, and use a PostgreSQL upsert or row locking when materializing results. Add a concurrent scoring test. Add composite indexes matching the standings queries, such as `(league_id, week_id)` on weekly results and `(league_id, season)` on season results if query plans justify them.

### Medium — team “logos” are abbreviations, not logo assets

`frontend/src/components/nfl/TeamLogo.tsx` renders team abbreviations inside a circular color badge. Its palette includes only 10 of 32 NFL teams, and no caller supplies the optional `imageSrc`, so the app never renders an actual logo. A failed future image URL would also leave an empty image because there is no `onError` fallback.

Recommended implementation:

1. Choose and document a source with rights appropriate for the product. The lowest-latency, most reliable UI option is a vetted local set of 32 small SVG/PNG assets with a retained attribution/licensing record. Do not scrape arbitrary logo URLs at render time.
2. Add a typed `TEAM_LOGOS` manifest keyed by the exact ESPN abbreviation, complete it for all 32 teams, and make `TeamLogo` resolve the image internally. Retain the current abbreviation badge as an accessible failure fallback.
3. Render explicit `width`/`height`, `decoding="async"`, and `loading="lazy"` for below-the-fold images; add `onError` to switch to the badge. Use `alt=""` when the adjacent team name already supplies the text, as it does in the picks UI.
4. Test all 32 codes, the unknown-code fallback, and image-load failure. Reuse the same component in picks and pick-breakdown views, which the project already mostly does.

An alternative is to capture ESPN's `team.logos` URL during schedule normalization and return it in the game API. That reduces asset maintenance but introduces a third-party availability, CSP, caching, and licensing dependency on the interactive path. If selected, proxy/cache the images through a controlled CDN rather than fetching them per card directly from ESPN.

### Medium — several avoidable runtime costs are visible

* The production frontend is one eagerly loaded JavaScript bundle: 311.41 kB raw / 94.83 kB gzip in the reviewed build. `App.tsx` statically imports every page, including the standings view that uses Recharts. Lazy-load route pages (at least standings/profile/admin) with `React.lazy` and a small loading fallback so the picks flow has less parse and transfer cost.
* On every page refresh, `AuthProvider` calls `/auth/me` without an access token. The fetch wrapper receives 401, refreshes the token, and retries `/auth/me`: three requests for a valid returning session. Expose a small `refreshSession` function and bootstrap with refresh then `/me`, reducing the common path to two requests and avoiding an intentional 401.
* `import_games` looks up each ESPN game one at a time; `score_week` does per-member query-then-create for weekly and season results; `lock_expired_picks` lazy-loads `game.picks` in a nested loop. These are small at a 20-member/17-game pool, so they are not the first performance priority, but batch reads, bulk updates, and upserts will make the scheduled path predictable and reduce database round trips.
* `GET /weeks` serializes `week.games` without eager loading, creating a query per returned week. Use `selectinload(NflWeek.games)` or calculate `locks_at` in the query if this endpoint is used for a full-season view.
* The weekly pick page runs three independent requests for current week, games, and picks. A single `GET /picks/current-card` response could return all three atomically, save two HTTP/database round trips, and prevent mixed data during a schedule update. Keep individual endpoints only if other consumers need them.

Measure these changes with real browser Web Vitals and API timings before and after. The stated targets (<1 s dashboard, <200 ms API) cannot be confirmed from a static review.

### Medium — test and delivery safeguards do not meet documented targets

CI runs backend tests with `pytest --cov=app` but does not enforce a coverage threshold or publish a report. Frontend CI runs Vitest without coverage even though the architecture document targets 90% backend and 80% frontend coverage. There is no end-to-end browser test for OAuth/session bootstrap, invite acceptance, complete pick entry, or production job behavior.

Recommended fix: enforce realistic, ratcheted coverage thresholds; add API authorization tests first; then add Playwright coverage for the critical member journey and a deployment smoke test that verifies job freshness. Do not use coverage as a substitute for the permission and job-runner tests above.

The frontend's configured `format:check` currently fails across 31 existing files. Since the CI workflow runs this check, the frontend job will not be green until that baseline formatting drift is reconciled.

### Low — a few maintainability and security details need tightening

* Invitation email HTML interpolates `league_name` and `commissioner_name` without escaping (`backend/app/services/email_service.py`). Escape all dynamic HTML fields, not only the reminder fields.
* The dashboard shows hard-coded “Not scored” ranks despite the application already exposing standings data. It is a misleading product state rather than a backend limitation.
* The architecture document describes a multi-league-looking product, but code enforces exactly one active league globally. Either document that explicit product constraint prominently or redesign league selection and all league-scoped records before attempting multiple pools.
* The developer environment has drift: `pyproject.toml` targets Python 3.10 while the architecture document says 3.13, Docker uses 3.10, and the local virtual environment is broken. Pick one supported version, recreate the environment from lock/pinned dependencies, and add a quick setup check.

## What is already working well

* The domain model has useful foreign keys, UUIDs, unique pick constraints, and a partial unique index for the single active league.
* The pick submission path validates complete-card coverage, valid team selection, and unique confidence values server-side; it also serializes simultaneous submissions from the same user.
* ESPN data normalization is isolated behind an integration module and has dedicated tests for schedule metadata.
* Refresh tokens are opaque, hashed at rest, rotated on use, and stored in an HTTP-only cookie; access tokens are short-lived and held in frontend memory.
* The frontend has a consistent component/style system, responsive pick cards, typed API DTOs, React Query caching, and useful unit tests for representative views.
* CI performs backend lint/format/type checks and frontend lint/test/build checks, which is a good base to extend.

## Recommended delivery order

1. Before adding features: deploy a real job runner, add monitoring, enforce active-league membership everywhere, and bind invitations to recipient email.
2. Restore the promised per-game locking flow and add the missing result-row constraint/upsert behavior.
3. Add team logos through a complete local manifest and resilient `TeamLogo` fallback; this is a contained, high-visibility UI improvement.
4. Improve perceived runtime with route splitting, the two-request auth bootstrap, and a combined current-picks-card endpoint. Benchmark before/after.
5. Add authorization, scheduler, and end-to-end critical-path tests; then enforce coverage thresholds.

## Verification performed

* `frontend`: `npm.cmd run lint` passed.
* `frontend`: `npm.cmd test -- --run` completed successfully.
* `frontend`: `npm.cmd run build` passed; build output was 311.41 kB JavaScript (94.83 kB gzip) and 30.01 kB CSS (6.06 kB gzip).
* `frontend`: `npm.cmd run format:check` failed because Prettier reports formatting drift in 31 existing files.
* `backend`: test execution was attempted but could not start because `backend/.venv` references a missing `C:\Users\justj\AppData\Local\Programs\Python\Python310\python.exe`. No backend test result is claimed.
