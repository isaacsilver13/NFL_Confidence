# Leaderboard and picks-table improvements — 25 October 2026

Status: **built** (approved 2026-10-25; placing = top 3, ties neutral). Not committed, pushed, or deployed. No browser smoke check yet.

## What exists today

- `LeaderboardPage` renders `LeaderboardTable` from `GET` weekly leaderboard (`leaderboard_service.get_weekly_leaderboard`), refetched every 60s. Columns: Rank, Member, Correct, Points, Points Left, SNF/MNF.
- "See everyone's picks" opens `AllPicksModal`, backed by `GET /picks/all/current?week=N` (`picks_service.get_all_picks_for_week`). It lists **every** league member, renders `TEAM (conf)` as plain text, and fetches once (`staleTime` 60s, no polling).
- The leaderboard already hides members without a submitted/complete card (`week_submission ∪ list_complete_card_user_ids`). The all-picks endpoint does not.
- The all-picks payload already carries each game's `status`, `winningTeam`, and `isTie`, so pick correctness can be derived on the client with no schema change.
- `pointsRemaining` (sum of confidence on unresolved, non-voided picks) is already on each leaderboard member.

## Changes

### 1. Color-code the picks table (green = correct, red = wrong), live
- `AllPicksModal.tsx`: per cell, outcome = game final and not a tie → `pick.team === game.winningTeam` ? correct : incorrect. Live, scheduled, tied, and cancelled games stay neutral.
- Style with the existing `accent` (green) and `danger` (red) tokens as a light tint plus colored text, e.g. `bg-accent/10 text-accent` and `bg-danger/10 text-danger`; check all three themes (light, `dark:`, `dev-dark:`).
- Not color-only: add a small ✓/✗ glyph with sr-only text ("correct"/"wrong") so it reads for color-blind users and screen readers.
- Live updates: add `refetchInterval: 60_000` to the modal query, stopping once every game is final. This matches the leaderboard's cadence; scores arrive via the existing tick job.
- Shared helper `pickOutcome(pick, game)` in a small module next to the modal so the member popup reuses it.

### 2. Member picks popup from the leaderboard
- Make each leaderboard member name a button (keyboard-accessible) that opens the same `AllPicksModal` with a `memberId` prop. It filters `data.members` to that one member and titles the dialog "<Name>'s picks — Week N".
- Reuses the `['picks','all',week]` query, so no new endpoint, and the second open is served from cache.
- Only clickable once `picksRevealed` is true (the endpoint rejects earlier). Before then the name stays plain text.
- Gets the same green/red coloring and live refresh for free.

### 3. Hide members without complete picks from "See everyone's picks"
- Backend: add `picks_service.list_submitted_user_ids(db, week_id)` (`week_submission ∪ complete card`) and use it in `get_all_picks_for_week`. Also replace the two duplicated copies of that union in `leaderboard_service` so the leaderboard and picks table can never disagree.
- Same "complete" definition as the leaderboard, so the two views always list the same people.

### 4. "Max Points" column on the weekly leaderboard
- Backend: add `max_points_possible = total_points + points_remaining` to `LeaderboardMemberRead` (computed in `_ranked_members`; weekly only, the season view leaves it at its default). Frontend: new sortable "Max Points" column after "Points Left", plus type in `types/leaderboard.ts`.

### 5. Mark who is mathematically eliminated from placing
- Definition (my assumption, please confirm): "placing" = finishing in the paid top 3 (matches `_weekly_payout_cents`). A member is eliminated when at least 3 *other* members already have **current points strictly greater than their max possible points**. This is a sound bound: it never marks someone eliminated who can still place. Equal points are not counted (tie-breakers on correct picks and highest missed confidence could still go either way).
- Backend computes `is_eliminated` in `_ranked_members` next to `max_points_possible`, so the rule lives in one tested place. Weekly only.
- Frontend: eliminated rows are dimmed with an "Eliminated" badge beside the name, plus a one-line legend under the table. Badge shows only while the week still has points in play (any `pointsRemaining > 0`); in a finished week everyone outside the top 3 would otherwise be flagged, which adds nothing.
- Known ceiling: the bound treats each rival's current points independently, so a late-week case where two rivals can't both pass someone stays "alive". With only SNF/MNF left, the existing outcome-scenarios view is exact. Upgrade path if wanted: enumerate remaining game outcomes (cheap for ≤2 games).

## Files touched

Backend (`backend/`): `app/services/picks_service.py`, `app/services/leaderboard_service.py`, `app/schemas/leaderboard.py`; tests in `tests/test_nfl.py` and `tests/test_leaderboard.py`. No migration.

Frontend (`frontend/`): `components/leaderboard/AllPicksModal.tsx`, `pages/LeaderboardPage.tsx`, `types/leaderboard.ts`; tests in `pages/LeaderboardPage.test.tsx` (plus a test file for the outcome helper).

## Tests (written first)

- Backend: all-picks omits members with an incomplete card and keeps submitted/complete-card members; `max_points_possible` equals points + points left; elimination cases: clearly out, tied-at-boundary stays alive, fewer than 3 rivals ahead stays alive, nobody eliminated when 3 or fewer members.
- Frontend: correct/wrong/neutral cell classes and sr-only text (final win, final loss, live, tie); modal refetches while games are live and stops when all are final; clicking a member opens a modal listing only that member; Max Points column renders and sorts; eliminated badge shows only mid-week.

## Verification

Narrowest first: touched backend tests, then `ruff`, `black --check`, `isort`, `mypy app`; frontend `vitest` on touched files, `lint`, `format:check`, `build`. Then a local run against seed data (`prepare_local.ps1`) with a browser check at 375px and desktop, including a mid-week state. No deploy, push, or production writes without a separate go-ahead.

## Open questions

1. Is "placing" the top 3 (paid places), as assumed? If you mean only 1st place, the rule becomes "at least 1 other member's current points exceed my max".
2. A tied game: neutral (my default) or red?
