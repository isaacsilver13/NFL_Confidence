# Authentication and scheduler remediation

Production automatic ticks belong to cron-job.org; its wake/tick jobs are unchanged.
`scheduled-tick.yml` is now manual-only, defaulting to dev. Keep its four scoped
URL/token secrets for manual recovery; the old TICK_*_ENABLED variables are unused.
Its historical filename does not mean a schedule is still active.

Refresh rotation uses conditional UPDATE ... RETURNING in the same transaction
as replacement issuance: one consumer wins, and failed issuance rolls back the
consume. No schema migration or existing-session invalidation is required.
The python-jose dependency is updated to 3.5.0; JWT APIs/algorithms/claims remain
unchanged. Unused passlib is removed. Release notes identify the CVE fixes in 3.4.0:
https://github.com/mpdavis/python-jose/releases/tag/3.4.0

Frontend CI runs the coverage-producing test execution once. Existing formatters,
type checks, coverage gate and deploy dependencies are retained.
