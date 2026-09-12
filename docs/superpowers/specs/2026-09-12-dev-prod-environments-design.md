# Dev and Prod Environments — Design

Version: 1.0
Status: Approved for implementation planning

## Context

The app currently has exactly one deployed environment: production, on Fly.io
(`nfl-confidence-api` + `nfl-confidence-web`), deployed by hand by following
the commands in `docs/deployment.md`. There is no way to verify a change —
especially something like the scoring/scheduler fix that motivated this
request — against a real, running deployment (real OAuth flow, real
scheduler, real email sending) without touching production data.

This spec adds a second, fully separate Fly.io environment ("dev") that
mirrors production's architecture, plus GitHub Actions automation so both
environments deploy themselves from git pushes instead of manual `fly
deploy` commands.

## Goals

- A dev deployment that behaves like prod (same scheduler, same OAuth flow,
  same email sending) against its own database, so bugs surface before
  reaching real league data.
- Push to `develop` deploys dev automatically; push/merge to `main` deploys
  prod automatically.
- Zero changes to prod's existing Fly apps, secrets, or URLs.

## Non-goals

- No Kubernetes/multi-region/preview-per-PR environments — just the two.
- No change to the scheduler's single-machine constraint (still one
  always-on machine per environment; still do not scale either API app
  horizontally — see `docs/release-readiness.md`).
- No new secrets-management tooling — secrets continue to live in Fly's
  `fly secrets` store, one set per app.

## Architecture

| | Prod (existing, unchanged) | Dev (new) |
|---|---|---|
| API app | `nfl-confidence-api` | `nfl-confidence-api-dev` |
| Web app | `nfl-confidence-web` | `nfl-confidence-web-dev` |
| API config | `backend/fly.toml` | `backend/fly.dev.toml` (new file) |
| Web config | `frontend/fly.toml` | `frontend/fly.dev.toml` (new file) |
| Database | Fly Managed Postgres | Neon Free (separate project/branch from the one used for local/CI testing) |
| Scheduler | `ENABLE_SCHEDULER=true` | `ENABLE_SCHEDULER=true` |
| Deploy trigger | push/merge to `main` | push to `develop` |
| URLs | `nfl-confidence-api.fly.dev`, `nfl-confidence-web.fly.dev` | `nfl-confidence-api-dev.fly.dev`, `nfl-confidence-web-dev.fly.dev` |

Fly has no built-in notion of "environments" — each app is standalone. The
established pattern (and the one used here) is one `fly.toml` per app, with
the environment selected by which config file you pass to `fly deploy
--config`. Prod's existing files are not modified.

## Required fix: the frontend's nginx proxy target is baked in at build time

[`frontend/nginx.frontend.conf`](../../../frontend/nginx.frontend.conf) hardcodes:

```
proxy_pass https://nfl-confidence-api.fly.dev;
proxy_ssl_name nfl-confidence-api.fly.dev;
```

This is copied verbatim into the Docker image
([`docker/Dockerfile.frontend`](../../../docker/Dockerfile.frontend) line 20). A
dev-tagged frontend image built from today's Dockerfile would still proxy
`/api/` to the **production** API, silently pointing dev traffic at prod.

**Fix**: rename the file `nginx.frontend.conf.template` and replace the
hardcoded host with `${API_UPSTREAM}` in both places. Change the Dockerfile
to copy it to `/etc/nginx/templates/default.conf.template` instead of
directly to `/etc/nginx/conf.d/default.conf` — the official `nginx:1.27-alpine`
image's entrypoint automatically runs `envsubst` on every file in
`/etc/nginx/templates/` at container start and writes the substituted result
into `conf.d/`, using whatever environment variables are present in the
container. `API_UPSTREAM` is then set via each `fly.toml`'s `[env]` block —
`nfl-confidence-api.fly.dev` for prod, `nfl-confidence-api-dev.fly.dev` for
dev — so one Docker image definition serves both environments correctly,
distinguished only by which `fly.toml` supplies the runtime env var.

This fix is a prerequisite for dev to work correctly at all, not an
optional nice-to-have, and should land before or together with the first
dev deploy.

## `backend/fly.dev.toml` (new file)

Same shape as `backend/fly.toml`, with:

```toml
app = "nfl-confidence-api-dev"
primary_region = "iad"

[build]
dockerfile = "../docker/Dockerfile.backend"

[deploy]
release_command = "alembic upgrade head"

[http_service]
internal_port = 8000
force_https = true
auto_stop_machines = "off"
auto_start_machines = true
min_machines_running = 1

[[http_service.checks]]
grace_period = "30s"
interval = "30s"
method = "GET"
timeout = "15s"
path = "/api/v1/health/ready"

[[vm]]
memory = "512mb"
cpus = 1
cpu_kind = "shared"

[env]
ENVIRONMENT = "development"
ENABLE_SCHEDULER = "true"
NFL_API_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
NFL_API_TIMEOUT_SECONDS = "10"
GOOGLE_OAUTH_TIMEOUT_SECONDS = "8"
APP_URL = "https://nfl-confidence-web-dev.fly.dev"
CORS_ORIGINS = "https://nfl-confidence-web-dev.fly.dev"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = "15"
JWT_REFRESH_TOKEN_EXPIRE_DAYS = "30"
EMAIL_FROM = "NFL Confidence Pool (dev) <pickspoolnfl@gmail.com>"
```

`DATABASE_URL`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and
`RESEND_API_KEY` are set as Fly secrets on `nfl-confidence-api-dev` (never
committed), separate values from prod's secrets — see "Manual one-time
setup" below.

## `frontend/fly.dev.toml` (new file)

Same shape as `frontend/fly.toml`, with:

```toml
app = "nfl-confidence-web-dev"
primary_region = "iad"

[build]
dockerfile = "../docker/Dockerfile.frontend"

[build.args]
VITE_API_URL = "/api/v1"

[http_service]
internal_port = 80
force_https = true
auto_stop_machines = "off"
auto_start_machines = true
min_machines_running = 1

[[http_service.checks]]
grace_period = "10s"
interval = "30s"
method = "GET"
timeout = "5s"
path = "/"

[[vm]]
memory = "256mb"
cpus = 1
cpu_kind = "shared"

[env]
API_UPSTREAM = "nfl-confidence-api-dev.fly.dev"
```

(Prod's `frontend/fly.toml` gains the matching
`[env] API_UPSTREAM = "nfl-confidence-api.fly.dev"` as part of the nginx
templating fix above, so both configs are symmetric.)

## CI/CD

Extend `.github/workflows/ci.yml`:

1. **Trigger changes**: add `develop` alongside `main` to both the `push`
   and `pull_request` `branches` lists, so `develop` gets the same
   lint/test/build gate `main` already has.
2. **New jobs**, gated on the existing `backend` and `frontend` test jobs
   passing (`needs: [backend, frontend]`):
   - `deploy-dev`: `if: github.ref == 'refs/heads/develop' && github.event_name == 'push'`. Deploys backend then frontend using the `.dev.toml` configs.
   - `deploy-prod`: `if: github.ref == 'refs/heads/main' && github.event_name == 'push'`. Deploys backend then frontend using the existing configs — this replaces the manual `fly deploy` steps in `docs/deployment.md`'s "Deploy in order" section.
   - Each job installs `flyctl` (`superfly/flyctl-actions/setup-flyctl@master`), authenticates via the `FLY_API_TOKEN` GitHub secret, and runs backend deploy (`flyctl deploy ./backend --config ./backend/fly.dev.toml --remote-only`, or the prod-config equivalent) as a step before the frontend deploy step in the same job, so a failed backend deploy blocks the frontend deploy — matching the documented "API first, migrations run via release_command" ordering.
3. One GitHub Actions secret: `FLY_API_TOKEN`. A single org-scoped Fly token can deploy both apps in each environment since all four apps live in the same Fly org; no per-app token needed for this scale.

`docs/deployment.md`'s existing manual `fly deploy` commands stay documented
as the rollback/fallback path, updated to note that normal deploys now
happen via CI.

## Manual one-time setup (outside this repo's automation — commands to hand to the user, not run by the agent)

1. **Fly apps**: `fly apps create nfl-confidence-api-dev` and
   `fly apps create nfl-confidence-web-dev`.
2. **Dev database**: create a new Neon project (or a new branch in an
   existing Neon project, separate from the one used for local/CI testing),
   copy its pooled connection string, and set it:
   `fly secrets set --app nfl-confidence-api-dev DATABASE_URL='<neon-connection-string>'`.
3. **Dev JWT secret**: generate and set a value distinct from prod's, the
   same way `docs/deployment.md` already documents for prod.
4. **Google OAuth**: add `https://nfl-confidence-web-dev.fly.dev` as an
   additional Authorized JavaScript origin and
   `https://nfl-confidence-web-dev.fly.dev/api/v1/auth/google/callback` as an
   additional Authorized redirect URI on the existing OAuth client (reusing
   one client for both environments — simplest option; a fully separate
   client is possible later if isolation becomes a concern). Set
   `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` secrets on the dev API app (same
   values as prod, since it's the same client).
5. **Resend**: reuse the existing verified sending domain; set the same
   `RESEND_API_KEY` secret on the dev API app. Dev sends real email — use
   your own address when testing the invite flow.
6. **GitHub secret**: add `FLY_API_TOKEN` (an org deploy token from
   `fly tokens create deploy`) to the repo's Actions secrets.
7. **Branch**: create the `develop` branch from `main`.

## Rollout order for implementation

1. nginx templating fix (`nginx.frontend.conf` → `.conf.template` +
   Dockerfile change) — verify locally via `docker-compose up` that prod
   behavior is unchanged (existing `docker-compose.yml` doesn't use this
   nginx path directly today, so this mainly needs verifying via a local
   `docker build`/`docker run` of the frontend image, or the first dev
   deploy itself).
2. Add `backend/fly.dev.toml` and `frontend/fly.dev.toml`.
3. User performs the manual one-time setup above.
4. Add the CI deploy jobs and update trigger branches.
5. Push to `develop`, verify the dev smoke test (reuse
   `docs/deployment.md`'s existing "Deployment smoke test" checklist against
   the `-dev` URLs).
6. Update `docs/deployment.md` to describe both environments and the new
   CI-driven deploy flow.

## Verification

- `docker build -f docker/Dockerfile.frontend .` succeeds and the running
  container's rendered `/etc/nginx/conf.d/default.conf` contains the
  correct substituted upstream (no literal `${API_UPSTREAM}` left over).
- First dev deploy: `fly status --app nfl-confidence-api-dev` healthy,
  `/api/v1/health/ready` reports `database: healthy`, `schema: valid`,
  `scheduler: running`; `fly status --app nfl-confidence-web-dev` healthy.
- Run the existing `docs/deployment.md` smoke-test checklist end-to-end
  against the dev URLs, including the score-sync verification step — this
  is the direct test of the scoring/scheduler fix from the prior session.
- Confirm prod is completely unaffected: prod `fly.toml`s unchanged, prod
  secrets untouched, a push to `develop` does not trigger `deploy-prod`.
