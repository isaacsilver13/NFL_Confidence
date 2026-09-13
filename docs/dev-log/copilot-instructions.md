# GitHub Copilot Instructions

Project: NFL Confidence Pool

Version: 1.0

---

## Purpose

This repository contains a production-quality web application for managing a private NFL Confidence Pool.

GitHub Copilot should always prioritize:

- Readability
- Simplicity
- Type safety
- Testability
- Maintainability

This application is intended to be maintained for many NFL seasons.

Never optimize for writing fewer lines of code.

Always optimize for code that another developer can quickly understand.

---

# Project Overview

Users join a private NFL confidence pool.

Every week users:

- Pick the winner of every NFL game
- Assign one unique confidence value to every game

Correct picks earn confidence points.

Incorrect picks earn zero.

NFL ties earn zero.

Games automatically lock at kickoff.

Scores update automatically.

Weekly and season standings are calculated automatically.

This application supports **NFL confidence pools only**.

Do not generate abstractions for other sports.

---

# General Principles

Prefer explicit code.

Avoid clever solutions.

Avoid unnecessary abstractions.

Prefer composition over inheritance.

Keep functions short.

Keep classes focused.

Business logic belongs in Services.

Database access belongs in Repositories.

API routes should be thin.

React components should focus on rendering.

---

# Backend Rules

Use FastAPI.

Use SQLAlchemy ORM.

Never write raw SQL unless performance absolutely requires it.

Every endpoint should:

Validate request

↓

Call Service

↓

Return Response

Routes should never contain business logic.

Business rules belong in Services.

Repositories should only perform database operations.

---

# Frontend Rules

Use React functional components only.

Never use class components.

Keep components focused on one responsibility.

Business logic belongs inside custom hooks.

Avoid prop drilling.

Prefer reusable UI components.

Use shadcn/ui whenever practical.

Prefer accessibility over visual effects.

---

# TypeScript Rules

Strict mode is enabled.

Never use "any".

Prefer explicit interfaces.

Always type API responses.

Always type component props.

Never suppress compiler warnings without documenting why.

---

# Python Rules

Use Python type hints everywhere.

Prefer dataclasses or Pydantic models where appropriate.

Never ignore exceptions.

Never use bare except blocks.

Raise meaningful exceptions.

Keep functions under approximately 40 lines when practical.

---

# Naming

Variables

Use descriptive names.

Good

weeklyLeaderboard

currentWeek

confidenceValue

Bad

data

obj

thing

tmp

Classes

Use PascalCase.

Functions

Use snake_case in Python.

Use camelCase in TypeScript.

Constants

UPPER_CASE.

Database tables

snake_case.

API routes

kebab-case.

---

# API Design

Use REST.

JSON only.

Return consistent response structures.

Success

{
    "data": ...
}

Failure

{
    "error": {
        "code": "...",
        "message": "..."
    }
}

Use proper HTTP status codes.

---

# Validation

Validate every request.

Never trust client input.

Return useful validation errors.

Use Pydantic on the backend.

Use Zod on the frontend.

---

# Error Handling

Never expose stack traces.

Log unexpected exceptions.

Provide user-friendly error messages.

Every API failure should include:

- Error code
- Message

Avoid vague messages.

---

# Database

Use SQLAlchemy relationships.

Prefer foreign keys.

Normalize tables.

Create indexes for frequently queried columns.

Avoid duplicated data.

Never store calculated values unless justified.

---

# Authentication

Google OAuth only.

Use JWT access tokens.

Use refresh tokens.

Protect all authenticated routes.

Do not implement username/password authentication.

---

# Performance

Avoid unnecessary queries.

Avoid N+1 database problems.

Use eager loading when appropriate.

Cache only when there is measurable benefit.

Optimize readability before optimization.

---

# Testing

Every new feature should include tests.

Service layer

Unit tests.

API layer

Integration tests.

Critical user flows

End-to-end tests.

Never merge code without tests.

---

# Logging

Log:

Authentication events

Errors

Background jobs

Failed validations

Long-running requests

Do not log:

Passwords

Access tokens

Refresh tokens

Sensitive user information

---

# Background Jobs

Background jobs should be idempotent.

Jobs may run more than once.

Design them so duplicate execution does not corrupt data.

---

# UI Guidelines

Mobile-first.

Simple.

Clean.

Fast.

Minimal animations.

Consistent spacing.

Large touch targets.

Loading skeletons where appropriate.

Empty states should explain what users need to do next.

---

# Accessibility

Every form control must have labels.

Keyboard navigation should work.

Buttons should have accessible names.

Use semantic HTML.

Meet WCAG AA standards whenever practical.

---

# Security

Never trust client data.

Use parameterized queries.

Escape output.

Store secrets in environment variables.

Require HTTPS.

Implement rate limiting.

Never commit secrets.

---

# Documentation

Every Service should include a docstring.

Complex logic should include explanatory comments.

Do not comment obvious code.

Document why something exists rather than what it does.

---

# Preferred Development Workflow

When implementing a feature:

1. Update database model if necessary.

2. Create migration.

3. Create schema.

4. Create repository.

5. Create service.

6. Create API endpoint.

7. Write backend tests.

8. Update frontend API client.

9. Create UI components.

10. Write frontend tests.

11. Update documentation if behavior changes.

---

# Preferred Pull Requests

Small.

Focused.

One feature per pull request.

Avoid mixing unrelated changes.

---

# If Requirements Are Ambiguous

Do not invent new product requirements.

Instead:

Choose the simplest implementation that satisfies the existing documentation.

Leave TODO comments only when explicitly instructed.

Never add speculative features.

---

# Final Principle

This project values maintainability over cleverness.

Future developers should be able to understand any file within a few minutes.

When in doubt, choose the implementation that is easiest to read and maintain.
