# GitHub Copilot Prompts

Version 1.0

Use these prompts while implementing the project.

---

## Database

Create SQLAlchemy 2.0 models from docs/03-database-design.md.

Use UUID primary keys.

Use relationships.

Generate Alembic migrations.

---

## Repository

Create repository classes for every model.

Repositories should only perform CRUD operations.

No business logic.

---

## Services

Create service classes.

Business logic belongs only here.

Use dependency injection.

Raise custom exceptions.

---

## API

Implement the REST endpoints described in docs/04-api-specification.md.

Generate:

- Request models
- Response models
- Validation
- Tests

---

## Frontend

Build React pages from docs/06-frontend-specification.md.

Requirements

- React
- TypeScript
- Tailwind
- shadcn/ui
- TanStack Query

---

## Forms

Use React Hook Form.

Validate with Zod.

Display inline validation.

---

## Tables

Create responsive tables.

Sortable columns.

Loading states.

Empty states.

---

## Leaderboards

Generate reusable leaderboard components.

Desktop and mobile layouts.

---

## Dashboard

Build the Dashboard page.

Use reusable cards.

Display:

Current Week

Countdown

Weekly Rank

Season Rank

Upcoming Games

Leaderboard Preview

---

## Testing

Generate unit tests.

Generate integration tests.

Generate Playwright tests.

---

## Refactoring

Refactor code without changing behavior.

Reduce duplication.

Improve readability.

Maintain tests.
