---
name: usage-report
description: Use when the user asks for the NFL Confidence usage report, user activity, who is logging in, how long people spend on the app, which pages or features are used or ignored, or DAU/WAU charts. Read-only against production through the Neon MCP.
---

# NFL Confidence usage report

Builds an HTML report from the `audit_log` events the app records (`login`, `session_start`,
`page_view`, `section_open`, `heartbeat`) plus the `picks` and `week_submissions` tables.

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
   with the lower-cased, single-quoted emails joined by commas (`''` if none), run it with
   the Neon MCP `run_sql` against project `nfl-confidence-pool-26`, and collect the rows.
3. **Render.** Save `{"<name>": [rows...], ...}` as JSON in the scratchpad directory, then run
   `python render_report.py <data.json> <report.html>` (stdlib only) from this folder. Give the
   user the full path to the HTML file.
4. **Summarize in chat**, briefly: logins and last login per member, who is most and least
   active, which features are used versus ignored (the report marks zero-member features as
   `ignored`), people who never returned or have no data yet, device split, and the DAU/WAU trend.

## Caveats to state

- Tracking only started when this shipped: there is no history before that, and members who
  signed up earlier show as "no data yet".
- Active time is a floor: 30-second heartbeats counted while the tab is visible and the user
  interacted in the last 2 minutes. People reading without touching the screen are undercounted.
- Days are bucketed in America/Chicago; "Last login" is shown in UTC.
- Picks and submissions come from the existing tables, so those counts include history.

## Self-check

`python test_render.py` (in this folder) verifies the renderer with sample and empty data.
