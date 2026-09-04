# Testing Strategy

Version: 1.0

---

# Philosophy

Automated tests are required for every feature.

---

# Backend

Unit Tests

Services

Repositories

Validation

Scoring

Leaderboard calculations

Integration Tests

API endpoints

Authentication

Database operations

Background jobs

---

# Frontend

Component Tests

Rendering

Validation

Loading states

Error states

Custom hooks

---

# End-to-End

Login

Join league

Submit picks

Edit picks

View leaderboard

Notification preferences

---

# Performance Tests

Leaderboard

<500 ms

Dashboard

<1 second

Picks page

<1 second

---

# Regression Tests

Scoring

Confidence validation

Locking games

Authentication

Leaderboard ranking

---

# Coverage

Long-term target

- Backend: 90% line coverage
- Frontend: 80% line coverage

CI-enforced gate

- Backend: 77% line coverage
- Frontend: 77% statements, 68% branches, 75% functions, and 78% lines

The CI gate starts at the measured baseline and will be ratcheted upward over time
toward the long-term target. The backend baseline excludes the currently date-sensitive
pick-lock fixture failures until those tests are repaired.

---

# Manual Testing Checklist

Google login

Invite flow

Create picks

Edit unlocked picks

Locked games

Leaderboard

Weekly scoring

Season standings

Responsive layout

Dark mode
