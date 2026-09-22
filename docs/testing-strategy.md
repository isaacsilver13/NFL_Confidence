# Testing Strategy

Version: 1.0

---

# Philosophy

Automated tests are required for every feature.

---

# Backend

Unit Tests

Services

Repositories

Validation

Scoring

Leaderboard calculations

Integration Tests

API endpoints

Authentication

Database operations

Background jobs

---

# Frontend

Component Tests

Rendering

Validation

Loading states

Error states

Custom hooks

---

# End-to-End

Login

Join league

Submit picks

Edit picks

View leaderboard

Notification preferences

**Tool:** Playwright (`frontend/e2e/`), covering mobile viewports only for now (`mobile-390` at 390×844 and `mobile-375` at 375×667, per the 390px overflow requirement in `docs/ui-design-system.md`). Not yet wired into CI — run locally.

**Preconditions:**

1. `backend/scripts/prepare_local.ps1` has been run (starts Docker Postgres, applies migrations, seeds deterministic test data).
2. The backend is running locally with Google OAuth unconfigured (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` unset) so `/auth/dev-login` is enabled.
3. `npm run dev` is available — Playwright's `webServer` config starts it automatically if it isn't already running.

**Run:** `npm run test:e2e` (from `frontend/`).

**Note on rate limiting:** `/auth/dev-login` and `/auth/refresh` are limited to 30 requests/hour per IP (see `backend/app/api/auth.py`) — a real anti-abuse limit, not a test-only setting. The suite runs fully serially (`workers: 1` in `playwright.config.ts`) and signs in once per worker, reusing that session across all tests (`e2e/fixtures.ts`'s `authedPage`), since the refresh token is single-use and rotates on every call — sharing a saved session across parallel contexts breaks after the first use. A full run costs roughly 24 of the 30 requests, so back-to-back runs within the same hour can hit 429s; the limiter is in-memory, so restarting the backend process resets it.

---

# Performance Tests

Leaderboard

<500 ms

Dashboard

<1 second

Picks page

<1 second

---

# Regression Tests

Scoring

Confidence validation

Locking games

Authentication

Leaderboard ranking

---

# Coverage

Long-term target

- Backend: 90% line coverage
- Frontend: 80% line coverage

CI-enforced gate

- Backend: 77% line coverage
- Frontend: 77% statements, 68% branches, 75% functions, and 78% lines

The CI gate starts at the measured baseline and will be ratcheted upward over time
toward the long-term target. The backend baseline excludes the currently date-sensitive
pick-lock fixture failures until those tests are repaired.

---

# Manual Testing Checklist

Google login

Invite flow

Create picks

Edit unlocked picks

Locked games

Leaderboard

Weekly scoring

Season standings

Responsive layout

Dark mode
