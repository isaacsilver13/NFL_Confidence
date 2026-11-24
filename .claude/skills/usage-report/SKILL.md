---
name: usage-report
description: Use when the user asks for the NFL Confidence usage report, user activity, who is logging in, how long people spend on the app, which pages or features are used or ignored, or daily-active charts, including the weekly scheduled report. Read-only against production through the Neon MCP.
---

# NFL Confidence usage report

Builds an HTML report from the events the app records (`login` from `audit_log`; `session_start`,
`page_view`, `section_open`, `heartbeat` from `usage_events`) plus the `picks` and `week_submissions` tables.

Rules: SELECT only. Never write to the database, never store or print a connection string,
and never start, wake, or poll anything on Fly. Use display names, not emails, in anything you
show the user.

## Steps

1. **Exclusion list.** Read `exclude.txt` in this folder (one email per line, `#` comments
   ignored; copy `exclude.example.txt` if missing). If it is missing or empty, run
   `SELECT display_name, email FROM users ORDER BY created_at` through the Neon `run_sql`,
   show the user the display names, ask which are test accounts (the league admin stays in),
   and write the chosen emails to `exclude.txt`. That file is git-ignored on purpose.
2. **Run the queries.** For each `-- name:` block in `queries.sql`, substitute `{{EXCLUDE}}`
   with the lower-cased, single-quoted emails joined by commas (`''` if none) and `{{SINCE}}`
   with the first Chicago day to count (`1970-01-01` for everything since tracking began, or
   today minus 7 days for the weekly report), run it with the Neon MCP `run_sql` against
   project `nfl-confidence-pool-26`, and collect the rows.
3. **Render.** Save `{"<name>": [rows...], ...}` as JSON in the scratchpad directory, plus
   `"window": {"since": "YYYY-MM-DD", "until": "YYYY-MM-DD"}` for a windowed run (omit it for
   all-time), then run `python render_report.py <data.json> <report.html>` (stdlib only) from
   this folder. Give the user the full path to the HTML file.
4. **Summarize in chat**, briefly: who is most and least active, which features are used versus
   unused (zero-member features show an empty bar), members who were quiet in the period or have
   no data yet, the device split, and the daily-active trend.

## Caveats to state

- Tracking only started when this shipped: there is no history before that, and members who
  signed up earlier show as "no data yet".
- Active time is a floor: 30-second heartbeats counted while the tab is visible and the user
  interacted in the last 2 minutes. People reading without touching the screen are undercounted.
- Days are bucketed in America/Chicago; "Last login" is shown in UTC.
- "Active" means a login, session start, page view or heartbeat that day. Heartbeats need
  interaction in the last 2 minutes, so an idle open tab does not count.
- Logins are only written on a real sign-in. Members who stay signed in via the refresh cookie
  show activity with zero logins, so rely on active minutes and page views, not login counts.
- "Quiet" = no activity in the period but some earlier. "No data yet" = never any tracked activity.
- Picks and submissions come from the existing tables, so those two feature rows are all-time
  even in a windowed run.

## Weekly mode (scheduled, no human present)

Used by the Tuesday-morning routine. A fresh checkout has no `exclude.txt`, so exclude nobody
(`{{EXCLUDE}}` = `''`) and do not ask. Set `{{SINCE}}` to today minus 7 days in America/Chicago and
`window` to that date and today. Everything else is the steps above: SELECT only, display names
only, render to HTML, then publish the HTML as a new private artifact titled
"NFL Confidence usage report, <since> to <until>". If artifacts cannot be published from the
session, put the step 4 summary in the final message instead.

## Self-check

`python test_render.py` (in this folder) verifies the renderer with sample and empty data.
