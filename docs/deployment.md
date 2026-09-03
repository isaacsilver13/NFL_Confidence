# Deployment

Version: 1.0

---

# Overview

The application will be deployed using Docker containers.

Hosting Platform

Fly.io

The checked-in Fly configs use these default app names:

- API: `nfl-confidence-api`
- Frontend: `nfl-confidence-web`

Fly app names are globally unique. Change the `app` value in
`backend/fly.toml` or `frontend/fly.toml` if either name is already taken, and
update the frontend `VITE_API_URL` build argument and the URLs below to match.

---

# Environments

Development

Local machine

Testing

GitHub Actions

Production

Fly.io

---

# Services

Frontend

React application

Backend

FastAPI application

Database

PostgreSQL

Email

Resend

---

# Environment Variables

Frontend

VITE_API_URL (optional; defaults to the same-origin `/api/v1` path)

BACKEND_URL (optional Vite development proxy target; defaults to `http://127.0.0.1:8000`)

Backend

DATABASE_URL

GOOGLE_CLIENT_ID

GOOGLE_CLIENT_SECRET

JWT_SECRET

RESEND_API_KEY

NFL_API_KEY

APP_URL

GOOGLE_OAUTH_REDIRECT_URL (production: `https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback`)

---

# Local Development

Run the frontend at `http://localhost:5173` and the backend at its local port. The
frontend calls `/api/v1` on its own origin, and Vite proxies `/api` to `BACKEND_URL`.
This keeps local browser requests same-origin, so the frontend does not need to know
the backend hostname and local CORS is not involved in the normal workflow.

Set `VITE_API_URL` only when the frontend must call an API hosted on a separate origin.
In that deployment, configure the backend `CORS_ORIGINS` allowlist to contain the exact
frontend origin; do not use `*` with credentialed requests.

### Neon Free with a local application

Neon Free can provide the hosted PostgreSQL database while the frontend and backend
remain local. The application only requires a PostgreSQL `DATABASE_URL`; Fly Managed
Postgres is not required.

1. Create a Neon project on the Free plan and copy its pooled PostgreSQL connection
	string. Keep the connection string out of tracked files and chat.
2. Set `DATABASE_URL` in the local backend environment to that connection string.
3. Run the migrations and optional deterministic fixture from the backend directory:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m scripts.seed_test_data --season 2026
```

4. Start the backend directly with its virtual environment and start the frontend with
	Vite. Do not start the Docker Compose backend at the same time, because Compose
	overrides `DATABASE_URL` with its local PostgreSQL service.

Neon Free scales compute to zero after inactivity and includes a monthly compute
allowance. The in-process scheduler performs recurring database work, so stop the
backend when it is not needed or set `ENABLE_SCHEDULER=false` for API and UI work that
does not require scheduled imports, pick locking, score synchronization, or reminders.
When the scheduler is disabled, `/api/v1/health/ready` reports `scheduler: disabled`.

---

# Docker

Frontend Dockerfile

Backend Dockerfile

docker-compose.yml for local development

## Fly.io first deployment

Run these commands from the repository root in PowerShell. Install and
authenticate `flyctl` first, then confirm that the selected organization is the
one that should own the apps.

```powershell
fly auth login
fly apps create nfl-confidence-api
fly apps create nfl-confidence-web
```

If an app already exists, the corresponding `fly apps create` command can be
skipped. The backend is intentionally configured with one always-on machine.
The FastAPI process owns the only APScheduler instance, and the Fly config does
not declare a second worker process. Do not scale the API to multiple machines
until the scheduler has moved to a dedicated worker or has a platform-level
singleton.

### Provision Postgres

Use Fly Managed Postgres for a new deployment. The exact plan names depend on
the Fly account and `flyctl` version; select a supported production plan when
the command prompts:

```powershell
fly mpg create --name nfl-confidence-db --region iad
fly mpg list
fly mpg attach <cluster-id-or-name> --app nfl-confidence-api
fly secrets list --app nfl-confidence-api
```

The attach operation supplies `DATABASE_URL` to the API app. The backend
normalizes Fly's `postgres://` or `postgresql://` form to the installed
`psycopg` driver. If your account still exposes the legacy Fly Postgres CLI,
use `fly postgres create` and `fly postgres attach` instead. Confirm that the
database is reachable before deploying the frontend.

### Set production secrets

Do not commit these values or paste them into chat. Generate the JWT secret in
your local PowerShell session and send secrets directly to Fly:

```powershell
$jwt = & .\backend\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"

fly secrets set --app nfl-confidence-api `
  ENVIRONMENT=production `
  JWT_SECRET=$jwt `
  APP_URL=https://nfl-confidence-web.fly.dev `
  CORS_ORIGINS=https://nfl-confidence-web.fly.dev `
	GOOGLE_OAUTH_REDIRECT_URL=https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback `
  GOOGLE_CLIENT_ID='<google-client-id>' `
  GOOGLE_CLIENT_SECRET='<google-client-secret>' `
  RESEND_API_KEY='<resend-api-key>' `
  EMAIL_FROM='NFL Confidence <picks@your-verified-domain.example>'
```

`DATABASE_URL` should already be present from the Postgres attach. If it is
not, stop and attach the database before continuing rather than copying a
password into a tracked file. Verify the non-secret names and values with:

```powershell
fly secrets list --app nfl-confidence-api
```

The list command shows names and timestamps, not secret values. The production
configuration rejects the insecure local JWT default. The frontend proxy makes
browser API requests same-origin, while the rollout cookie remains `Secure`,
`HttpOnly`, and `SameSite=None` until the private-window callback flow has been
verified; tighten it to `SameSite=Lax` in a follow-up after that check.

### Configure Google OAuth

In Google Cloud Console, create or select a Web application OAuth client. Add:

- Authorized JavaScript origin: `https://nfl-confidence-web.fly.dev`
- Authorized redirect URI: `https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback`

The callback is proxied by the frontend to FastAPI. On success it sets the
refresh cookie on the web origin and redirects the browser to `APP_URL`; the SPA
then bootstraps the session through the same-origin proxy. Keep the old API
callback URI authorized only during rollout if it is needed for rollback.
The API bounds Google discovery and token exchange with
`GOOGLE_OAUTH_TIMEOUT_SECONDS` (8 seconds by default) and returns a structured
authentication error if the provider or network does not respond in time.
Do not add a trailing slash to either URI unless the deployed route also has
one. Keep the Google consent screen in testing mode until the invited users are
known, or complete Google's production verification requirements before a
larger launch.

### Configure Resend

In Resend, add and verify the sending domain you will use for `EMAIL_FROM`.
Publish the DNS records Resend provides, wait for the domain to show as
verified, create an API key with sending permission, and set that key as
`RESEND_API_KEY`. Use a real sender such as
`NFL Confidence <picks@your-verified-domain.example>`; the local `.local`
sender must never be used in production. Send one invite email during smoke
testing and confirm both delivery and the Resend event log.

### Deploy in order

Deploy the API first. Its release command runs Alembic before the new machine
receives traffic:

```powershell
fly deploy .\backend --config .\backend\fly.toml
fly status --app nfl-confidence-api
fly logs --app nfl-confidence-api
Invoke-RestMethod https://nfl-confidence-api.fly.dev/api/v1/health
Invoke-RestMethod https://nfl-confidence-api.fly.dev/api/v1/health/ready
```

The readiness response must report `database: healthy`. For the selected $0
pilot, it should report `scheduler: disabled`; it should report
`scheduler: running` only when automated jobs are intentionally enabled on a
single API machine. A 503 means the machine must not receive traffic; inspect
`fly logs` before proceeding. The deployment release command is safe to rerun
because Alembic tracks the applied revision.

Then deploy the frontend:

```powershell
fly deploy .\frontend --config .\frontend\fly.toml
fly status --app nfl-confidence-web
Invoke-WebRequest https://nfl-confidence-web.fly.dev/
```

The frontend config builds against `/api/v1`; Nginx proxies that path to the API.
If either Fly app name changes, update `frontend/fly.toml` and
`frontend/nginx.frontend.conf`, deploy the frontend again, and set the backend
`APP_URL`, `CORS_ORIGINS`, and `GOOGLE_OAUTH_REDIRECT_URL` to the final frontend
URL.

## Deployment smoke test

Run this against the deployed URLs with a real browser. Use a temporary test
week or perform the checks before inviting the pool:

1. Open `https://nfl-confidence-web.fly.dev/` and sign in with Google. Confirm
	the browser returns to the frontend and a refresh preserves the session. In
	a private/incognito window, confirm the post-redirect request is to
	`https://nfl-confidence-web.fly.dev/api/v1/auth/refresh`, the refresh cookie is
	`HttpOnly` and scoped to `/api/v1/auth`, and logout remains effective after reload.
2. As commissioner, create the private league and send an invite. Accept it
	with a second Google account and verify both members appear.
3. Import the first week from the backend container or a local operator shell:
	`fly ssh console --app nfl-confidence-api -C "python -m app.jobs.nfl_schedule --season 2026 --week 1"`.
	If the image does not contain the module path expected by your shell, run the
	equivalent schedule-import command from the backend source inside the VM.
4. Submit one complete set of picks. Confirm `GET /api/v1/weeks/current`
	exposes the earliest kickoff in `locksAt`.
5. After that kickoff, confirm the UI is read-only and a direct `POST
	/api/v1/picks` receives a validation error.
6. Invoke a score sync in a production-like environment, or wait for a real
	final game. Confirm history, weekly standings, tie handling, and the payout
	values update. Re-run the sync and verify totals do not change.
7. Create an incomplete member and a complete member before Wednesday's
	reminder time. Run the reminder callable once, confirm only the incomplete
	member receives mail, then run it again and confirm no duplicate delivery.
8. Review `fly logs --app nfl-confidence-api` for schedule import, score sync,
	lock, reminder, and failure messages. Restart the machine and verify the
	data and readiness probe survive.

Keep the manual import and sync commands available during the first live week;
they are the recovery path for an ESPN outage or missed scheduler window.

## Google OAuth troubleshooting

If Google account selection returns an API `Internal Server Error`, watch the
API logs while reproducing the login. Do not paste or replay the callback URL:
its `code` and `state` query values are sensitive and single-use.

```powershell
fly logs --app nfl-confidence-api
fly secrets list --app nfl-confidence-api
```

The secrets list should contain `DATABASE_URL`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, and `JWT_SECRET`; it does not display their values.
`JWT_SECRET` must be a non-default production secret because it signs access
tokens and protects the OAuth session state.

The Google OAuth client must use these exact production URLs:

- JavaScript origin: `https://nfl-confidence-web.fly.dev`
- Redirect URI: `https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback`

The callback should finish with a `303` redirect to the frontend. A `401`
indicates a provider, session, or incomplete-claims authentication failure; a
`409` indicates that the Google email is already linked to a different Google
account. Any remaining `500` should be investigated in the Fly logs, especially
for database connectivity or migration errors.

With `ENABLE_SCHEDULER=false`, run the recurring operations from the backend
directory with the manual job dispatcher:

```powershell
.venv\Scripts\python.exe -m scripts.import_nfl_schedule --season 2026 --week 1
.venv\Scripts\python.exe -m scripts.run_job lock
.venv\Scripts\python.exe -m scripts.run_job sync
.venv\Scripts\python.exe -m scripts.run_job reminders
```

Run `lock` around the earliest kickoff, `sync` during and after live games, and
`reminders` at the configured reminder time. Each command uses the configured
`DATABASE_URL` and prints its affected-row count.

---

# Continuous Integration

Every Pull Request

- Install dependencies
- Run linter
- Run backend tests
- Run frontend tests
- Build frontend
- Build backend
- Build Docker images

---

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

---

# Monitoring

Liveness endpoint

/api/v1/health

Readiness endpoint

/api/v1/health/ready

The liveness endpoint only confirms that the FastAPI process is responding. The
readiness endpoint also verifies the database connection and embedded scheduler;
configure Fly's HTTP health check against `/api/v1/health/ready` so traffic is not
routed to an instance that cannot run the scheduled pool jobs.

Application logs

Application logs currently use the container's standard output. Scheduled job
failures are logged with the job id and traceback; collect these logs in the
hosting platform before enabling automated production alerts.

Database backups

Daily

Retention

30 days

---

# Rollback

Previous Docker image retained.

Rollback requires:

- Previous image
- Previous migration state
- Verification health check

## Operational schedule

The API process owns one APScheduler instance. It imports the next unimported
week on Tuesday at 10:00 AM Eastern, checks for expired picks every minute,
syncs scores hourly during the configured Sunday and Monday/Thursday windows,
and sends weekly reminders on Wednesday at 6:00 PM Eastern. A fresh production
database must be migrated and seeded with the active league before the Tuesday
import can run; use the backend schedule import CLI for the initial week.
