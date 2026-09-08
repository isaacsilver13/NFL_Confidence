# Frontend Specification

Framework

React

Language

TypeScript

---

# Layout

Top Navigation

Main Content

Footer

Navigation is sticky.

---

# Pages

## Login

Google Sign In

League Logo

Short Description

---

## Dashboard

Current Week

Countdown

My Rank

Weekly Rank

Season Rank

Upcoming Games

Leaderboard Preview

---

## Picks

One card per game.

Card contains

Away Team

Home Team

Kickoff

Radio Buttons

Confidence Dropdown

Status

Locked Indicator

---

## Weekly Leaderboard

Rank

Name

Points

Correct Picks

Incorrect Picks

Prize Icon

---

## Season Leaderboard

Rank

Total Points

Weekly Wins

Top Three Finishes

---

## Profile

Avatar

Display Name

Season Statistics

Historical Picks

Weekly Finishes

---

## Members

Commissioner-only tab.

- View league members and their read-only Google email addresses
- Edit display names
- Edit member or commissioner role
- Remove members
- View the shared league passcode
- Invite members by email

The tab is shown to every member with the commissioner (`owner`) role. The
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
