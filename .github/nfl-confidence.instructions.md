---
applyTo: "{frontend,backend}/**/*.{ts,tsx,css,py}"
---

# NFL Confidence Instructions

NFL Confidence is a single-league confidence-pool app. Its frontend is React
19, TypeScript, Vite, React Router, TanStack Query, and Tailwind CSS v4. Its
backend is FastAPI on Python 3.10, SQLAlchemy, PostgreSQL, Alembic, and
Pydantic v2. The frontend development server proxies `/api` to the backend.

## Structure and data flow
- Keep FastAPI route handlers in `backend/app/api/` thin. Put business rules in
  `backend/app/services/`, database queries in `backend/app/repositories/`,
  SQLAlchemy models in `backend/app/models/`, and request/response schemas in
  `backend/app/schemas/`.
- Preserve the API envelope in `backend/app/core/responses.py`: successful
  responses contain `data` and `message`; failures contain `error.code`,
  `error.message`, and optional `error.details`.
- Use the frontend `apiFetch<T>()` client in `frontend/src/api/client.ts` for
  API calls. It owns in-memory access-token handling, one refresh-and-retry for
  401 responses, and conversion of error envelopes into `ApiError`.
- Use TanStack Query for server state. Colocate fetch/mutation functions under
  `frontend/src/api/`, keep transient form state in the owning component with
  `useState`, and invalidate the relevant query keys after successful mutations.
  Do not add a global client-state store for local UI state.

## Permissions and roles
- The only current roles are `LeagueRole.OWNER` and `LeagueRole.MEMBER` in
  `backend/app/models/enums.py`; an owner is the commissioner.
- Authorize sensitive backend actions with dependency injection:
  `get_current_user`, then `get_active_league_member`, and
  `get_active_league_owner` for commissioner-only routes. UI role checks are
  only for visibility; never rely on them as authorization.
- Read the frontend role from `SessionBootstrap.membership.role` and mirror the
  existing conditional rendering pattern. When adding a role or permission,
  update the enum, dependencies, endpoint coverage, session/types, and UI
  visibility together, with explicit tests for allowed and forbidden users.

## Forms, validation, and saving
- Existing forms use explicit HTML `onSubmit` handlers, component-local draft
  state, `useMutation`, and inline success/error feedback. Do not introduce a
  different form library for a small change just because React Hook Form and
  Zod are installed.
- Preserve client-side guards before a mutation, such as the locked-week and
  complete/unique confidence validation in `frontend/src/pages/PicksPage.tsx`.
  Keep server validation in Pydantic schemas and existing domain errors
  (`ValidationError`, `ConflictError`, `ForbiddenError`, and related errors).
- Catch `ApiError` at the UI boundary and present its message as inline form
  feedback; this app does not use a toast system. Clear stale feedback when the
  user changes the affected draft.
- For live-save changes, retain validation and errors, guard against writes
  after locked/disabled states, avoid overlapping or stale writes, and refresh
  the same query keys the submit flow refreshed.

## UI and assets
- Style with Tailwind utility classes and the theme tokens from
  `frontend/src/index.css`. Reuse `frontend/src/components/ui/Button.tsx` and
  its established variants for actions; do not add CSS modules, CSS-in-JS, or a
  second component library.
- NFL logos are data-driven: `frontend/src/assets/teamLogos.ts` maps ESPN team
  codes to `/logos/<CODE>.png`, and `frontend/src/components/nfl/TeamLogo.tsx`
  handles loading and fallback rendering. Trace the manifest, consumers, and
  public asset before changing any image path; preserve accessible alt text and
  the fallback behavior.

## Testing and validation
- Frontend tests use Vitest and React Testing Library. Run the narrow relevant
  test when available, then use `npm run test`, `npm run lint`, or `npm run
  build` as appropriate from `frontend/`.
- Backend tests use pytest and httpx `TestClient` fixtures from
  `backend/tests/conftest.py`. Assert the response envelope, including error
  codes, and run targeted pytest tests before the backend suite. Backend style
  is checked with Ruff and Black as configured in `backend/pyproject.toml`.

## Communication
- Flag any assumption you had to make in your response.
- If a change affects shared logic used by multiple roles or views,
  call that out.
