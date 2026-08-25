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

VITE_API_URL

Backend

DATABASE_URL

GOOGLE_CLIENT_ID

GOOGLE_CLIENT_SECRET

JWT_SECRET

RESEND_API_KEY

NFL_API_KEY

APP_URL

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
