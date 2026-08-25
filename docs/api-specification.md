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
      "status": "SCHEDULED"
    }
  ]
}

---

## GET /games/{id}

Returns game details.

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

Returns historical picks.

Filter

Season

Week

---

# Leaderboard

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

Returns profile.

Includes

Season stats

Weekly finishes

Overall accuracy

Confidence accuracy

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
