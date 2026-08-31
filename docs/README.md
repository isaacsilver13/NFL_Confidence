# NFL Confidence Pool

A modern web application for running private NFL Confidence Pick'em leagues.

## Overview

NFL Confidence Pool allows commissioners to create private leagues where members assign a unique confidence value to every NFL game each week.

If a pick is correct, the user earns the confidence value assigned.

If a pick is incorrect or the game ends in a tie, the user earns zero points.

The application automatically imports NFL schedules, locks picks at kickoff, updates scores throughout the week, and maintains weekly and season-long leaderboards.

---

## Features

- Google Authentication
- Private invite-only leagues
- Weekly confidence picks
- Automatic NFL schedule import
- Automatic scoring
- Live leaderboard updates
- Weekly winners
- Season standings
- Weekly team and confidence pick distributions
- Private completed-week pick history
- Email reminders
- Commissioner dashboard
- Mobile-first responsive design

Future versions include:

- Entry fee collection
- Prize payouts
- Survivor pools
- Advanced statistics
- Multiple scoring systems

---

## Tech Stack

Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- React Router

Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic

Infrastructure

- Docker
- Fly.io
- GitHub Actions

Authentication

- Google OAuth

---

## Design Principles

- Mobile-first
- Fast
- Simple
- Automatic whenever possible
- Minimal commissioner intervention
- Highly reliable scoring
- Clear user interface

## Local Analytics Fixture

After applying the database migrations, run the historical leaderboard fixture from
`backend`:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m scripts.seed_leaderboard_data --season 2026
```

The command creates ten completed historical weeks (weeks 2-11), eight final games per
week, five members, and deterministic picks and leaderboard aggregates. It is protected
by a database marker and should be run once. A later invocation exits with an
`already seeded` message without changing the fixture.
