# Frontend-Tester Instructions — NFL Confidence (updated 2026-09-13)

Hand this document to the `frontend-tester` agent as its checklist. Dev and
prod are running the same code as of this update (`develop` was fast-forwarded
to `main`'s tip on 2026-09-13). Test against **dev** unless a check
specifically says prod.

## Target

- Primary: `https://nfl-confidence-web-dev.fly.dev` (dev frontend)
- API: `https://nfl-confidence-api-dev.fly.dev` (dev backend — for direct
  health/readiness checks only, not for driving the browser against)
- This is the **dev** environment, safe to click through with test data —
  it has its own database (confirmed separate `DATABASE_URL` from prod),
  so nothing here can affect production data.

## Incident note (context, not a checklist item)

On 2026-09-13, production's database (an external Neon Postgres project)
was found empty during a leaderboard bug investigation and was restored
from a Neon point-in-time backup. Root cause is still under investigation
and looks Neon-side, not application code. Dev was unaffected (separate
database). If you see anything in prod with an unexpected `created_at`
around 2026-09-13 05:50–06:00 UTC, that's residue from this incident, not
a new bug — don't report it as one.

---

## Part A — Dev environment infrastructure

1. **Dev talks to dev, not prod.** Open `https://nfl-confidence-web-dev.fly.dev/`.
   Open browser dev tools → Network tab. Trigger any API call (e.g. load the
   page, which calls session bootstrap). Confirm the request goes to a path
   like `/api/v1/...` on the same origin (`nfl-confidence-web-dev.fly.dev`),
   and that the response doesn't contain production league/user data you
   don't recognize.
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
5. **Import a week's schedule**, if dev's database doesn't already have
   current-week data. This requires shell access to the dev machine, not
   the browser: `fly ssh console --app nfl-confidence-api-dev -C "python -m scripts.run_job sync"`.
   If you don't have `fly` CLI access, skip this and report it as
   `BLOCKED` rather than guessing — everything downstream (picks, standings,
   leaderboard) depends on this data existing.
6. **Submit picks.** Submit a complete set of picks for the current week.
   Confirm `GET /api/v1/weeks/current` (visible in Network tab) reports the
   earliest kickoff in `locksAt`, and that the Picks page reflects the
   saved selections after a page reload.
7. **Pick locking.** This one you likely can't wait for in real time —
   report as `BLOCKED` with a note unless a game happens to kick off during
   your test window. If it does: confirm the UI goes read-only after that
   kickoff and a direct `POST /api/v1/picks` call is rejected.
8. **Mobile viewport.** Resize to a mobile width (375px) and re-check items
   3, 4, and 6 above. Confirm no horizontal page scroll, the header's Sign
   Out button is reachable without scrolling, and the Picks page's sticky
   progress bar doesn't overlap the app's top nav bar.
9. **Console/network hygiene** (do this throughout, not just once): note
   any JavaScript console errors or failed (4xx/5xx, excluding expected
   auth 401s that trigger a refresh) network requests you see while doing
   the above. A clean run should have none.

---

## Part B — Regression: current-week resolution and scoring (fixed, stable)

**Status**: fixed and stable in production since 2026-09-12 — this is a
regression check, not a new-feature test. The original bug: standings, the
weekly leaderboard, and individual pick outcomes stopped updating once a
week's last game kicked off, because the app's notion of "the current NFL
week" was tied to kickoff time rather than finish time.

10. Import and let a full week play out (or manually trigger sync after
    games finish: `fly ssh console --app nfl-confidence-api-dev -C "python -m scripts.run_job sync"`).
11. Confirm **every** game's pick shows a resolved outcome (Correct/
    Incorrect) on the Profile pick-history page — including the last game
    of the week, not just the earlier ones.
12. Confirm the weekly leaderboard's point totals include that last game
    for every member (compare a member's total against a manual sum of
    their picks' points).
13. Confirm season standings (Standings page) shows non-empty data after
    at least one full week completes.
14. Re-run a sync a second time and confirm totals/standings don't change
    (idempotency).

---

## Part C — New: live current-week leaderboard and table cleanup (2026-09-13)

**Status**: merged and deployed to both dev and prod as of 2026-09-13.

15. **Live current week by default.** Open the Leaderboard tab without
    selecting anything. It should default to the current, possibly
    in-progress week (not force you to wait for a week to fully complete),
    and the week dropdown should label it "Week N — Live".
16. **Points Left column.** For the live week, confirm a member's "Points
    Left" equals the sum of confidence values on their picks for games
    that haven't finished yet. As games finish, Points Left should shrink
    and Points should grow correspondingly on the next sync.
17. **Week selector covers past weeks too.** The same dropdown should also
    list every completed week (without "Live"), and selecting one shows
    that week's final standings.
18. **Column set.** The Leaderboard table should show exactly: Rank,
    Member, Correct, Points, Points Left — in that order. Missed, Wins,
    and Payout columns should **not** appear (they were intentionally
    removed).
19. **Dark mode.** Switch to dark mode (or use system dark mode). The
    selected week's text in the dropdown should be clearly readable
    (light text on dark background) — this was previously unreadable
    (dark navy text on a near-black background).
20. **Standings tab unaffected.** Confirm the Standings tab (season
    standings) still only shows fully completed weeks — it should not
    show live/in-progress data. This behavior didn't change, so it's a
    regression check.
21. **No-data states.** If no week has any data yet at all (e.g. a brand
    new season before the first sync), the Leaderboard tab should show a
    message like "No weeks available yet." — not an endless loading
    spinner.

---

## Part D — Unverified: older stashed UI/mobile fixes

**Status**: unclear which of these have shipped. At least one (#22 below)
was independently confirmed already implemented in current code as of
2026-09-13 — don't assume the rest are still pending just because they're
listed here. Check each fresh rather than trusting old status labels.

22. **Pick outcome color**: "Correct" picks on the Profile history page
    should render in green (accent/success color), not default/black text.
    *(Confirmed implemented in current code as of 2026-09-13 — this should
    PASS; flag it if it doesn't.)*
23. **Loading states**: navigating between pages, or the initial auth
    check, should show a spinner — not a blank white flash.
24. **Error messages**: a failing "Create League," "Join League," invite,
    payment-toggle, void-picks, or member-update action should show the
    server's actual error message (e.g. "A league already exists...") —
    not a generic "please try again" for every failure type.
25. **Confirm dialogs**: "Void unpaid picks" and "Remove member" should
    show an in-app confirm dialog, not the browser's native `confirm()`
    popup.
26. **Touch targets**: the payment-admin week selector and "Paid" checkbox
    row should be at least 44px tall (comfortably tappable on mobile).
27. **Accordion sections on the dashboard** (Picks/Leaderboard/Standings/
    Profile) should **not** flash a loading state every time you re-open a
    section you'd already opened once in the same visit — collapsing
    should hide it, not tear it down.
28. **Mobile header**: on a 360-390px-wide phone, the Sign Out button
    should be reachable without needing to scroll the nav bar horizontally.
29. **Tables** (Leaderboard, Standings, Profile history) on mobile should
    show a subtle fade on the right edge hinting there's more to scroll to,
    and alternating row shading.
30. **Picks page on mobile**: the sticky progress header should sit
    visibly below the app's top nav bar, never overlapping/hidden behind
    it, when scrolling.

---

## Report format

For each numbered item above: `PASS` / `FAIL` / `BLOCKED` / `UNKNOWN (needs a fresh check)`,
with concrete evidence (what you saw, a status code, a console error, a
screenshot description). Group Part A/B/C/D separately in the report. Flag
any console error or failed network request you noticed under a separate
"Console/Network Issues" heading even if not tied to a specific numbered
item.
