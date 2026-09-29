# Frontend Specification

Framework

React

Language

TypeScript

---

# Layout

Top Navigation

Main Content

Navigation is sticky. No footer.

---

# Pages

The app is mostly a single-page dashboard, not five separate routed pages.
`/login`, `/join`, `/` (dashboard), `/picks`, and `/league-settings` are real
routes. `/leaderboard`, `/standings`, and `/profile` are kept as redirects
(to `/#leaderboard` etc.) for old links/bookmarks, not pages of their own --
`/picks` used to redirect the same way but was promoted to its own top-level
nav tab.

## Login

Google Sign In

League Logo

Short Description

---

## Join League

Shown after sign-in when the user isn't yet a league member. Accepts a
league passcode.

---

## Dashboard

The one page members land on after sign-in. Shows the current league/week
summary and a link into the Picks tab, then three collapsible accordion
sections (Weekly Leaderboard, Season Standings, Profile) — expand/collapse
state persists per user (localStorage) and is deep-linkable via URL hash
(`/#leaderboard`, `/#standings`, `/#profile`).

## Picks

Its own top-level nav tab (`/picks`), not an accordion section. One card per
game.

Card contains

Away Team

Home Team

Kickoff

Team Buttons

Confidence Buttons

Status

Locked Indicator

### Weekly Leaderboard section

Defaults to the current (possibly in-progress) week, labeled "Live" while
the week isn't finished. A dropdown also lists every completed week.

Rank

Member

Correct

Points

Points Left (live week only)

### Season Standings section

Rank

Total Points

Correct / Incorrect Picks

### Profile section

Display Name

Current-week pick progress

Historical Picks (by completed week)

---

## Members

Commissioner-only page, routed at `/league-settings`.

- View league members and their read-only Google email addresses
- Edit display names
- Edit member or commissioner role
- Remove members
- View the shared league passcode
- Invite members by email
- Mark weekly payments and void unpaid picks

The page is shown to every member with the commissioner (`owner`) role. The
backend also enforces this permission for direct navigation or API requests.

---

# Components

Navbar

CountdownCard

GameCard

ConfidenceSelector

LeaderboardTable

StandingsCard

ProfileCard

InviteModal

LoadingSkeleton

ErrorMessage

SuccessToast

---

# Responsive Breakpoints

Mobile

0-767

Tablet

768-1023

Desktop

1024+

---

# Colors

Primary

NFL Blue

Accent

Green

Danger

Red

Background

Light Gray

Dark Mode

Supported

---

# Icons

Lucide Icons

Only

---

# Forms

React Hook Form

Zod Validation

Inline Errors
