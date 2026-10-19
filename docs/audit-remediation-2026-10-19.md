# Authentication and scheduler remediation

Production automatic ticks belong to cron-job.org; its wake/tick jobs are unchanged.
`scheduled-tick.yml` is now manual-only, defaulting to dev. Keep its four scoped
URL/token secrets for manual recovery; the old TICK_*_ENABLED variables are unused.
Its historical filename does not mean a schedule is still active.

Refresh rotation uses conditional UPDATE ... RETURNING in the same transaction
as replacement issuance: one consumer wins, and failed issuance rolls back the
consume. No schema migration or existing-session invalidation is required.
JWT signing/verification now uses PyJWT 2.15.1; the HS256 wire format and issued
claims remain compatible with existing access tokens. An independent HMAC fixture
checks compatibility. python-jose is removed because its latest release still
matches an unpatched advisory; this app's explicit algorithm restriction means
that match alone did not establish a reachable exploit. Unused passlib is removed.
See [the advisory](https://github.com/advisories/GHSA-3qf3-8w2g-rqmx).
PyJWT also rejects future `iat` values; keep clocks synchronized across instances
to avoid brief authentication failures from an instance whose clock is ahead.

FastAPI/Starlette, multipart parsing, Authlib, pytest/pytest-asyncio and Black are
updated to supported patched versions. Starlette is pinned to 1.7.0 for Python3.10
compatibility. Black's required normalization preserves every changed Python AST,
including historical migrations; there are no schema or SQL changes.

Frontend CI runs the coverage-producing test execution once. Existing formatters,
type checks, coverage gate and deploy dependencies are retained.
