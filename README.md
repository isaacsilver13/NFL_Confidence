# NFL Confidence Pool

A web app for running one private NFL confidence-pick'em league per deployment.

Members pick a team for each game and assign each confidence value once. Correct picks earn that value; incorrect picks and ties earn zero. Commissioners manage membership, invitations, and league settings.

## How it works

- The entire weekly card locks at the week's earliest kickoff. Sunday picks cannot be changed after a Thursday opener.
- A complete autosaved card counts as an entry; members can also submit it explicitly.
- Schedule imports and score refreshes feed weekly and season standings.
- Google sign-in protects member access. Local development has a separate development-login path.
- This is a single-league application. It does not collect entry fees or send prize payouts.

## Run locally

Copy `backend/.env.example` to `backend/.env` and review the local settings before starting the stack:

```powershell
Copy-Item backend/.env.example backend/.env
docker compose up --build
```

Database initialization, migrations, and deterministic seed data are covered in the [development and deployment guide](docs/deployment.md). See [testing strategy](docs/testing-strategy.md) for the backend, frontend, and browser checks.

## Stack and documentation

React, TypeScript, Vite, and TanStack Query on the frontend; FastAPI, SQLAlchemy, Alembic, and PostgreSQL on the backend. Docker, GitHub Actions, and Fly.io support delivery.

Start with the [documentation index](docs/README.md), [product rules](docs/01-product-requirements.md), and [architecture](docs/technical-architecture.md). Dated material under `docs/dev-log/` records development history and may describe superseded behavior.
