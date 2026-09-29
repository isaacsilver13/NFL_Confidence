# Background Jobs

Version 1.0

---

# Purpose

Automate every repetitive task.

---

## How jobs are triggered

The app does not run its own cron. It sleeps between requests (Fly auto-stop), so a
GitHub Actions workflow calls `POST /api/v1/internal/tick` (hourly inside the game windows, a few times a day
otherwise; see the workflow's cron lines), which also wakes the machine. The app then runs whichever jobs are due at that moment, in
`America/Chicago`, and each job runs at most once per clock-hour slot. See
`docs/deployment.md` ("Scheduled jobs") for setup, and `backend/app/jobs/schedule.py`
for the rules.

| Job | When (America/Chicago) | Setting(s) |
|---|---|---|
| Sunday score sync | Sun, hourly 10:00-23:00 (23:00 included) | `SUNDAY_SYNC_START_HOUR`, `SUNDAY_SYNC_END_HOUR` |
| Mon/Thu score sync | Mon and Thu, hourly 19:00-22:00 | `MONTHU_SYNC_START_HOUR`, `MONTHU_SYNC_END_HOUR` |
| Overnight score sync | Daily 02:00 | `OVERNIGHT_SYNC_HOUR` |
| Next-week import | Tue 09:00 | `IMPORT_DAY`, `IMPORT_HOUR` |
| Weekly picks reminder | Wed 17:00 | `REMINDER_DAY`, `REMINDER_HOUR` |
| Pick lock | Every hour | |

The sections below describe each job's purpose; the cadences written in them are the
original design, and the table above is what runs.

---

## Import Schedule

Runs

Tuesday

Imports

Current NFL Week

Games

Kickoff Times

Venue and location

Favorite-side spread when available

The callable local entry point is `python -m scripts.import_nfl_schedule --season YEAR --week WEEK`.
ESPN odds and venue fields are optional; missing values are stored as null and do not reject an event.

---

## Lock Games

Runs

Every Minute

Locks games whose kickoff has passed.

---

## Update Scores

Runs

Every Minute During Live Games

Updates

Scores

Status

Winning Team

---

## Calculate Weekly Scores

Runs

Whenever A Game Becomes Final

Updates

User Scores

Leaderboard

Weekly Results

---

## Calculate Season Standings

Runs

After Weekly Score Update

Updates

Overall Rankings

Weekly Wins

---

## Reminder Emails

Thursday

6 PM

Sunday

9 AM

30 Minutes Before Kickoff

---

## Cleanup

Runs Nightly

Deletes

Expired Sessions

Expired Invites

Old Logs

---

## Health Check

Runs Every Five Minutes

Checks

Database

NFL API

Email Service
