# Frontend improvements — 19 October 2026

1. Expose all commissioner names in league metadata and fix weekly/season dashboard summaries.
2. Correct completed-week averages, weekly pick counts, confidence success rates, and kickoff sorting in My Picks.
3. Compact game breakdown cards and review tables; apply readable team selection colors; replace the Eagles logo with a transparent source asset.
4. Group member administration tools in accessible accordions.
5. Run focused regressions, frontend lint/build/tests, local responsive smoke checks, and an independent agent review. Fix confirmed findings.

Season wins and podiums retain the existing completed-week rank calculation: wins count rank 1; podiums count ranks 1, 2, and 3, including tied ranks under the existing ranking rules.

## Completed

- League/bootstrap metadata now includes all commissioners without exposing the owner-only member roster. Season records aggregate completed weekly results; previously the season response defaulted to zero because the season model has no pick-count fields.
- Weekly summaries follow the same selected week as the leaderboard and refresh every minute, including when collapsed. Season summaries refresh on the same interval.
- My Picks averages only completed weeks, shows correct/settled counts per week, charts success percentages across settled non-voided picks with correct/used tooltips, and defaults the compact review table to kickoff then alphabetical matchup.
- Breakdown cards use two columns on desktop and one on narrow phones. Selected winners and selection labels use readable team palettes. Member tools use accessible accordions.
- Replaced the Eagles asset with the transparent [ESPN team logo](https://a.espncdn.com/i/teamlogos/nfl/500/phi.png); verified the corner alpha is zero in a browser.

## Verification

- All 185 frontend tests pass. Frontend lint and production build pass.
- Changed frontend files pass Prettier. The repository-wide format check reports existing issues in 55 untouched files; those files were left as-is.
- Backend Ruff, Black, import-order, and mypy checks pass. The new disposable SQLite regression verifies commissioner metadata for ordinary members and excludes ongoing weeks from season records.
- Synthetic browser smoke checks pass at 375px, 390px, and 1280px. Checked chart fractions and labels, completed-week average, no page overflow, responsive game columns, transparent Eagles logo, team colors across themes, and member accordions. Screenshots are under the ignored frontend/test-results/frontend-smoke directory.
- Independent agent reviewed the implementation and final layout refinements; no concrete findings remained.
- The full PostgreSQL-backed suite was not run: local configuration points to a hosted database and Docker is not running. No hosted database writes or deployment were performed.

## Release verification

The user subsequently requested full testing and deployment. Changes were reapplied on main at e3a7288, retaining its newer team palettes, authentication fixes, combined dashboard card, and current-week admin defaults.

- Full backend suite: 248 passed against local Docker PostgreSQL; 85.88% coverage. Ruff, Black, isort, and mypy all pass with main's pinned dependencies.
- Frontend suite: 191 passed with main's Vitest 5 dependency; 86.15% statement coverage. Lint, production build, and formatting checks pass (the Windows formatting check uses automatic line endings).
- All 20 mobile Playwright checks pass against an isolated local PostgreSQL fixture. Updated stale test navigation and progress-panel expectations to the current UI.
- Additional real-API browser checks pass at 375px, 390px, and 1280px, including correct completed-week averages, chart fractions, sorting, responsive cards, team colors, commissioner list, current-week admin defaults, and saving/submitting four picks followed by reload.
- These checks exposed a submission race: Submit could run before the last debounced autosave. Submit now waits for the latest draft to save, with a Retry save action for network failures. Deferred-save and failed-save recovery regressions cover both cases; independent review confirmed the recovery fix.
- No migration is required for these changes. Production rollout uses the existing main CI workflow and its Fly deployment job.
