# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project boundary

FastAPI backend (`backend/`), React/TypeScript frontend (`frontend/`), PostgreSQL/Alembic schema. Keep backend changes under `backend/` and frontend changes under `frontend/` unless the request names another boundary.

## Commands

Backend (run from `backend/`, Python 3.10 — 3.14 is not a supported substitute):
```
pip install -r requirements.txt
ruff check .                                  # lint
black --check .                               # format check (drop --check to auto-fix)
isort --check-only .                          # import order check
mypy app                                      # type check
pytest --cov=app --cov-fail-under=77          # full suite, matches CI's coverage gate
pytest tests/path/to/test_file.py::test_name  # single test
alembic upgrade head                          # apply migrations
alembic revision --autogenerate -m "..."      # new migration
```
`backend/scripts/prepare_local.ps1` (or the "NFL Confidence: Prepare database and seed test data" task) sets up local Postgres via Docker Compose and seeds deterministic test data. `backend/scripts/verify.ps1` (or the "NFL Confidence: Verify" task) runs the CI-equivalent backend+frontend checks together.

Frontend (run from `frontend/`):
```
npm run dev             # vite dev server
npm run lint            # eslint
npm run format:check    # prettier check (npm run format to auto-fix)
npm run test            # vitest run
npm run test:watch      # vitest watch, useful for a single file/pattern
npm run test:coverage
npm run build           # tsc -b && vite build
npm run test:e2e        # Playwright, mobile viewports only; see docs/testing-strategy.md for preconditions
```

Full local stack: `docker-compose.yml` at repo root brings up Postgres + backend + frontend together.

For a focused change, run the narrowest relevant backend test, frontend test, type check, or build first — keep pre-existing failures separate from failures introduced by the current change.

## Architecture

- Backend flow: routes -> services -> repositories -> models (`app/api`, `app/services`, `app/repositories`, `app/models`). Frontend flow: pages/components/hooks -> API client -> backend routes.
- Alembic migrations (`backend/alembic/`) are the database source of truth — never edit an applied migration to change schema history.
- **Two parallel job-scheduling systems exist in `app/jobs/`**: `scheduler.py` + `nfl_schedule.py` (the live, automatically-running scheduler) and `job_runner.py` + `worker.py` (a separate, admin-triggered path). They are not the same code path — when touching pick-locking or schedule-driven behavior, check which of the two systems the change needs to apply to, and be aware their locking logic has been found to diverge (live scheduler locks per-week; the admin-triggered path has been found to lock per-game). Verify current behavior in both before assuming parity.
- Auth lives in `app/auth`; `app/integrations` holds external API clients; `app/db` holds session/engine setup separate from `app/models`.
- Dev vs prod are fully separate Fly.io apps with separate config: `backend/fly.dev.toml` / `backend/fly.toml` and `frontend/fly.dev.toml` / `frontend/fly.toml`. CI (`.github/workflows/ci.yml`) deploys `develop` → dev Fly apps and `main` → prod Fly apps automatically after backend+frontend checks pass, using `flyctl deploy --config <dev-or-prod>.toml`.
- Consult `docs/technical-architecture.md`, `docs/testing-strategy.md`, `docs/deployment.md`, and `docs/release-readiness.md` for detailed requirements rather than duplicating them here.

## Safety boundaries

- Never expose or commit `.env` values, OAuth credentials, JWT secrets, database URLs, API keys, or callback codes.
- Do not push, merge, deploy, mutate production secrets, or alter production data unless explicitly requested.
- Inspect the current diff before editing files with existing changes — preserve unrelated tracked, untracked, and user-authored work.
- Do not claim a migration, release, authentication flow, or browser smoke test succeeded without current evidence.
