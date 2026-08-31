# API Specification

Version: 1.0

Base URL

/api/v1

Content-Type

application/json

Authentication

Bearer JWT

All authenticated endpoints require a valid JWT access token.

---

# Standard Response Format

Success

{
  "data": {},
  "message": null
}

Error

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Confidence values must be unique.",
    "details": []
  }
}

---

# Authentication

## GET /auth/google/login

Description

Redirects the user to Google OAuth.

Authentication

None

Response

302 Redirect

---

## GET /auth/google/callback

Description

Handles the Google OAuth callback.

Authentication

None

Response

200

Returns

- Access Token
- Refresh Token
- User Profile

---

## POST /auth/logout

Description

Invalidates the refresh token.

Authentication

Required

Response

204 No Content

---

## GET /auth/me

Returns the currently authenticated user.

Authentication

Required

Response

{
  "data": {
    "id": "...",
    "displayName": "...",
    "email": "...",
    "avatarUrl": "..."
  }
}

---

# League

## GET /league

Returns league information.

Authentication

Required

Returns

League name

Current season

Number of members

Commissioner

Invite code

---

## GET /league/members

Returns all league members.

Authentication

Required

Sorted alphabetically.

---

## POST /league/invite

Creates an invite.

Authentication

Commissioner only.

Request

{
  "email": "friend@email.com"
}

Returns

Invite created.

---

## POST /league/join

Join using invite token.

Request

{
  "token": "abc123"
}

---

# Weeks

## GET /weeks/current

Returns current NFL week.

Authentication

Required

Returns

Week number

Status

Start date

End date

---

## GET /weeks

Returns every week.

Used for historical standings.

---

# Games

## GET /games/current

Returns current week's games.

Ordered by kickoff.

Example

{
  "data": [
    {
      "id": "...",
      "awayTeam": "CHI",
      "homeTeam": "GB",
      "kickoff": "...",
      "status": "SCHEDULED",
      "venueName": "Lambeau Field",
      "venueLocation": "Green Bay, WI",
      "spreadTeam": "GB",
      "spread": -3.5
    }
  ]
}

---

## GET /games/{id}

Returns game details, including venue and favorite-side spread when supplied by the schedule/odds
feed. `venueName`, `venueLocation`, `spreadTeam`, and `spread` may be null when the source does not
provide those values.

Including

Current score

Status

Winning team

Kickoff

---

# Picks

## GET /picks/current

Returns authenticated user's picks.

Authentication

Required

---

## POST /picks

Creates or updates all picks for the week.

Request

{
  "week": 4,
  "picks": [
    {
      "gameId": "...",
      "team": "GB",
      "confidence": 16
    }
  ]
}

Validation

Confidence values unique.

No duplicate games.

Game not locked.

Selected team must be playing.

Response

200

---

## GET /picks/history

Returns the authenticated user's historical picks for completed weeks in the active league season.

Each pick includes matchup, selected team, confidence value, game status, winning team or tie,
points earned, and an outcome of `correct`, `incorrect`, or `unscored`.

No user or member filter is accepted. The authenticated user is always the data scope.

---

# Leaderboard

## GET /leaderboard/pick-breakdown

Returns the completed-week pick breakdown for the active league.

Each week contains one row per game. A game row includes both matchup teams, the median confidence
points across distinct league-member picks, and each team's distinct user pick count. Games with no
submitted picks are still returned with a null median and zero counts. The frontend derives each
team's percentage from those counts and colors the bar with the team's established palette.

Example game row:

{
  "gameId": "...",
  "awayTeam": "CHI",
  "homeTeam": "GB",
  "medianConfidence": 4.5,
  "teamCounts": [
    {"team": "CHI", "userCount": 6},
    {"team": "GB", "userCount": 2}
  ]
}

## GET /leaderboard/week

Current weekly standings.

Returns

Rank

User

Points

Correct Picks

---

## GET /leaderboard/season

Season standings.

Returns

Rank

Total Points

Weekly Wins

Average Points

---

# Profile

## GET /profile

Returns the authenticated user's profile view and completed-week pick history.

It does not expose another member's picks or per-member trend statistics.

---

# Notifications

## GET /notifications/preferences

Returns reminder settings.

---

## PATCH /notifications/preferences

Update reminder preferences.

Request

{
  "emailEnabled": true,
  "thursdayReminder": true,
  "sundayReminder": true,
  "kickoffReminder": true
}

---

# Health

## GET /health

Returns

{
  "status": "healthy"
}

No authentication.

Used by Fly.io.

---

# Validation Rules

Google account required.

Invite required.

One pick per game.

Confidence values unique.

Confidence values

1...

Number of games that week.

Cannot edit locked games.

Cannot submit after kickoff.

Cannot pick both teams.

Cannot pick teams not playing.

---

# Status Codes

200

Success

201

Created

204

Deleted

400

Validation

401

Unauthorized

403

Forbidden

404

Not Found

409

Conflict

422

Invalid Input

429

Rate Limited

500

Unexpected Error

---

# Rate Limits

Authenticated

300 requests/hour

Unauthenticated

30 requests/hour

Health endpoint

Unlimited

---

# Pagination

All future collection endpoints use:

?page=1

&pageSize=25

Response

{
  "data": [],
  "pagination": {
    "page": 1,
    "pageSize": 25,
    "total": 150
  }
}

---

# Versioning

Every endpoint begins with

/api/v1

Future breaking changes create

/api/v2

Never break existing clients.

---

# OpenAPI

FastAPI should automatically generate

/swagger

and

/redoc

Every endpoint must include

Description

Request model

Response model

Status codes

Example payloads
