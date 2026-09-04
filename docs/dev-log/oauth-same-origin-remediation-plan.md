# OAuth same-origin remediation plan

## Objective

Fix the production Google login loop seen in private browsing and browsers that
block third-party cookies. After a user completes Google account selection, the
application currently returns them to the frontend login page because the SPA
cannot use the refresh-token cookie issued by the separately hosted API.

Deliver a production deployment in which the browser talks only to
`https://nfl-confidence-web.fly.dev/api/v1`. The frontend's Nginx server will
proxy those requests to the API. This makes the OAuth state and refresh cookies
first-party cookies for the web application.

## Diagnosis to preserve

Current production has two origins:

- Frontend: `https://nfl-confidence-web.fly.dev`
- API: `https://nfl-confidence-api.fly.dev`

`frontend/fly.toml` currently builds the frontend with the API's absolute URL.
The Google callback is served by the API and sets `refresh_token` on the API
origin with `Secure; HttpOnly; SameSite=None`. The frontend then bootstraps by
calling `POST /auth/refresh` across origins. Private browsers commonly block
that cookie as third-party storage, so the refresh returns 401 and the SPA
shows the login page.

This is not a Google client-ID, account-picker, or frontend-routing issue.
The observed return to the login page is the expected UI response to the failed
session bootstrap.

## Scope and guardrails

- Do not weaken cookie security (do not remove `Secure` or `HttpOnly`).
- Do not rely on users enabling third-party cookies.
- Keep the API publicly reachable for health checks and operator tooling unless
  a separate infrastructure decision intentionally changes that.
- Keep production OAuth callback and state validation enabled.
- Do not overwrite existing uncommitted work. At the time of writing, the
  repository has uncommitted changes in backend auth code, auth tests, frontend
  Docker configuration, deployment documentation, and a new
  `frontend/nginx.frontend.conf`. Review and preserve those changes before
  editing.

## Target request flow

```text
Browser
  -> https://nfl-confidence-web.fly.dev/api/v1/auth/google/login
  -> Nginx proxy -> https://nfl-confidence-api.fly.dev/api/v1/auth/google/login
  -> Google
  -> https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback
  -> Nginx proxy -> API callback
  -> Set-Cookie on nfl-confidence-web.fly.dev; 303 to frontend /
  -> SPA POST /api/v1/auth/refresh (same origin, cookie included)
  -> authenticated application
```

## Implementation steps

### 1. Establish a clean change boundary

1. From `repos/NFL_Confidence`, run `git status --short` and `git diff`.
2. Determine whether the existing uncommitted OAuth hardening changes belong to
   the current work. Do not discard them. Coordinate with their author if
   necessary.
3. Create a feature branch or commit only changes that are part of this plan.
4. Review `frontend/nginx.frontend.conf`; it serves the SPA and proxies `/api/`
  to the backend.

### 2. Route production API requests through the frontend origin

Update `frontend/nginx.frontend.conf` with a `location /api/` block that proxies
to the API app. Required behavior:

```nginx
location /api/ {
    proxy_pass https://nfl-confidence-api.fly.dev;
    proxy_ssl_server_name on;
    proxy_ssl_name nfl-confidence-api.fly.dev;

    # Let FastAPI construct external URLs for the web app, not the upstream API.
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Notes:

- Do not add a trailing slash to `proxy_pass` in this form. The upstream must
  receive `/api/v1/...`, not a path with `/api` stripped.
- Retain the existing SPA fallback (`try_files ... /index.html`) and static-asset
  cache rules.
- Confirm the backend Docker command keeps `--proxy-headers` and
  `--forwarded-allow-ips=*`; it currently does. This is required for the
  forwarded HTTPS scheme to be trusted.
- Prefer an explicit callback setting in the backend (step 3) even when proxy
  headers work. It prevents a future proxy header change from silently breaking
  Google OAuth.

### 3. Make the OAuth callback URL explicit and public-origin based

Add a configuration value such as `GOOGLE_OAUTH_REDIRECT_URL` to
`backend/app/core/config.py`. In production, set it to:

```text
https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback
```

Recommended behavior:

- If `google_oauth_redirect_url` is configured, use it in `google_login`.
- Otherwise preserve the current `request.url_for("google_callback")` behavior
  for local development and tests.
- Add the setting to `backend/.env.example` with an empty local default and to
  the production deployment documentation.

This removes dependence on the upstream `Host` header for the OAuth redirect
URI while keeping development simple.

### 4. Build the frontend for same-origin API requests

In `frontend/fly.toml`, change the build argument to:

```toml
[build.args]
VITE_API_URL = "/api/v1"
```

The source already defaults to `/api/v1`; this explicit production setting is
important because the current Fly build overrides that default with the API's
absolute URL.

No React auth-flow rewrite should be necessary. `googleLoginUrl`,
`refreshAccessToken`, and `apiFetch` already derive their paths from
`VITE_API_URL` and use `credentials: 'include'`.

### 5. Cookie and CORS decisions

After the proxy is live, browser API requests are same-origin. Keep the refresh
cookie scoped to `/api/v1/auth` and keep it `Secure` and `HttpOnly`.

Choose and document one cookie policy:

1. Preferred: use `SameSite=Lax` in production because all browser-visible
   authentication traffic is now same-origin. This is more restrictive than
   `None` and still supports the top-level Google redirect callback.
2. Acceptable transitional option: leave `SameSite=None` temporarily. The
   same-origin proxy still fixes the private-window issue; tighten to `Lax` in a
   small follow-up after the end-to-end test passes.

Do not make this decision by assumption. Verify Google callback behavior in a
private window before changing the policy. If changing it now, update
`_set_refresh_cookie` and its tests.

`CORS_ORIGINS` may remain set to the web URL. It is no longer needed for normal
browser traffic, but retaining this explicit allowlist is safe for direct API
use. Do not change it to `*` because the application uses credentials.

### 6. Update Google Cloud OAuth configuration

In the Google Cloud Console OAuth client used by production:

- Add authorized JavaScript origin:
  `https://nfl-confidence-web.fly.dev` (already expected).
- Add authorized redirect URI:
  `https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback`.
- Keep the existing API callback URI temporarily during rollout only if it is
  needed to roll back. Remove unused redirect URIs after the rollout is stable.

The callback URI must match exactly: HTTPS, hostname, path, and no trailing
slash.

### 7. Update Fly configuration and secrets

Set the API secret/configuration:

```powershell
fly secrets set --app nfl-confidence-api `
  GOOGLE_OAUTH_REDIRECT_URL=https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback
```

Do not print or copy OAuth credentials, JWT secrets, or database URLs into
files, shell history, or chat.

Deploy the API before the frontend if code was added for the explicit redirect
URL. Deploy the frontend after Nginx proxy and `VITE_API_URL` changes are built.

## Required tests

### Backend unit tests

Add or update tests in `backend/tests/test_auth.py` to prove:

- configured `GOOGLE_OAUTH_REDIRECT_URL` is passed to Authlib's
  `authorize_redirect`;
- unconfigured local behavior still uses the request-derived callback URL;
- successful callback still returns 303 and sets a refresh cookie;
- cookie attributes match the chosen production policy.

Run:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m pytest tests/test_auth.py
```

Use the repository's existing test command or active virtual environment if
this path differs.

### Frontend tests and build

Add a focused test proving that the production build uses `/api/v1`, or verify
the generated bundle in CI. Do not hard-code the Fly API hostname in tests.

Run:

```powershell
Set-Location frontend
npm test -- --run
npm run build
```

### Nginx/proxy verification

Build the frontend Docker image and verify:

- `GET /` serves the SPA;
- `GET /api/v1/health` is proxied to the API and returns the API health JSON;
- `POST /api/v1/auth/refresh` reaches the API without a browser CORS request;
- a redirect from the login endpoint uses the web-origin callback URI.

Prefer a small container-based integration test if practical. At minimum,
inspect Nginx configuration with `nginx -t` in the built image and run a local
compose or equivalent smoke test with a backend.

### End-to-end acceptance test (mandatory)

Use a real browser after deployment, including a private/incognito window:

1. Open `https://nfl-confidence-web.fly.dev/`.
2. Click **Continue with Google** and sign in with a test account.
3. Confirm the browser returns to the authenticated application, not `/login`.
4. In DevTools Network, confirm the post-redirect refresh request is to
   `https://nfl-confidence-web.fly.dev/api/v1/auth/refresh`, not the API host.
5. Confirm the refresh token appears as an HttpOnly cookie for the web host,
   scoped to `/api/v1/auth`.
6. Reload the page; confirm the session persists.
7. Close and reopen a private window, repeat the flow, and confirm it works.
8. Test logout, then confirm a reload remains logged out.
9. Check API logs for OAuth state validation errors, callback errors, and 5xx
   responses while reproducing once.

## Deployment sequence

1. Review diff and run all focused tests.
2. Update Google Cloud to authorize the new web-origin callback URI.
3. Set the API redirect-URL secret/configuration.
4. Deploy API (only if backend changes were made); confirm readiness:
   `https://nfl-confidence-api.fly.dev/api/v1/health/ready`.
5. Deploy frontend with the same-origin build argument and Nginx proxy.
6. Confirm `https://nfl-confidence-web.fly.dev/api/v1/health` returns the API
   health response through the proxy.
7. Perform the mandatory private-window end-to-end test.
8. Monitor frontend and API Fly logs for at least one successful login and one
   refresh after deployment.

## Rollback plan

If the frontend proxy deployment fails:

1. Roll back the frontend app to the previous Fly release.
2. Leave the old API callback URI authorized in Google Cloud until rollback is
   complete, so existing production login remains functional.
3. If the API deployment introduced only the optional redirect URL setting,
   either clear that setting or roll back the API so its callback again matches
   the previous API-origin flow.
4. Reproduce with a non-private browser to confirm the old deployment is back
   to its known behavior. Note that private-window login will remain broken
   until the same-origin fix is restored.

## Completion criteria

- Production frontend bundle contains `/api/v1`, not
  `https://nfl-confidence-api.fly.dev/api/v1`.
- Web-origin `/api/v1/health` successfully proxies to the API.
- Google redirects to the web-origin callback URL.
- Private/incognito login reaches an authenticated route and survives reload.
- No CORS errors, OAuth state errors, or refresh 401s appear in the successful
  browser flow.
- Focused backend/frontend tests and production smoke test pass.
