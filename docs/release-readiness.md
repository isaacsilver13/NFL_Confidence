# Release Readiness

## Scope

This release packages the previously uncommitted NFL Confidence changes into
small, dependency-ordered pull requests. The implementation includes:

- active-league authorization for league-scoped API routes
- invite recipient email binding and escaped invite HTML
- week-level pick locking at the earliest kickoff
- idempotent weekly scoring and uniqueness protection
- database-backed job execution records and admin job controls
- session bootstrap and health/readiness endpoints
- local team logo assets with an accessible badge fallback
- Fly.io API and frontend deployment configuration

## Scheduler ownership

Production uses the embedded APScheduler in the FastAPI API process. The API Fly
configuration runs one always-on machine and sets `ENABLE_SCHEDULER=true`. It
does not declare the older standalone worker process, so only one scheduler
implementation owns recurring imports, locks, score syncs, and reminders.

The admin job endpoints and `scripts/run_job.py` remain available for controlled
manual retries. Do not scale the API horizontally until the scheduler is moved
to a dedicated singleton worker or another platform-managed one-at-a-time
execution model.

## Logo assets

The frontend uses one authoritative path: `/logos/<ESPN_CODE>.png`. The
`TEAM_LOGOS` manifest and `TeamLogo` component own the mapping and render an
abbreviation badge if an image cannot load. The duplicate long-name asset tree
and its copy script were removed so runtime code and packaged assets cannot
drift.

NFL team marks remain the property of their respective owners. The assets are
included for the private pool UI and are not an endorsement or affiliation.
Verify redistribution and branding requirements before turning the deployment
into a public or commercial product.

## Validation completed

Backend:

- `119 passed` with pytest
- Ruff clean
- Black check clean
- isort check clean
- mypy clean

Frontend:

- 42 tests passed
- ESLint clean
- Prettier check clean
- production build clean

## Deployment gate

Before deployment from merged `main`:

1. Apply Alembic migrations against the target PostgreSQL database.
2. Set `JWT_SECRET`, OAuth, email, database, `APP_URL`, and exact CORS secrets in Fly.
3. Deploy the API and verify `/api/v1/health` and `/api/v1/health/ready`.
4. Confirm readiness reports a healthy database and a running scheduler.
5. Deploy the frontend and verify the root page loads and logo requests return 200.
6. Run the invite, pick-lock, score-sync, and reminder smoke checks in
   `deployment.md`.

A deployment must not proceed if the production JWT secret is still the local
default, migrations fail, readiness is 503, or the logo asset rights are not
acceptable for the intended audience.
