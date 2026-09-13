# Frontend-Tester Instructions — NFL Confidence (2026-09-12 session, updated)

Hand this document to the `frontend-tester` agent as its checklist. It covers
everything changed in this session, split into what's **live and testable
right now** on the dev deployment, and what's **not deployed yet** (so don't
report those as failures — they can't pass until they're merged/deployed).

**Update since this doc was first written**: the scoring/leaderboard fix
(originally Part B1 below, "not yet merged") has since been merged and
deployed to **both** dev and production (PR #18, plus a follow-up prod
migration-history fix in PR #19 that was blocking prod deploys generally).
It has moved into Part B below as a live, testable item. Only the stashed
frontend/mobile UI fixes (Part C) remain undeployed.

## Target

- Primary: `https://nfl-confidence-web-dev.fly.dev` (dev frontend)
- API: `https://nfl-confidence-api-dev.fly.dev` (dev backend — for direct
  health/readiness checks only, not for driving the browser against)
- This is the **dev** environment, safe to click through with test data —
  it has its own database, separate from production.

---

## Part A — Live now: dev environment infrastructure

This session stood up the dev deployment itself. These checks verify the
infrastructure is actually correct, not just "up."

1. **Dev talks to dev, not prod.** Open `https://nfl-confidence-web-dev.fly.dev/`.
   Open browser dev tools → Network tab. Trigger any API call (e.g. load the
   page, which calls session bootstrap). Confirm the request goes to a path
   like `/api/v1/...` on the same origin (`nfl-confidence-web-dev.fly.dev`),
   and that the response doesn't contain production league/user data you
   don't recognize. **Why this matters**: a bug earlier in this work would
   have made the dev frontend silently proxy to the *production* API — this
   check exists specifically to catch that class of bug if it ever
   regresses.
2. **Health/readiness.** `GET https://nfl-confidence-api-dev.fly.dev/api/v1/health/ready`
   should return `200` with a JSON body reporting `"status":"ready"`,
   `"database":"healthy"`, `"scheduler":"running"`.
3. **Sign-in and session persistence.** Sign in with Google. Confirm the
   browser returns to the frontend and a page refresh preserves the
   session (still signed in, no re-login prompt). In a private/incognito
   window, confirm the post-login request goes to
   `https://nfl-confidence-web-dev.fly.dev/api/v1/auth/refresh` and that
   the refresh cookie is `HttpOnly`.
4. **League + invite flow.** As commissioner, create a league (name it
   something obviously a test, e.g. "QA Test League"), send an invite,
   accept it with a second Google account, confirm both members appear in
   the member list.
5. **Import a week's schedule** (dev's database starts empty). This
   requires shell access to the dev machine, not the browser:
   `fly ssh console --app nfl-confidence-api-dev -C "python -m app.jobs.nfl_schedule --season 2026 --week 1"`.
   If you don't have `fly` CLI access, skip this and report it as
   `BLOCKED` rather than guessing — everything downstream (picks, standings)
   depends on this data existing.
6. **Submit picks.** Submit a complete set of picks for the imported week.
   Confirm `GET /api/v1/weeks/current` (visible in Network tab) reports the
   earliest kickoff in `locksAt`, and that the Picks page reflects the
   saved selections after a page reload.
7. **Pick locking.** This one you likely can't wait for in real time —
   report as `BLOCKED` with a note unless the imported week happens to have
   a game kicking off during your test window. If it does: confirm the UI
   goes read-only after that kickoff and a direct `POST /api/v1/picks`
   call is rejected.
8. **Mobile viewport.** Resize to a mobile width (375px) and re-check items
   3, 4, and 6 above. Confirm no horizontal page scroll, the header's Sign
   Out button is reachable without scrolling, and the Picks page's sticky
   progress bar doesn't overlap the app's top nav bar.
9. **Console/network hygiene** (do this throughout, not just once): note
   any JavaScript console errors or failed (4xx/5xx, excluding expected
   auth 401s that trigger a refresh) network requests you see while doing
   the above. A clean run should have none.

---

## Part B — Live now: scoring/leaderboard fix (backend, merged and deployed)

**Status**: merged to `main` and `develop`, deployed to **both** production
(`nfl-confidence-api.fly.dev` / `nfl-confidence-web.fly.dev`) and dev
(`nfl-confidence-api-dev.fly.dev` / `nfl-confidence-web-dev.fly.dev`) as of
2026-09-12. A separate, pre-existing production migration-history drift bug
that was blocking *all* prod deploys (unrelated to this fix, but discovered
while shipping it) was also fixed and deployed. Test this against **dev**
per this doc's Target section — dev's database starts empty, so item 10
below (importing/playing out a week) is a prerequisite for items 11-15.

**The bug this fixes**: standings, the weekly leaderboard, and individual
pick outcomes stopped updating. Root cause: the app's notion of "the
current NFL week" was tied to a date window that closed the instant the
week's last game kicked off (using kickoff time, not finish time), so that
game's final score was never re-synced — leaving its picks unscored
forever, the week never reaching "complete," and season standings (which
only count complete weeks) permanently empty. The weekly leaderboard kept
updating for earlier games but always fell short by whatever the last
game was worth.

**Now that this is deployed, test:**

10. Import and let a full week play out (or manually trigger sync after
    games finish — commissioner tools or `fly ssh console --app
    nfl-confidence-api-dev -C "python -m scripts.run_job sync"`).
11. Confirm **every** game's pick shows a resolved outcome (Correct/
    Incorrect) on the Profile pick-history page — including the last game
    of the week, not just the earlier ones.
12. Confirm the weekly leaderboard's point totals include that last game
    for every member (compare a member's total against a manual sum of
    their picks' points).
13. Confirm season standings (`/api/v1/leaderboard/season` — the Standings
    page) shows non-empty data after at least one full week completes. Before
    this fix, this would stay empty indefinitely.
14. Re-run a sync a second time and confirm totals/standings don't change
    (idempotency).
15. As commissioner, open `/api/v1/admin/jobs/status` (or wherever this is
    surfaced in the UI, if anywhere yet — currently it may only be reachable
    as a raw API call) and confirm it shows the scheduler's actual recent
    runs (job names like `sunday_score_sync`, `overnight_score_sync`) with
    real timestamps, not "never run" for everything.

---

## Part C — NOT deployed yet: verify only after unstash (report as N/A for now)

### C1. Frontend UI/mobile fixes (stashed, not committed, not deployed)

These were intentionally **not** deployed — the user asked to stash them
rather than ship them for now. Listed here so they're not forgotten and so
this checklist covers them whenever they do land:

16. **Pick outcome color**: "Correct" picks on the Profile history page
    should render in green (accent color), not default/black text.
17. **Loading states**: navigating between pages, or the initial auth
    check, should show a spinner — not a blank white flash.
18. **Error messages**: a failing "Create League," "Join League," invite,
    payment-toggle, void-picks, or member-update action should show the
    server's actual error message (e.g. "A league already exists...") —
    not a generic "please try again" for every failure type.
19. **Confirm dialogs**: "Void unpaid picks" and "Remove member" should
    show an in-app confirm dialog, not the browser's native `confirm()`
    popup.
20. **Touch targets**: the payment-admin week selector and "Paid" checkbox
    row should be at least 44px tall (comfortably tappable on mobile).
21. **Accordion sections on the dashboard** (Picks/Leaderboard/Standings/
    Profile) should **not** flash a loading state every time you re-open a
    section you'd already opened once in the same visit — collapsing
    should hide it, not tear it down.
22. **Mobile header**: on a 360-390px-wide phone, the Sign Out button
    should be reachable without needing to scroll the nav bar horizontally.
23. **Tables** (Leaderboard, Standings, Profile history) on mobile should
    show a subtle fade on the right edge hinting there's more to scroll to,
    and alternating row shading.
24. **Picks page on mobile**: the sticky progress header should sit
    visibly below the app's top nav bar, never overlapping/hidden behind
    it, when scrolling.

---

## Report format

For each numbered item above: `PASS` / `FAIL` / `BLOCKED` / `N/A (not deployed yet)`,
with concrete evidence (what you saw, a status code, a console error, a
screenshot description). Group Part A, Part B, and Part C separately in the
report. Flag any console error or failed network request you noticed under a
separate "Console/Network Issues" heading even if not tied to a specific
numbered item.
