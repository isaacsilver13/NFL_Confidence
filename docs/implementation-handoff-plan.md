# NFL Confidence Pool implementation handoff plan

> Historical design plan. Production currently uses the single-machine
> embedded scheduler documented in [release-readiness.md](release-readiness.md).

Prepared: 2026-09-02  
Source review: [code-review-2026-09-02.md](code-review-2026-09-02.md)

## Objective

Make the current single-league NFL Confidence Pool safe and reliable in production, restore its promised per-game pick flow, add real team logos, and reduce the common-page runtime cost without expanding into a multi-league redesign.

## Assumptions and decisions needed before work starts

This plan assumes the intentional v1 scope remains one active league. If multiple independent pools are a near-term requirement, stop after the authorization/work-runner fixes and redesign league selection and tenancy before implementing product features.

The engineering owner must choose one production job platform before Phase 1:

1. **Recommended:** a dedicated, single worker/cron process with a PostgreSQL advisory lock or durable job-run records.
2. An external scheduler that invokes authenticated job endpoints or runs `backend/scripts/run_job.py` on schedule.

The API service must not run its own scheduler in production. The chosen platform must provide retries, logs, alerting, and one-at-a-time execution.

The product owner must also approve a team-logo source and usage rights. The default implementation in this plan uses a licensed/vetted local asset set of 32 compact images.

## Workstreams and handoff tickets

### Phase 0 — establish a reliable baseline

**Owner:** backend/platform engineer  
**Dependencies:** none  
**Goal:** make local and CI results trustworthy before security or behavior changes.

Tasks:

1. Recreate `backend/.venv` from the pinned `requirements.txt` using the project-supported Python version. Align `pyproject.toml`, Docker, documentation, and CI on that version; do not upgrade Python as part of this ticket.
2. Run backend lint, format, type checks, and tests against local PostgreSQL or Docker Compose. Record the command sequence in the repository README or developer documentation.
3. Run Prettier on the existing frontend baseline in a dedicated formatting-only change, then require `npm run format:check` to pass. Do not combine this mechanical change with product work.
4. Add CI artifacts for backend coverage and frontend test output. Threshold enforcement belongs in Phase 5 after missing critical tests are added.

Acceptance criteria:

* Local setup has one documented command path that runs the complete backend test suite.
* The existing CI workflow is green, including frontend format check.
* No production behavior changes are included in this phase.

### Phase 1 — secure the private-league boundary and restore production jobs

**Owner:** backend/platform engineer  
**Dependencies:** Phase 0, job-platform decision  
**Goal:** make "invite-only" true in the API and make automation actually execute in production.

#### Ticket 1A: active-league membership authorization

Implement a single dependency/service that resolves the active league and verifies the authenticated user's `LeagueMember` row. It should return the league and membership, or raise a 403 without revealing league details.

Apply it to all league-scoped routes:

* league summary and member list;
* current/week games and weeks;
* current picks and pick history;
* weekly leaderboard, season standings, and pick breakdown;
* pick creation.

Keep league creation and invitation joining as intentional exceptions. Preserve the commissioner-specific owner check for invitation creation.

Tests:

* non-members receive 403 for every league-scoped route;
* active members can read and submit picks;
* a non-member cannot create a pick;
* the existing owner/member flows continue to work.

#### Ticket 1B: bind invitations to the intended account

Before accepting an invite, compare normalized `Invite.email` and authenticated `User.email`. Reject a mismatch without consuming the invite. Escape dynamic invitation HTML fields as part of this ticket.

Tests:

* matching email succeeds;
* a different email receives a failure and the intended user can still accept;
* expired, reused, and concurrent invite cases remain correct.

#### Ticket 1C: deploy and observe the job runner

Create the chosen job process/schedule for:

* next-week schedule import;
* current-week ESPN synchronization and scoring;
* pick locking;
* weekly reminders.

Use the existing callable job functions initially; do not rewrite the domain logic. Add one global execution lock per job/run window and structured logs with job name, season/week, duration, import count, score count, and error outcome. Keep `ENABLE_SCHEDULER=false` in the web API deployment.

Add a readiness/operational endpoint or monitoring query that reports the most recent successful schedule sync. Alert when it is stale during the NFL season.

Acceptance criteria:

* An automated staging run imports a week, synchronizes a final game, recalculates standings, and writes a single delivery record for a reminder.
* Retrying or overlapping a job does not duplicate results or emails.
* Production configuration has a documented owner and recovery procedure for failed jobs.

### Phase 2 — correct game-level locking and score materialization

**Owner:** backend engineer, frontend engineer  
**Dependencies:** Phase 1 authorization  
**Goal:** let members edit future games while protecting started games and harden derived scoring rows.

#### Ticket 2A: per-game pick locking

Replace the all-week deadline in `picks_service.create_picks` with game-level validation. A submission may create/update only games with kickoff after server time. Started games retain their existing pick; users may continue to save future games.

Define the card validation rule before implementation: the recommended rule is that a member may save a partial editable card, but confidence values must be unique across both saved locked picks and editable picks. The API must return enough state for the client to explain blocked selections.

Update the Picks page to disable only started game controls, show a per-game locked state, and retain the existing server error display. Do not trust browser time for authorization; it is display-only.

Tests:

* Thursday game locks while Sunday/Monday games remain editable;
* a member cannot modify a started game;
* confidence values remain unique across locked and editable games;
* server time, not browser time, is authoritative;
* simultaneous final submissions preserve a valid card.

#### Ticket 2B: make result rows concurrency-safe

Add an Alembic migration with a unique constraint on `weekly_results(league_id, week_id, user_id)`. Audit and remove/merge duplicates before applying the constraint in any environment with data. Change scoring to use an upsert or safe locking strategy. Review and add query-specific composite indexes only after inspecting PostgreSQL query plans.

Tests:

* two simultaneous scoring attempts leave one weekly result per member/week;
* repeated score runs remain idempotent;
* existing season-result behavior remains unchanged.

Acceptance criteria:

* The documented weekly flow works across Thursday through Monday games.
* Database constraints protect result uniqueness independently of application code.

### Phase 3 — add resilient team logos

**Owner:** frontend engineer  
**Dependencies:** logo rights/source approval  
**Goal:** replace abbreviation-only badges with real, fast, reliable team marks.

Tasks:

1. Store 32 optimized assets under `frontend/src/assets/nfl-teams/` or `frontend/public/nfl-teams/`, with a short provenance/license record in the same directory or docs.
2. Create a typed abbreviation-to-asset manifest for the exact ESPN abbreviations. Include all teams, including `ARI`, `ATL`, `CAR`, `CLE`, `DEN`, `DET`, `HOU`, `IND`, `JAX`, `LAC`, `LAR`, `LV`, `MIA`, `MIN`, `NE`, `NO`, `NYG`, `NYJ`, `PIT`, `TB`, `TEN`, `WAS`, and the ten currently styled teams.
3. Change `TeamLogo` to resolve the manifest internally. Render a sized image with `decoding="async"`; lazy-load only images not initially visible. On a failed load or unknown code, use the current abbreviation badge.
4. Keep image `alt` empty where the adjacent label already names the team; use meaningful text only when the logo is displayed alone.
5. Use the upgraded component in every matchup/pick-breakdown surface; do not add individual external image fetches to cards.

Tests:

* manifest covers all 32 codes;
* known code renders the expected asset;
* unknown and failed images render the abbreviation fallback;
* the logo component preserves current accessibility behavior.

Acceptance criteria:

* A fresh picks page displays local/cached logos for all NFL teams with no runtime dependency on ESPN images.
* No layout shift occurs when images load.

### Phase 4 — improve the common runtime path

**Owner:** frontend engineer with backend support  
**Dependencies:** Phases 1–3 may be delivered independently; measure each change  
**Goal:** improve actual user-perceived load time without premature backend rewrites.

#### Ticket 4A: route-level code splitting

Convert non-critical pages to lazy imports with a small shared loading fallback. Start with Standings (which brings Recharts), Profile, League Settings, and Join. Keep authentication and Picks straightforward unless measurement shows they need splitting.

Record baseline and post-change production bundle sizes. Confirm deep links still work and all lazy-load errors have a reasonable user-facing fallback.

#### Ticket 4B: efficient session bootstrap

Expose an explicit client refresh function. On initial app load, refresh the session once and then request `/auth/me`; do not intentionally send `/auth/me` without a bearer token first. Preserve the existing single-flight refresh behavior for concurrent 401s.

Tests:

* valid returning session uses one refresh plus one `/me` request;
* no-cookie session resolves to logged out without an infinite retry;
* 401 during an ordinary request refreshes once and retries once.

#### Ticket 4C: current pick-card endpoint

Add a read endpoint that returns the current week, games, user picks, and each game's server-side lock state in one response. Move the Picks page to one TanStack Query key. Retain current endpoints until callers have migrated, then remove only through a planned compatibility change.

Measure:

* transfer size and number of requests for first visit to Picks;
* p50/p95 API latency for the new endpoint;
* LCP/INP or equivalent browser timing on a production-like connection.

Acceptance criteria:

* The Picks page makes one data request for its initial card state.
* The initial bundle and real page metrics improve relative to the recorded baseline.
* No performance claim is accepted without before/after data.

### Phase 5 — quality gates and release

**Owner:** QA/engineering owner  
**Dependencies:** Phases 1–4  
**Goal:** prevent regressions in privacy, scoring, and weekly usability.

Tasks:

1. Add API tests for membership authorization, recipient-bound invitations, per-game locking, concurrent scoring, and job idempotency.
2. Add Playwright (or equivalent) browser coverage for login/session restoration, invitation acceptance, complete confidence-card submission, a Thursday-lock/Sunday-edit path, and team-logo fallback.
3. Configure coverage reporting and introduce thresholds at or below the newly measured baseline. Ratchet them upward rather than immediately enforcing the aspirational 90%/80% numbers.
4. Add a staging deployment checklist: migration applied, worker scheduled, job freshness visible, manual retry tested, and alert recipient confirmed.
5. Release in this order: migration/authorization → worker → per-game locks → logos → runtime changes. Roll back application deployments independently from database migrations whenever possible.

Release acceptance criteria:

* Unauthorized private-league access is blocked.
* A production-like job run completes and is observable.
* Pick locking behaves per game.
* All logo and critical user-flow tests pass.
* CI is green, including formatting and the agreed coverage gates.

## Suggested ownership and sequencing

| Deliverable | Primary owner | Reviewers | Can run in parallel |
| --- | --- | --- | --- |
| Phase 0 baseline | Backend/platform | Frontend | No — establishes confidence |
| 1A/1B authorization | Backend | Security/QA | 1C after deployment decision |
| 1C job runner | Platform/backend | Operations | 1A/1B |
| Phase 2 locking/results | Backend + frontend | QA | Starts after 1A |
| Phase 3 logos | Frontend | Product/design | Any time after source approval |
| Phase 4 performance | Frontend + backend | QA | After baseline metrics; logos can overlap |
| Phase 5 release gates | QA/engineering | All owners | Begins alongside each phase |

## Handoff checklist

* [ ] Confirm single-league scope or authorize a tenancy redesign.
* [ ] Select the production job platform and on-call owner.
* [ ] Approve a logo source and usage rights.
* [ ] Assign an owner for each Phase 1 ticket before feature work begins.
* [ ] Capture baseline bundle, API, and browser performance metrics.
* [ ] Create separate pull requests per ticket; keep formatting-only and migration changes isolated.
* [ ] Require the acceptance criteria and tests in each ticket before merging.

