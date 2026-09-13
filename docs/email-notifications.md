# Email Notifications

Version: 1.0

---

# Purpose

Email reminders help ensure league members submit picks on time.

All emails should be concise, mobile-friendly, and include a direct link back to the relevant page in the application.

---

# Notification Types

## League Invitation

Trigger:
Commissioner invites a new member.

Subject:
You're invited to join <League Name>

Body:

- League name
- Commissioner name
- Invitation link
- Expiration date

---

## Thursday Reminder

Trigger:
Thursday at 6:00 PM (league timezone)

Send only if:

- User has not submitted all picks.

Subject:
Don't forget your NFL Confidence Picks

Body:

- Current NFL week
- Number of picks remaining
- Link to Picks page

---

## Sunday Reminder

Trigger:
Sunday at 9:00 AM

Send only if:

- Sunday games remain unpicked.

Subject:
Sunday games lock soon

---

## Kickoff Reminder

Trigger:
30 minutes before the next unlocked game.

Do not send if:

- User has completed all eligible picks.

---

## Weekly Results

Trigger:
After Monday Night Football is finalized.

Subject:
Week X Results

Body:

- Weekly rank
- Weekly points
- Correct picks
- Link to leaderboard

---

## Season Update

Trigger:
Tuesday morning

Subject:
Season Standings Updated

Body:

- Current season rank
- Total points
- Weekly winner
- Link to standings

---

# Delivery Rules

Retry failed sends up to 3 times.

Log all deliveries.

Track:

- Sent
- Delivered
- Failed
- Opened (future)

Never send duplicate reminders.

Respect user notification preferences.
