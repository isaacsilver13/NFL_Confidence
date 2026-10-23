# NFL Confidence Pool

A full-stack web application for running private NFL confidence-pick'em leagues.

Commissioners can create invite-only leagues, and members assign a unique confidence value to each NFL game every week. Correct picks earn their assigned value; incorrect picks and ties earn zero. The app imports schedules, locks picks at kickoff, scores completed games, and maintains weekly and season-long leaderboards.

## Highlights

- Private leagues with commissioner tools and member invitations
- Weekly confidence picks, automatic scoring, and leaderboards
- Schedule and score updates with kickoff-based pick locking
- Mobile-first React interface with a FastAPI backend
- Separate local, development, and production deployment configurations

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, and TanStack Query
- Backend: FastAPI, SQLAlchemy, Alembic, and PostgreSQL
- Delivery: Docker Compose, GitHub Actions, and Fly.io

## Local development

The root Docker Compose configuration starts PostgreSQL, the backend, and the frontend together:

```powershell
docker compose up --build
```

For the complete setup, test commands, architecture, security model, and deployment guidance, see [the documentation](docs/README.md).

## Project status

This is an actively developed personal project. It is intended for private confidence-pool leagues and does not process entry fees or prize payouts.
