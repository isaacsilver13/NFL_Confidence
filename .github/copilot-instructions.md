# NFL Confidence Copilot Instructions

## Project boundary

This repository contains the NFL Confidence FastAPI backend, React frontend, PostgreSQL/Alembic schema, background jobs, and deployment documentation. Keep backend changes under `backend/` and frontend changes under `frontend/` unless the request names another boundary.

## Runtime and architecture

- Backend validation uses Python 3.10 from `backend/.venv`; Python 3.14 is not a supported substitute for this project.
- Local PostgreSQL is Docker Compose-backed. Use `backend/scripts/prepare_local.ps1` or the `NFL Confidence: Prepare database and seed test data` task for migration and deterministic seed setup.
- Backend flow is routes -> services -> repositories -> models. Frontend flow is pages/components/hooks -> API client -> backend routes.
- Alembic migrations are the database source of truth. Do not edit an applied migration to change schema history.

## Validation

- Use `backend/scripts/verify.ps1` or the `NFL Confidence: Verify` task for the CI-equivalent backend and frontend checks.
- For a focused change, run the narrowest relevant backend test, frontend test, type check, or build first. Keep pre-existing failures separate from failures introduced by the current change.
- Consult `docs/technical-architecture.md`, `docs/testing-strategy.md`, `docs/deployment.md`, and `docs/release-readiness.md` for detailed requirements instead of copying them into this file.

## Safety boundaries

- Never expose or commit `.env` values, OAuth credentials, JWT secrets, database URLs, API keys, or callback codes.
- Do not push, merge, deploy, mutate production secrets, or alter production data unless the user explicitly requests that operation.
- Preserve unrelated tracked, untracked, and user-authored work. Inspect the current diff before editing files with existing changes.
- Do not claim a migration, release, authentication flow, or browser smoke test succeeded without current evidence.
