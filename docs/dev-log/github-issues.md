# GitHub Issues

Version 1.0

This document defines the initial implementation backlog.

Each issue should become a GitHub Issue.

---

# Epic 1 - Project Setup

## Issue 1

Title

Initialize Repository

Tasks

- Create frontend
- Create backend
- Configure gitignore
- Configure prettier
- Configure eslint
- Configure black
- Configure isort

Acceptance Criteria

- Project runs locally
- Lint passes
- Formatters configured

---

## Issue 2

Configure Docker

Tasks

- Dockerfile frontend
- Dockerfile backend
- docker-compose
- PostgreSQL service

Acceptance Criteria

docker compose up starts the entire application.

---

## Issue 3

GitHub Actions

Tasks

- Backend tests
- Frontend tests
- Lint
- Build

Acceptance Criteria

Every pull request runs CI automatically.

---

# Epic 2 - Authentication

## Issue 4

Google OAuth

Acceptance Criteria

- Login works
- Logout works
- Session persists

---

## Issue 5

JWT Authentication

Acceptance Criteria

Protected endpoints require authentication.

---

## Issue 6

User Model

Acceptance Criteria

Users stored in PostgreSQL.

---

# Epic 3 - League

## Issue 7

League Model

---

## Issue 8

League Invite API

---

## Issue 9

Accept Invite Flow

---

## Issue 10

League Dashboard

---

# Epic 4 - NFL Data

## Issue 11

Create NFL Data Provider Interface

---

## Issue 12

Schedule Import Job

---

## Issue 13

Game Sync Job

---

## Issue 14

Store Games

---

## Issue 15

Weekly Schedule API

---

# Epic 5 - Picks

## Issue 16

Pick Model

---

## Issue 17

Create Picks API

---

## Issue 18

Update Picks API

---

## Issue 19

Confidence Validation

Acceptance Criteria

- Duplicate confidence values rejected
- Missing confidence values rejected
- Invalid team rejected

---

## Issue 20

Lock Picks

Acceptance Criteria

Games become immutable after kickoff.

---

# Epic 6 - Scoring

## Issue 21

Score Calculation Service

---

## Issue 22

Weekly Leaderboard

---

## Issue 23

Season Leaderboard

---

## Issue 24

Weekly Winners

---

## Issue 25

Rank Calculations

---

# Epic 7 - Notifications

## Issue 26

Reminder Preferences

---

## Issue 27

Thursday Reminder

---

## Issue 28

Sunday Reminder

---

## Issue 29

Kickoff Reminder

---

## Issue 30

Weekly Results Email

---

# Epic 8 - Frontend

## Issue 31

Dashboard

---

## Issue 32

Picks Page

---

## Issue 33

Leaderboard

---

## Issue 34

Profile

---

## Issue 35

League Settings

---

# Epic 9 - Production

## Issue 36

Logging

---

## Issue 37

Monitoring

---

## Issue 38

Health Checks

---

## Issue 39

Security Review

---

## Issue 40

Production Launch
