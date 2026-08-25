# Database Design

Version: 1.0

Database:
PostgreSQL 17

ORM:
SQLAlchemy 2.0

---

# Design Principles

The database is designed around these principles:

- Normalize data where practical.
- Never duplicate information that can be derived.
- UUID primary keys for all application tables.
- Immutable game results once finalized.
- Automatic timestamps.
- Foreign key constraints everywhere.
- Explicit indexes for frequently queried data.

---

# Entity Relationship Diagram

User
 │
 │ 1
 │
 ├───────────────┐
 │               │
 │               │
League        Invite
 │
 │
 ├─────────────── LeagueMember
 │
 │
 ├─────────────── Week
 │                     │
 │                     │
 │                     Game
 │                       │
 │                       │
 │                    Pick
 │
 └────────────── WeeklyResult

---

# users

Stores authenticated users.

Columns

id
UUID
Primary Key

google_id
TEXT
Unique

email
TEXT
Unique

display_name
TEXT

avatar_url
TEXT
Nullable

created_at
TIMESTAMP WITH TIME ZONE

updated_at
TIMESTAMP WITH TIME ZONE

Indexes

google_id

email

---

# leagues

One league per application.

Version 1 only supports one league.

Columns

id
UUID

name

owner_id

season

invite_code

is_active

created_at

updated_at

Notes

Only one active league exists.

The schema supports future expansion but the application will enforce a single league.

---

# league_members

Maps users into the league.

Columns

id

league_id

user_id

joined_at

role

Enum

OWNER

MEMBER

Constraints

One user may only join once.

UNIQUE

league_id

user_id

---

# nfl_weeks

Stores NFL weeks.

Columns

id

season

week_number

start_date

end_date

status

Status Enum

PRESEASON

REGULAR

PLAYOFF

SUPER_BOWL

COMPLETE

---

# nfl_games

Stores every NFL game.

Columns

id

week_id

espn_game_id

kickoff_time

home_team

away_team

home_score

away_score

winning_team

game_status

is_tie

last_synced

created_at

updated_at

---

Game Status Enum

SCHEDULED

LIVE

FINAL

POSTPONED

CANCELLED

---

Indexes

week_id

kickoff_time

game_status

winning_team

---

# picks

Most important table.

One record per

User

Game

Columns

id

user_id

game_id

picked_team

confidence_value

submitted_at

locked_at

points_earned

Constraints

One pick per game.

UNIQUE

user_id

game_id

Confidence values must be unique for a user each week.

This rule is enforced in application logic and the database.

---

# weekly_results

Stores calculated weekly standings.

Columns

id

league_id

week_id

user_id

total_points

correct_picks

incorrect_picks

weekly_rank

created_at

Indexes

week_id

user_id

weekly_rank

---

# season_results

Stores cumulative standings.

Columns

id

league_id

user_id

season

total_points

weekly_wins

first_place_finishes

second_place_finishes

third_place_finishes

current_rank

updated_at

---

# invites

Tracks invitations.

Columns

id

league_id

email

token

expires_at

accepted_at

created_at

Indexes

token

email

---

# reminder_preferences

User notification settings.

Columns

id

user_id

email_enabled

thursday_reminder

sunday_reminder

kickoff_reminder

updated_at

---

# audit_log

Optional but recommended.

Every important action.

Examples

League created

Invite sent

Picks submitted

Reminder sent

Columns

id

user_id

action

entity

entity_id

metadata

created_at

---

# Relationships

User

↓

LeagueMember

↓

League

↓

Week

↓

Game

↓

Pick

↓

Weekly Result

↓

Season Result

---

# Cascade Rules

Delete User

↓

Delete Picks

↓

Delete Notification Preferences

Do NOT delete

Weekly Results

Season Results

Audit Logs

Historical league results should remain intact.

---

# Team Storage

Do NOT create a teams table.

Store official team abbreviations directly.

Examples

CHI

GB

DET

MIN

KC

BUF

PHI

BAL

Benefits

Simpler joins

Faster queries

No maintenance

---

# Time Handling

Store every timestamp in UTC.

Frontend converts to user's timezone.

Never store local times.

---

# Confidence Validation

A confidence number may only be used once.

Example

17 games

Allowed

17
16
15
...
1

Not allowed

17
17
15
...

Validation occurs

Frontend

Backend

Database transaction

All three must agree.

---

# Weekly Locking

Each game locks independently.

Example

Thursday game

Locks Thursday.

Sunday games remain editable.

Monday game remains editable.

This allows users to continue making picks for games that have not started.

---

# Scoring Rules

Correct Pick

points_earned = confidence_value

Incorrect Pick

points_earned = 0

NFL Tie

points_earned = 0

Cancelled Game

Ignored until commissioner decision (future enhancement)

---

# Database Indexes

users

email

google_id

league_members

league_id

user_id

games

week_id

kickoff_time

status

picks

user_id

game_id

weekly_results

week_id

weekly_rank

season_results

current_rank

---

# Migration Strategy

Every schema change must include

Alembic migration

Migration test

Rollback support

---

# Future Tables (Not in Version 1)

payments

transactions

weekly_prizes

push_notifications

email_queue

statistics

pick_trends

These are intentionally excluded until after the MVP is complete.
