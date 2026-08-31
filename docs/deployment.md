# Deployment

Version: 1.0

---

# Overview

The application will be deployed using Docker containers.

Hosting Platform

Fly.io

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

---

# Local Development

Run the frontend at `http://localhost:5173` and the backend at its local port. The
frontend calls `/api/v1` on its own origin, and Vite proxies `/api` to `BACKEND_URL`.
This keeps local browser requests same-origin, so the frontend does not need to know
the backend hostname and local CORS is not involved in the normal workflow.

Set `VITE_API_URL` only when the frontend must call an API hosted on a separate origin.
In that deployment, configure the backend `CORS_ORIGINS` allowlist to contain the exact
frontend origin; do not use `*` with credentialed requests.

---

# Docker

Frontend Dockerfile

Backend Dockerfile

docker-compose.yml for local development

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

Health endpoint

/api/v1/health

Application logs

Structured JSON

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
