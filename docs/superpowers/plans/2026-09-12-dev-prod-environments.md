# Dev and Prod Environments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a second, fully separate Fly.io environment ("dev") that mirrors production, and automate both environments' deploys via GitHub Actions instead of manual `fly deploy` commands.

**Architecture:** One `fly.toml` per Fly app per environment (`backend/fly.toml` + new `backend/fly.dev.toml`, `frontend/fly.toml` + new `frontend/fly.dev.toml`), a runtime-templated nginx config so the frontend's backend-proxy target is no longer baked into the Docker image, and two new GitHub Actions jobs gated on the existing test jobs that deploy on push to `develop` (dev) or `main` (prod).

**Tech Stack:** Fly.io, Docker, nginx (envsubst templating), GitHub Actions, flyctl, Neon Postgres (dev only — prod keeps Fly Managed Postgres).

**Spec:** [docs/superpowers/specs/2026-09-12-dev-prod-environments-design.md](../specs/2026-09-12-dev-prod-environments-design.md)

## Global Constraints

- Prod's existing `backend/fly.toml`, `frontend/fly.toml`, and all existing Fly secrets must not change in a way that alters prod behavior — the only permitted change to an existing prod file is adding the new `API_UPSTREAM` env var (Task 2), which preserves prod's current hardcoded value.
- Both environments run the scheduler (`ENABLE_SCHEDULER=true`) — do not scale either API app to more than one machine (`min_machines_running = 1` stays as-is), per the existing single-scheduler-instance constraint documented in `docs/release-readiness.md`.
- Never commit a real secret value (JWT secret, API keys, connection strings) to any tracked file. Secrets are set via `fly secrets set` / `gh secret set` only.
- Dev sends real email through the same Resend domain as prod — flag this to the user rather than silently assuming a mock.

---

## Part A — Repository changes

These four tasks only touch tracked files and can be fully implemented, tested, and committed without touching any cloud account.

### Task 1: Make the frontend's backend-proxy target a runtime env var instead of a build-time constant

**Files:**
- Create: `frontend/nginx.frontend.conf.template`
- Delete: `frontend/nginx.frontend.conf`
- Modify: `docker/Dockerfile.frontend`

**Interfaces:**
- Produces: an `API_UPSTREAM` environment variable, read by the nginx container at startup, defaulting to `nfl-confidence-api.fly.dev` (prod's current hardcoded value) if unset. Task 2's `frontend/fly.toml`/`frontend/fly.dev.toml` changes set this per environment.

- [ ] **Step 1: Confirm the current file's exact content before changing it**

Run: `cat frontend/nginx.frontend.conf`

Expected output (this is what you're about to template):
```
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;

    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        try_files $uri =404;
    }

    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    location /api/ {
        proxy_pass https://nfl-confidence-api.fly.dev;
        proxy_ssl_server_name on;
        proxy_ssl_name nfl-confidence-api.fly.dev;

        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Create the templated version**

Create `frontend/nginx.frontend.conf.template` with the hardcoded host replaced by `${API_UPSTREAM}` in both places it appears:

```
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;

    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        try_files $uri =404;
    }

    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    location /api/ {
        proxy_pass https://${API_UPSTREAM};
        proxy_ssl_server_name on;
        proxy_ssl_name ${API_UPSTREAM};

        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Note: `$uri`, `$host`, `$scheme`, and `$proxy_add_x_forwarded_for` are nginx's own runtime variables, not shell/env vars — they are left untouched by `envsubst` because no environment variable is ever named `uri`, `host`, `scheme`, or `proxy_add_x_forwarded_for` in the container. Only `${API_UPSTREAM}` gets substituted. This is the same pattern documented in the official `nginx` Docker image's templating feature (`/etc/nginx/templates/*.template` → `envsubst` → `/etc/nginx/conf.d/`).

- [ ] **Step 3: Delete the old, non-templated file**

Run: `rm frontend/nginx.frontend.conf`

- [ ] **Step 4: Update the Dockerfile to use the template and set a safe default**

In `docker/Dockerfile.frontend`, replace the final stage:

```dockerfile
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

with:

```dockerfile
FROM nginx:1.27-alpine

# Default matches prod; overridden per-environment via fly.toml's [env] block
# (see frontend/fly.toml and frontend/fly.dev.toml).
ENV API_UPSTREAM=nfl-confidence-api.fly.dev

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.frontend.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Leave the build stage (everything above `FROM nginx:1.27-alpine`) untouched — this task does not change `VITE_API_URL` or the build-time `RUN grep` checks.

- [ ] **Step 5: Build the image and verify the template renders correctly with an explicit override**

Run (from the repo root):
```bash
docker build -f docker/Dockerfile.frontend -t nfl-confidence-web-test ./frontend
docker run -d --name nfl-confidence-web-test -e API_UPSTREAM=dev-test.example.com -p 18080:80 nfl-confidence-web-test
sleep 1
docker exec nfl-confidence-web-test cat /etc/nginx/conf.d/default.conf
```

Expected: the printed config contains `proxy_pass https://dev-test.example.com;` and `proxy_ssl_name dev-test.example.com;` — the value you passed via `-e`, not the hardcoded prod host. `$uri`, `$host`, `$scheme`, `$proxy_add_x_forwarded_for` must appear unchanged (still literal nginx variables, not empty or substituted).

- [ ] **Step 6: Verify the no-override case still matches prod's original behavior**

Run:
```bash
docker rm -f nfl-confidence-web-test
docker run -d --name nfl-confidence-web-test -p 18080:80 nfl-confidence-web-test
sleep 1
docker exec nfl-confidence-web-test cat /etc/nginx/conf.d/default.conf
docker rm -f nfl-confidence-web-test
docker rmi nfl-confidence-web-test
```

Expected: with no `-e API_UPSTREAM=...` supplied, the rendered config contains `proxy_pass https://nfl-confidence-api.fly.dev;` — identical to what was hardcoded before this change. This proves prod's Docker image behavior is unchanged when Task 2 hasn't yet added an explicit `API_UPSTREAM` to `frontend/fly.toml`, and stays correct afterward since Task 2 sets it to the same value.

- [ ] **Step 7: Commit**

```bash
git add frontend/nginx.frontend.conf.template docker/Dockerfile.frontend
git rm frontend/nginx.frontend.conf
git commit -m "feat: make frontend nginx proxy target a runtime env var"
```

---

### Task 2: Add dev Fly configs for both apps

**Files:**
- Create: `backend/fly.dev.toml`
- Create: `frontend/fly.dev.toml`
- Modify: `frontend/fly.toml`

**Interfaces:**
- Consumes: `API_UPSTREAM` env var from Task 1.
- Produces: the two dev Fly app configs that Task 3's CI jobs and Task 5's `fly apps create` target.

- [ ] **Step 1: Add `[env] API_UPSTREAM` to prod's frontend config**

In `frontend/fly.toml`, add an `[env]` block at the end (there isn't one currently):

```toml
[env]
API_UPSTREAM = "nfl-confidence-api.fly.dev"
```

- [ ] **Step 2: Create `backend/fly.dev.toml`**

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

- [ ] **Step 3: Create `frontend/fly.dev.toml`**

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

- [ ] **Step 4: Validate all three TOML files parse correctly**

Run:
```bash
flyctl config validate --config backend/fly.toml
flyctl config validate --config backend/fly.dev.toml
flyctl config validate --config frontend/fly.toml
flyctl config validate --config frontend/fly.dev.toml
```

Expected: for each, a line `Validating <path>` followed by `✓ Configuration is valid` — this catches TOML syntax errors and unknown keys without needing the target app to exist yet.

- [ ] **Step 5: Commit**

```bash
git add backend/fly.dev.toml frontend/fly.dev.toml frontend/fly.toml
git commit -m "feat: add dev Fly app configs"
```

---

### Task 3: CI/CD — deploy dev on push to `develop`, deploy prod on push to `main`

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the existing `backend` and `frontend` job names in this same workflow file (as `needs:` targets), and the `FLY_API_TOKEN` GitHub Actions secret (provided by Task 9 — the workflow will fail at deploy time until that secret exists, but this task's own file-correctness verification does not require it).
- Produces: two new jobs, `deploy-dev` and `deploy-prod`.

- [ ] **Step 1: Add `develop` to the existing trigger branches**

In `.github/workflows/ci.yml`, change:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main, "feature/**"]
```

to:

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop, "feature/**"]
```

- [ ] **Step 2: Add the two deploy jobs at the end of the file**

Append after the existing `frontend` job:

```yaml
  deploy-dev:
    needs: [backend, frontend]
    if: github.event_name == 'push' && github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy backend (dev)
        run: flyctl deploy ./backend --config ./backend/fly.dev.toml --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

      - name: Deploy frontend (dev)
        run: flyctl deploy ./frontend --config ./frontend/fly.dev.toml --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

  deploy-prod:
    needs: [backend, frontend]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy backend (prod)
        run: flyctl deploy ./backend --config ./backend/fly.toml --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

      - name: Deploy frontend (prod)
        run: flyctl deploy ./frontend --config ./frontend/fly.toml --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

The frontend deploy step only runs after the backend deploy step succeeds (sequential steps in one job fail the job on the first error and skip the rest by default), matching the documented "API first, so its `release_command` migrations run before the frontend serves traffic" order.

- [ ] **Step 3: Verify the workflow file is valid YAML**

Run:
```bash
python -c "import yaml, sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('valid')"
```

Expected: `valid`. (If `pyyaml` isn't installed in this shell, run `pip install pyyaml` first, or validate via `gh workflow view` after pushing instead.)

- [ ] **Step 4: Verify the job names and needs match reality**

Run: `grep -n "^  [a-z-]*:" .github/workflows/ci.yml`

Expected output includes exactly: `backend:`, `frontend:`, `deploy-dev:`, `deploy-prod:` — confirming `needs: [backend, frontend]` in the new jobs references the correct, exact existing job names (a typo here would silently make GitHub Actions reject the workflow at parse time).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat: auto-deploy dev on push to develop, prod on push to main"
```

---

### Task 4: Update deployment docs

**Files:**
- Modify: `docs/deployment.md`

- [ ] **Step 1: Update the "Environments" section**

Replace:

```
Development

Local machine

Testing

GitHub Actions

Production

Fly.io
```

with:

```
Development

Local machine (docker-compose or local processes + Neon Free), plus a
hosted dev environment on Fly.io (`nfl-confidence-api-dev`,
`nfl-confidence-web-dev`) for pre-production verification.

Testing

GitHub Actions

Production

Fly.io (`nfl-confidence-api`, `nfl-confidence-web`)
```

- [ ] **Step 2: Replace the aspirational "Continuous Deployment" section with what actually happens**

Replace:

```
# Continuous Deployment

Merge into main

↓

GitHub Actions

↓

Build Images

↓

Deploy to Fly.io

↓

Run Database Migrations

↓

Health Check

↓

Deployment Complete
```

with:

```
# Continuous Deployment

`.github/workflows/ci.yml` deploys automatically after its lint/test/build
jobs pass:

- Push to `develop` → deploys `nfl-confidence-api-dev` then
  `nfl-confidence-web-dev` (the `deploy-dev` job).
- Push or merge to `main` → deploys `nfl-confidence-api` then
  `nfl-confidence-web` (the `deploy-prod` job).

Each deploy runs the backend first — its `release_command` applies Alembic
migrations before the new machine takes traffic — then the frontend. A
failed backend deploy blocks the frontend deploy in the same run. The
manual `fly deploy` commands under "Deploy in order" below remain the
rollback/fallback path if CI is unavailable or a deploy needs to be run
by hand.
```

- [ ] **Step 3: Add a "Dev environment setup" subsection after "Fly.io first deployment"**

Insert this new `##` section immediately after the existing `## Fly.io first deployment` section (before `### Provision Postgres`), documenting the one-time setup for the dev apps in parallel with prod's:

```
## Dev environment one-time setup

The dev environment (`nfl-confidence-api-dev`, `nfl-confidence-web-dev`)
mirrors production but uses its own database and its own copy of every
secret. Run once, using the same account/org as prod:

```powershell
fly apps create nfl-confidence-api-dev
fly apps create nfl-confidence-web-dev
```

Provision a dev database on Neon Free (a separate project or branch from
whatever Neon project is used for local/CI testing — do not point dev at
the same database used for automated tests) and set it:

```powershell
fly secrets set --app nfl-confidence-api-dev DATABASE_URL='<neon-dev-connection-string>'
```

Generate a dev-only JWT secret (distinct from prod's) and set the
remaining secrets, reusing prod's Google OAuth client and Resend key:

```powershell
$jwt = & .\backend\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"

fly secrets set --app nfl-confidence-api-dev `
  JWT_SECRET=$jwt `
  GOOGLE_CLIENT_ID='<same-value-as-prod>' `
  GOOGLE_CLIENT_SECRET='<same-value-as-prod>' `
  RESEND_API_KEY='<same-value-as-prod>'
```

In Google Cloud Console, add to the **existing** OAuth client (do not
create a new one unless isolation from prod becomes a concern later):

- Authorized JavaScript origin: `https://nfl-confidence-web-dev.fly.dev`
- Authorized redirect URI: `https://nfl-confidence-web-dev.fly.dev/api/v1/auth/google/callback`

Dev sends real email through the same verified Resend domain as prod —
use your own address, not a real invitee's, when testing the invite flow
in dev.

Create an org-scoped Fly deploy token (not `fly tokens create deploy`,
which is limited to a single app) and add it as a GitHub Actions secret so
CI can deploy all four apps, which share one Fly org:

```powershell
fly orgs list
fly tokens create org --org <org-slug>
gh secret set FLY_API_TOKEN
```

Finally, create the `develop` branch:

```powershell
git checkout -b develop main
git push -u origin develop
```

A push to `develop` after this setup triggers the first dev deploy. Run
the "Deployment smoke test" checklist below against the `-dev` URLs
before trusting the environment for pre-production verification.
```

- [ ] **Step 4: Commit**

```bash
git add docs/deployment.md
git commit -m "docs: document the dev environment and CI-driven deploy flow"
```

---

## Checkpoint: get Part A onto `main` before starting Part B

Tasks 1-4 only commit locally. Task 9 later branches `develop` off `main`
and expects `ci.yml`'s new trigger branches and deploy jobs to already be
there — push the branch these commits were made on, and get it merged into
`main` (PR + merge, matching this repo's existing workflow — see its git
history for the established pattern) before starting Task 5. Confirm with
`git log --oneline -5 main` that Tasks 1-4's commits appear on `main`
before proceeding.

---

## Part B — Cloud account setup

These tasks modify your Fly.io account, Google Cloud OAuth client, and
GitHub repo secrets. `flyctl` and `gh` are already authenticated in this
workspace (confirmed: `isaacsilver13@gmail.com` / `isaacsilver13`,
repo `isaacsilver13/NFL_Confidence`).

Two different rules apply depending on the step:

- **Resource/account changes that don't expose a secret value** (creating
  Fly apps, listing secrets by name, creating the `develop` branch,
  watching a CI run) can be agent-executed, but each one either costs
  money (new Fly machines) or changes account-level state — confirm each
  one individually before moving to the next, the same as any other
  side-effectful action. Do not batch them.
- **Anything that sets or transmits a secret value** (a database
  connection string, `JWT_SECRET`, `GOOGLE_CLIENT_SECRET`,
  `RESEND_API_KEY`, the Fly deploy token) is marked "(human)" below and
  must be run by you, in your own terminal — it should never pass through
  the agent's tool calls or transcript, the same rule that applies to any
  other password or API key.

### Task 5: Create the two dev Fly apps

- [ ] **Step 1: Create the API app**

Run: `fly apps create nfl-confidence-api-dev`

Expected: `New app created: nfl-confidence-api-dev`

- [ ] **Step 2: Create the web app**

Run: `fly apps create nfl-confidence-web-dev`

Expected: `New app created: nfl-confidence-web-dev`

- [ ] **Step 3: Confirm both exist**

Run: `fly apps list`

Expected: the list includes `nfl-confidence-api`, `nfl-confidence-web`,
`nfl-confidence-api-dev`, and `nfl-confidence-web-dev`.

---

### Task 6: Provision the dev database

**This entire task is human-run, in your own terminal, not by the agent.**
`DATABASE_URL` is a credential (it embeds a database password) — it should
never pass through the agent's tool calls or transcript, the same as any
other password/API-key value per the agent's standing rules.

- [ ] **Step 1: create the Neon project/branch**

In the Neon console, create a new project (or a new branch in an existing
project — but a **different** one from whatever project/branch is used for
local/CI testing) named something like `nfl-confidence-dev`. Copy its
pooled connection string.

- [ ] **Step 2: set it as the dev API app's `DATABASE_URL`**

In your own terminal (not through the agent):

```bash
fly secrets set --app nfl-confidence-api-dev DATABASE_URL='<paste-the-neon-connection-string>'
```

Expected: `Secrets are staged for the first deployment` (Fly secrets apply
on the next deploy, which happens in Task 10).

- [ ] **Step 3: tell the agent it's done** so it can continue to Task 7's
  verification step, without you sharing the connection string itself.

---

### Task 7: Set the remaining dev secrets

Generating the JWT secret and confirming secret *names* are present (Step
4) can be agent-executed — no credential value is exposed in the agent's
own commands there. Actually setting `JWT_SECRET`, `GOOGLE_CLIENT_SECRET`,
and `RESEND_API_KEY` (Steps 1 and 3) must be **run by you, in your own
terminal** — the same rule as Task 6.

- [ ] **Step 1 (human): generate and set a dev-only JWT secret**

In your own terminal:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Take the printed value and, still in your own terminal:

```bash
fly secrets set --app nfl-confidence-api-dev JWT_SECRET='<paste-the-generated-value>'
```

This must be a **different** value from prod's `JWT_SECRET` — generate a
fresh one, do not reuse prod's, and don't share the value with the agent.

- [ ] **Step 2 (human): look up the existing prod OAuth/Resend values**

Look up `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `RESEND_API_KEY`
from wherever you originally stored them (Google Cloud Console →
Credentials for the OAuth values; your Resend dashboard or password
manager for the API key — `fly secrets list` only shows secret *names*,
never values, so they can't be read back from Fly).

- [ ] **Step 3 (human): set the Google OAuth and Resend secrets**

In your own terminal:
```bash
fly secrets set --app nfl-confidence-api-dev \
  GOOGLE_CLIENT_ID='<value-from-step-2>' \
  GOOGLE_CLIENT_SECRET='<value-from-step-2>' \
  RESEND_API_KEY='<same-value-as-prod>'
```

`GOOGLE_CLIENT_ID` is not secret and can safely be shared with the agent if
useful for context, but `GOOGLE_CLIENT_SECRET` and `RESEND_API_KEY` should
not be.

- [ ] **Step 4: Confirm all expected secret names are present (not values)**

Run: `fly secrets list --app nfl-confidence-api-dev`

Expected: the list includes `DATABASE_URL`, `JWT_SECRET`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `RESEND_API_KEY` — names and
timestamps only, matching the pattern `docs/deployment.md` already
documents for verifying prod's secrets.

---

### Task 8: Register the dev URL with Google OAuth (human — Google Cloud Console has no CLI for this)

- [ ] **Step 1:** In Google Cloud Console → APIs & Services → Credentials,
  open the existing OAuth 2.0 Client used by prod.
- [ ] **Step 2:** Add `https://nfl-confidence-web-dev.fly.dev` to
  **Authorized JavaScript origins**.
- [ ] **Step 3:** Add
  `https://nfl-confidence-web-dev.fly.dev/api/v1/auth/google/callback` to
  **Authorized redirect URIs**.
- [ ] **Step 4:** Save.

---

### Task 9: Wire up GitHub Actions and the `develop` branch

Steps 1-2 create and store a credential (the Fly deploy token) — **run
both in your own terminal, in one go, without relaying the token value
through the agent.** Confirming the org slug (part of Step 1) is safe to
do via the agent first if useful.

- [ ] **Step 1 (human): create an org-scoped Fly deploy token**

`fly tokens create deploy` is scoped to a single app; since one GitHub
secret needs to deploy all four apps (prod + dev, API + web), create an
org-scoped token instead. The agent can run `fly orgs list` to confirm the
org slug (no secret involved), but you should run the token creation
itself:

```bash
fly tokens create org --org <org-slug>
```

- [ ] **Step 2 (human): store it as a GitHub Actions secret, in the same terminal session**

```bash
gh secret set FLY_API_TOKEN --repo isaacsilver13/NFL_Confidence
```

When prompted, paste the token from Step 1.

- [ ] **Step 3: Confirm it's set**

Run: `gh secret list --repo isaacsilver13/NFL_Confidence`

Expected: `FLY_API_TOKEN` appears in the list (value not shown).

- [ ] **Step 4: Create and push the `develop` branch**

Run:
```bash
git fetch origin
git checkout -b develop origin/main
git push -u origin develop
```

Branching from `origin/main` (not the possibly-stale local `main`) ensures
`develop` actually includes Part A's merged changes.

Expected: GitHub shows a new `develop` branch, and (since Part A's
`ci.yml` changes must already be merged into `main` before this branch is
cut, so `develop` inherits them) a new Actions run starts for the push,
including the `deploy-dev` job.

---

### Task 10: First dev deploy and smoke test

- [ ] **Step 1: Watch the `deploy-dev` job run**

Run: `gh run watch --repo isaacsilver13/NFL_Confidence`

Expected: `backend`, `frontend`, and `deploy-dev` all succeed. `deploy-prod`
is skipped (its `if` condition only matches `main`).

- [ ] **Step 2: Verify both dev apps are healthy**

Run:
```bash
fly status --app nfl-confidence-api-dev
fly status --app nfl-confidence-web-dev
curl -s https://nfl-confidence-api-dev.fly.dev/api/v1/health/ready
```

Expected: both `fly status` calls show a running machine passing health
checks, and the readiness JSON reports `"database": "healthy"`,
`"schema": "valid"`, `"scheduler": "running"`.

- [ ] **Step 3: Run the full smoke test from `docs/deployment.md`**

Follow the existing "Deployment smoke test" checklist in
`docs/deployment.md`, substituting the `-dev` URLs
(`https://nfl-confidence-web-dev.fly.dev`,
`https://nfl-confidence-api-dev.fly.dev`) everywhere it references the
prod URLs. Pay particular attention to step 6 (score sync) — this is the
direct live verification of the scoring/scheduler fix from the prior
session, now safely testable against dev data instead of the real league.

- [ ] **Step 4: Confirm prod was not touched**

Run:
```bash
fly status --app nfl-confidence-api
git log --oneline -5 main
```

Expected: prod's machine shows no new deploy event from this work, and
`main`'s history shows only the commits from Tasks 1-4 (merged normally,
not auto-deployed until pushed/merged to `main`).

---

## Self-Review Notes

- **Spec coverage:** every section of the spec has a corresponding task —
  architecture/Fly configs (Tasks 2, 5), the nginx fix (Task 1), CI/CD
  (Tasks 3, 9), docs (Task 4), manual setup (Tasks 6-9), rollout/verification
  (Task 10).
- **Type/name consistency:** `API_UPSTREAM` is introduced in Task 1 and
  consumed identically by both `frontend/fly.toml` and
  `frontend/fly.dev.toml` in Task 2. Job names `backend`/`frontend` used in
  Task 3's `needs:` match the existing `ci.yml` job keys verified in Task 3
  Step 4. App names (`nfl-confidence-api-dev`, `nfl-confidence-web-dev`) are
  identical across Tasks 2, 3, 5, 6, 7, 8, 10.
- **No placeholders left unresolved** other than values that can only come
  from the user's accounts (Neon connection string, existing Google/Resend
  credentials) — each of those is called out as a human step with an exact
  instruction for what to do with the value once obtained, not left vague.
