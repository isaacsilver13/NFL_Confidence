# Front-end Polish and Per-Game T-Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the per-game picks T-chart plus the phone-layout fixes from the 2026-11-02 front-end review, all in one branch and one PR to `develop`.

**Architecture:** Frontend-only. No backend or schema change: `GET` game picks already returns `picks[]` (`memberName`, `team`, `confidence`, `isCorrect`) ordered by `confidence_value DESC` (`backend/app/services/leaderboard_service.py:638`). Each task edits a different component, so tasks are independent and can land in any order; the T-chart goes first because the user asked for it.

**Tech Stack:** React 18 + TypeScript, Tailwind (`dark:` and `dev-dark:` class pairs), React Query, Vitest + Testing Library, Playwright.

**Spec:** This conversation. User requests: per-game popup becomes a T-chart (two teams either side, each picker with points, descending by points). "That's all good" on the review list, "do everything in one shot".

## Global Constraints

- Work on a branch cut from `develop` (which already has everything on prod). Open the PR into `develop`. Merging is the user's call; the PR deploys dev only.
- Colors: copy the existing paired classes (`text-ink-muted dark:text-slate-400 dev-dark:text-text-muted` etc.). Do not introduce CSS variables (review item 7 is deliberately out of scope, see Not In This Plan).
- Every new interactive element keeps a 44px touch target (`min-h-11`, as `Button` does) and a text label for screen readers; correct/wrong is never conveyed by color alone (keep the ✓/✗ plus `sr-only` pattern from `AllPicksModal.tsx` `PickCell`).
- Verify at 375px and 1280px widths in the built-in browser against the local seed (`backend/scripts/prepare_local.ps1`, dev-login needs Google/Resend env blanked via the launcher in the session scratchpad).
- Close-out checks: `npm run lint`, `npm run format:check` (see Task 8 for the Windows caveat), `npm run test`, `npm run build`.

## Review Focus

- A game where every pick is on one team: the empty side must say "No picks", not render blank or crash.
- Two members with equal points on the same team: order must be stable (tie-break by name), not jump between refetches.
- Game with `isCorrect: null` (not final): no ✓/✗ and no color, only the number.
- Long display names on a 375px screen: names truncate/wrap inside their half, never push the chart sideways.
- Commissioner with Refresh: after Task 4 reorders buttons the Refresh button must still be absent for non-owners.

## File Structure

| File | Change |
|---|---|
| `frontend/src/components/leaderboard/WeeklyPickBreakdown.tsx` | Replace flat list in `GamePicksModal` with `GamePicksTChart` |
| `frontend/src/components/leaderboard/WeeklyPickBreakdown.test.tsx` | Update modal test, add T-chart tests |
| `frontend/src/pages/LeaderboardPage.tsx` (`LeaderboardTable`) | Phone layout: sticky Rank/Member, Points beside them |
| `frontend/src/layouts/AppLayout.tsx` | Phone nav: nothing clipped, Sign out and theme reachable |
| `frontend/src/pages/DashboardPage.tsx` (`DashboardHeader`) | "Make picks" first and primary |
| `frontend/src/pages/PicksPage.tsx:718-723` | Empty state with guidance |
| `frontend/src/components/leaderboard/AllPicksModal.tsx` | Loading text in member view; game filter for the everyone grid |
| `frontend/e2e/*.spec.ts`, `frontend/playwright.config.ts` | Add a desktop project |
| `.gitattributes` (new, repo root) | Stop CRLF churn in Prettier |

---

### Task 1: Per-game picks T-chart

**Files:**
- Modify: `frontend/src/components/leaderboard/WeeklyPickBreakdown.tsx` (the `GamePicksModal` body, lines ~49-88)
- Test: `frontend/src/components/leaderboard/WeeklyPickBreakdown.test.tsx`

**Interfaces:**
- Consumes: `GamePicks` / `GamePickDetail` from `@/types/leaderboard` (unchanged); `TeamLogo`, `getTeamPalette` already imported in this file.
- Produces: `function GamePicksTChart({ data }: { data: GamePicks }): JSX.Element` (module-private) and `function sortSidePicks(picks: GamePickDetail[]): GamePickDetail[]` (module-private; confidence descending, then `memberName` ascending via `localeCompare`).

Layout decisions (fixed, so the implementer does not choose): two equal columns under a header row, away team left and home team right (matches the "AWAY at HOME" title). Header cell per side: `TeamLogo` (decorative), team code, and `N picks`. Under each header an ordered list (`<ol>`) of `memberName` on the left and the confidence number on the right, bold, colored by `isCorrect` as today (accent / danger / muted). Add `sr-only` text "Correct" / "Wrong" after the number. Empty side shows "No picks". Modal widens from `max-w-md` to `max-w-lg`. The list scrolls inside the existing `max-h-96 overflow-y-auto` wrapper; the header row stays sticky at the top of that wrapper. Keep the existing loading, error, and "No picks were submitted for this game." states.

- [ ] **Step 1: Write failing tests** in `WeeklyPickBreakdown.test.tsx`. Replace the final test's assertions on `CHI (5)` / `GB (3)` and add:
  - `it('splits picks into a column per team, highest points first')`: mock picks `[Alex CHI 5 true, Sam GB 3 false, Jo CHI 9 true, Kim GB 7 false]`; open the modal; assert the CHI list (`within(screen.getByRole('list', { name: 'CHI picks' }))`) reads `Jo 9, Alex 5` in order and the GB list reads `Kim 7, Sam 3`.
  - `it('breaks equal points by member name')`: Zed CHI 4 and Amy CHI 4 render Amy then Zed.
  - `it('shows "No picks" for a team nobody picked')`: all picks on CHI; GB list shows `No picks`.
  - `it('marks correct and wrong picks for screen readers')`: Alex's number is followed by an `sr-only` "Correct", Sam's by "Wrong", and a pick with `isCorrect: null` has neither.
- [ ] **Step 2: Run to confirm they fail:** `npx vitest run src/components/leaderboard/WeeklyPickBreakdown.test.tsx` → FAIL (lists named "CHI picks" not found).
- [ ] **Step 3: Implement `GamePicksTChart` and `sortSidePicks`** per the layout decisions above. Each `<ol>` gets `aria-label={`${team} picks`}`. Split picks with `filter` on `pick.team === game.awayTeam / homeTeam`.
- [ ] **Step 4: Run to confirm they pass:** same command → PASS.
- [ ] **Step 5: Browser check** at 375px and 1280px with a seeded revealed week: both columns visible without horizontal scroll, descending order, long name wraps. Take a screenshot of each.
- [ ] **Step 6: Commit** `feat: show per-game picks as a two-team T-chart`.

### Task 2: Weekly leaderboard readable on phones (review item 1)

**Files:**
- Modify: `frontend/src/pages/LeaderboardPage.tsx` (`LeaderboardTable`)
- Test: `frontend/src/pages/LeaderboardPage.test.tsx`

**Interfaces:** Consumes `SortableTh` (`className` prop already used). Produces nothing new.

Decision: keep the table (sorting and tests depend on it) but make the first columns sticky: Rank and Member `sticky left-0` with an opaque background matching the row/hover color, and move **Points** to sit immediately after Member (order becomes Rank, Member, Points, Correct, Points Left, Max Points, SNF/MNF). Reduce `min-w-[680px]` padding on phones (`px-3 sm:px-5`). Points being third means it is visible on a 375px screen without scrolling.

- [ ] **Step 1: Failing test** `it('lists Points directly after Member')`: assert header order `['Rank','Member','Points','Correct','Points Left','Max Points']` (existing tests may assert the old order; update them in the same step).
- [ ] **Step 2: Run** `npx vitest run src/pages/LeaderboardPage.test.tsx` → FAIL.
- [ ] **Step 3: Implement** the column reorder and sticky classes in both `<thead>` and `<tbody>`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Browser check at 375px:** Rank, Member and Points all visible with no scrolling; scrolling right keeps Rank/Member pinned and text is not overlapped (sticky cells opaque in light, dark and dev-dark themes).
- [ ] **Step 6: Commit** `feat: keep rank, member and points visible on phones`.

### Task 3: Phone navigation (review item 2)

**Files:**
- Modify: `frontend/src/layouts/AppLayout.tsx` (the `<nav>`, line 49)
- Test: `frontend/src/layouts/AppLayout.test.tsx` (create if absent; check with Glob first)

Decision: no menu component. On screens below `sm`, show Sign out and the theme toggle as icon-only buttons (hide the "Sign out" text with `hidden sm:inline`, keep `aria-label="Sign out"`), shrink the logo margin, and let the nav links row wrap instead of `overflow-x-auto` clipping (`flex-wrap`). Goal: every link, the theme toggle and Sign out are visible at 375px with no horizontal scroll, for both member and commissioner.

- [ ] **Step 1: Failing test** `it('keeps Sign out reachable by its accessible name')`: `getByRole('button', { name: 'Sign out' })` exists (fails because the name currently comes from visible text only if icon-only; this pins the label so the visual change cannot drop it). Add `it('shows Members only to commissioners')`.
- [ ] **Step 2: Run** → FAIL on the aria-label case.
- [ ] **Step 3: Implement** the class and label changes.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Browser check at 375px as commissioner (most links):** nothing clipped, no horizontal page scroll (`document.documentElement.scrollWidth <= innerWidth` via the browser JS tool).
- [ ] **Step 6: Commit** `fix: make top nav fit phone screens`.

### Task 4: Dashboard header order (review item 4)

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx` (`DashboardHeader`, lines ~404-422)
- Test: `frontend/src/pages/DashboardPage.test.tsx`

Decision: render "Make picks" first with `variant="primary"`, then Refresh (stays `secondary`, commissioner-only). Change `navigate('/picks')` usage unchanged.

- [ ] **Step 1: Failing test** `it('puts Make picks before Refresh for commissioners')`: `screen.getAllByRole('button')` filtered to those two names has `Make picks` first. Existing "hidden from members" test must still pass.
- [ ] **Step 2: Run** `npx vitest run src/pages/DashboardPage.test.tsx` → FAIL.
- [ ] **Step 3: Implement** the swap and variant change.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: make Make picks the primary dashboard action`.

### Task 5: Picks page empty state (review item 5)

**Files:**
- Modify: `frontend/src/pages/PicksPage.tsx:718-723`
- Test: `frontend/src/pages/PicksPage.test.tsx`

Decision: replace the bare line with a heading "No picks open yet" and one sentence "Picks open once the next NFL week is loaded. Check back soon or ask your commissioner." Same muted color as other empty states, not `text-danger`. Do not change the error state at line 706.

- [ ] **Step 1: Failing test** `it('explains what to do when there is no current week')` asserting the heading and sentence (update any existing test asserting "No current week is available.").
- [ ] **Step 2: Run** `npx vitest run src/pages/PicksPage.test.tsx` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `fix: explain the empty picks state`.

### Task 6: Everyone's picks on phones and loading text (review items 3 and 6)

**Files:**
- Modify: `frontend/src/components/leaderboard/AllPicksModal.tsx`
- Test: `frontend/src/pages/LeaderboardPage.test.tsx` (existing modal tests live here)

Decisions:
- Member view loading text becomes `Loading picks…` (everyone view keeps `Loading everyone's picks…`); error text likewise.
- Everyone grid: add a `<select aria-label="Show game">` above the grid with options "All games" (default) and one per game (`AWAY @ HOME`). Choosing a game renders only that game's column (members stay as rows, still sticky first column). This is what removes sideways scrolling on a phone. Implement by filtering `data.games` before `PicksTable`; sorting columns still derive from the filtered list.

- [ ] **Step 1: Failing tests:** `it('says "Loading picks…" in the single-member popup')`; `it('narrows the everyone grid to one game')` (select a game, assert only that game's column header remains).
- [ ] **Step 2: Run** `npx vitest run src/pages/LeaderboardPage.test.tsx` → FAIL.
- [ ] **Step 3: Implement** the copy change and the game filter (local `useState<string>('all')` inside the everyone view).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Browser check at 375px:** with one game selected the grid fits without sideways scroll.
- [ ] **Step 6: Commit** `feat: filter everyone's picks by game; fix member loading text`.

### Task 7: Desktop e2e run and Prettier line endings (review items 8 and 9)

**Files:**
- Modify: `frontend/playwright.config.ts` (add `{ name: 'desktop-1280', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } } }` to `projects`)
- Create: `.gitattributes` at repo root containing `* text=auto eol=lf`
- Check: `frontend/e2e/dashboard.spec.ts`, `login.spec.ts` pass under the new project

- [ ] **Step 1:** Add the desktop project. Run `npm run test:e2e` per `docs/testing-strategy.md` preconditions → both specs pass on three projects. If a spec assumes a mobile layout, fix the assertion, not the project.
- [ ] **Step 2:** Add `.gitattributes`. Run `git add --renormalize .` and inspect `git status`: expect no content diffs if the repo is already LF. If it shows large rewrites, stop and ask rather than committing them.
- [ ] **Step 3:** `npm run format:check` → expect no warnings (before this it flagged 66 untouched files locally, likely CRLF).
- [ ] **Step 4: Commit** `chore: add desktop e2e project and enforce LF line endings`.

---

## Final verification and delivery

- [ ] `npm run lint`, `npm run format:check`, `npm run test`, `npm run build` from `frontend/` all clean; paste the pass counts in the PR body.
- [ ] Browser: screenshots at 375px and 1280px of leaderboard, member popup, game T-chart, everyone grid with game filter, dashboard header (commissioner and member), nav, empty picks state.
- [ ] Push branch, open PR into `develop`, bind it, read CI. `develop` merge auto-deploys dev; confirm `deploy-dev` green and `/api/v1/health` 200 on `nfl-confidence-web-dev`. Do not touch `main` or prod without explicit approval.
- [ ] Write the left-off note for the repo.

### Task 8: Dark-palette tokens replace `dark:` + `dev-dark:` pairs (review item 7)

Added after the user chose to include the refactor. Done as a strict no-visual-change refactor.

- `frontend/src/index.css`: 15 `--color-night-*` tokens in `@theme` (prod dark = Tailwind slate scale) and overridden in `html.dark.dev-theme` (Bears tokens).
- A codemod collapsed 250 `dark:X dev-dark:Y` pairs in 20 non-test `.tsx` files into one `dark:<night token>` class (for example `dark:text-slate-400 dev-dark:text-text-muted` became `dark:text-night-muted`). Irregular leftovers (alpha mismatches, unpaired `dark:`/`dev-dark:` classes) were left alone on purpose.
- Light-mode classes were not touched, so light mode cannot change.
- Verification: Playwright snapshot of computed colors (color, background, 4 borders, outline, text-decoration, fill, stroke) for every element on login, dashboard (all sections open), game-picks modal, everyone's-picks modal, member modal, `/picks` and `/league-settings`, in light / dark / dev-dark, at 1280px and 375px, plus the hover state of every interactive element. Baseline taken from the pre-refactor code, then after: 22,542 element-states, 0 differences. (Runs taken close to the dev-login rate limit were discarded as unreliable.)

## Not In This Plan

- Backend changes, tie-game enumeration in eliminations, and Monday-doubleheader outcomes: unchanged risks from the shipped work.

## Execution Notes (2026-11-02)

- Executed on branch `feat/frontend-polish-t-chart` cut from `develop` (7e2c15f). Not pushed.
- Task 2 reorders columns to Rank, Member, Points, Correct, Points Left, Max Points.
- Task 5 also handles the server's 404 for "no current week", which is where the red text really came from.
- Task 6 also drops the grid's `min-w-[640px]` when one game is shown (found in the browser).
- Task 7: a third e2e project exceeds the 30/hour dev-login limit if all three run together; `docs/testing-strategy.md` now says to run them separately.
- Pre-existing, not caused by this work: two desktop e2e tests (`pick and confidence buttons are comfortable tap targets`, `picks progress starts below navigation`) fail because the local seed has no open current week; they fail identically with the original `PicksPage.tsx`.

## Self-Review

- Spec coverage: T-chart (Task 1), review items 1-6 and 8-9 (Tasks 2-7); item 7 explicitly deferred with reason.
- Type consistency: only `GamePickDetail`/`GamePicks` (existing) and the two module-private helpers in Task 1.
- Weakest assumption: sticky table columns (Task 2) look right in all three themes; this is only provable in the browser, hence the screenshot step.
