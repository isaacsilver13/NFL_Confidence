# Background Jobs

Version 1.0

---

# Purpose

Automate every repetitive task.

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
