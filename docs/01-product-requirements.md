# Product Requirements Document

Version 1.0

---

# Vision

Create the easiest and most reliable way for small groups to run an NFL Confidence Pool.

The application should remove spreadsheets, manual scorekeeping, and commissioner overhead while providing a polished experience comparable to commercial fantasy sports applications.

---

# Goals

Primary goals

- Members can submit picks in under two minutes.
- Scores update automatically.
- Weekly winners are automatically calculated.
- Season standings are always accurate.
- Mobile experience is first-class.

---

# Non Goals

Version 1 will NOT include

- Native mobile applications
- Fantasy football
- Sports betting
- Public leagues
- Chat
- Ads

---

# Target Users

### Commissioner

Responsibilities

- Create league
- Invite members
- Configure season
- Configure payouts
- Manage reminders

Restrictions

Cannot edit picks

Cannot edit scores

Cannot edit game results

---

### Member

Responsibilities

- Join league
- Submit weekly picks
- Assign confidence values
- View standings
- Receive reminders

---

# League Rules

Private invite-only.

Maximum members: 20 (configurable later).

Google account required.

One commissioner.

One season per league.

One pick per game.

Confidence numbers must be unique.

Example

17 games

Confidence values

1–17

Each number must be used exactly once.

Correct pick

Earn confidence points.

Incorrect pick

Zero points.

Tie game

Zero points regardless of selected team.

---

# Weekly Flow

Tuesday

NFL schedule imported.

Wednesday

Members begin making picks.

Thursday kickoff

Thursday games lock individually.

Sunday kickoff

Sunday games lock individually.

Monday Night Football

Last games lock.

After each game finishes

Scores recalculate automatically.

Tuesday morning

Weekly winners finalized.

---

# Functional Requirements

Authentication

- Google Sign-In
- Secure sessions
- Invite-only registration

League

- Create league
- Join league
- Invite users
- Leave league

Picks

- Select winner
- Assign confidence
- Edit until kickoff
- Auto-save progress
- Submit confirmation

Scoring

- Automatic scoring
- Weekly leaderboard
- Season leaderboard
- Tiebreak detection

Notifications

- Thursday reminder
- Sunday reminder
- 30-minute kickoff warning

Administration

- Configure payouts
- Configure season
- Invite users

---

# Success Metrics

95% of users submit picks in under two minutes.

Zero manual score corrections.

No commissioner intervention after kickoff.

Application uptime >99%.

Average page load under one second.
