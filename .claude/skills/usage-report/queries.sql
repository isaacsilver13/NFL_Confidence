-- Usage report queries. SELECT only. Run each one with the Neon MCP run_sql.
-- Replace {{EXCLUDE}} with the quoted, lower-cased test-account emails from exclude.txt,
-- e.g. 'test1@example.com','dev@example.com'; use '' when the list is empty.
-- Replace {{SINCE}} with the first Chicago day to count (YYYY-MM-DD): today minus 7 days for the
-- weekly report, 1970-01-01 for everything since tracking began.
-- Days are bucketed in America/Chicago. Rows with user_id NULL (deleted users) are
-- dropped by the JOIN to users. Save each result as a JSON list under its name.

-- name: users
SELECT u.id::text AS user_id, u.display_name
FROM users u
WHERE lower(u.email) NOT IN ({{EXCLUDE}})
ORDER BY u.display_name;

-- name: logins_per_user
SELECT a.user_id::text AS user_id, count(*) AS login_count, max(a.created_at) AS last_login
FROM audit_log a JOIN users u ON u.id = a.user_id
WHERE a.action = 'login' AND lower(u.email) NOT IN ({{EXCLUDE}})
  AND (a.created_at AT TIME ZONE 'America/Chicago')::date >= DATE '{{SINCE}}'
GROUP BY a.user_id;

-- name: active_buckets_per_user
-- Distinct 30-second heartbeat buckets; active time = buckets x 30 s.
SELECT a.user_id::text AS user_id,
       count(DISTINCT floor(extract(epoch FROM a.created_at) / 30)) AS buckets
FROM usage_events a JOIN users u ON u.id = a.user_id
WHERE a.action = 'heartbeat' AND lower(u.email) NOT IN ({{EXCLUDE}})
  AND (a.created_at AT TIME ZONE 'America/Chicago')::date >= DATE '{{SINCE}}'
GROUP BY a.user_id;

-- name: page_views
SELECT a.user_id::text AS user_id, a.path, count(*) AS views
FROM usage_events a JOIN users u ON u.id = a.user_id
WHERE a.action = 'page_view' AND lower(u.email) NOT IN ({{EXCLUDE}})
  AND (a.created_at AT TIME ZONE 'America/Chicago')::date >= DATE '{{SINCE}}'
GROUP BY 1, 2;

-- name: section_opens
SELECT a.user_id::text AS user_id, a.section, count(*) AS opens
FROM usage_events a JOIN users u ON u.id = a.user_id
WHERE a.action = 'section_open' AND lower(u.email) NOT IN ({{EXCLUDE}})
  AND (a.created_at AT TIME ZONE 'America/Chicago')::date >= DATE '{{SINCE}}'
GROUP BY 1, 2;

-- name: dau
-- Active = any login (audit_log), session_start, page_view or heartbeat (usage_events) that day.
-- Heartbeats already require interaction in the last 2 minutes, so they are real activity.
-- Zero-filled between first and last day.
WITH activity AS (
  SELECT user_id, created_at FROM audit_log WHERE action = 'login'
  UNION ALL
  SELECT user_id, created_at FROM usage_events WHERE action IN ('session_start', 'page_view', 'heartbeat')
), active AS (
  SELECT (a.created_at AT TIME ZONE 'America/Chicago')::date AS day, a.user_id
  FROM activity a JOIN users u ON u.id = a.user_id
  WHERE lower(u.email) NOT IN ({{EXCLUDE}})
    AND (a.created_at AT TIME ZONE 'America/Chicago')::date >= DATE '{{SINCE}}'
), bounds AS (SELECT min(day) AS lo, max(day) AS hi FROM active)
SELECT d::date::text AS day, count(DISTINCT active.user_id) AS users
FROM bounds, generate_series(bounds.lo, bounds.hi, interval '1 day') AS d
LEFT JOIN active ON active.day = d::date
GROUP BY d ORDER BY d;

-- name: device_split
SELECT a.device, count(*) AS sessions
FROM usage_events a JOIN users u ON u.id = a.user_id
WHERE a.action = 'session_start' AND lower(u.email) NOT IN ({{EXCLUDE}})
  AND (a.created_at AT TIME ZONE 'America/Chicago')::date >= DATE '{{SINCE}}'
GROUP BY 1;

-- name: feature_adoption
-- Members = distinct non-excluded users who did it; events = how many times.
-- The two picks rows come from the picks tables, so they are all-time whatever {{SINCE}} is.
WITH ev AS (
  SELECT a.user_id, a.action, a.path, a.section
  FROM usage_events a JOIN users u ON u.id = a.user_id
  WHERE lower(u.email) NOT IN ({{EXCLUDE}})
    AND (a.created_at AT TIME ZONE 'America/Chicago')::date >= DATE '{{SINCE}}'
), feats(feature, users, events) AS (
  SELECT 'Dashboard page', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'page_view' AND path = '/'
  UNION ALL SELECT 'Picks page', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'page_view' AND path = '/picks'
  UNION ALL SELECT 'Members (league settings) page', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'page_view' AND path = '/league-settings'
  UNION ALL SELECT 'Leaderboard section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'leaderboard'
  UNION ALL SELECT 'Game breakdown section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'breakdown'
  UNION ALL SELECT 'Standings section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'standings'
  UNION ALL SELECT 'Profile section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'profile'
  UNION ALL SELECT 'Made picks (all-time)', count(DISTINCT p.user_id), count(*)
    FROM picks p JOIN users u ON u.id = p.user_id WHERE lower(u.email) NOT IN ({{EXCLUDE}})
  UNION ALL SELECT 'Submitted a week (all-time)', count(DISTINCT s.user_id), count(*)
    FROM week_submissions s JOIN users u ON u.id = s.user_id WHERE lower(u.email) NOT IN ({{EXCLUDE}})
)
SELECT feature, users, events FROM feats;

-- name: never_returned
-- All-time, never windowed. Activity = login, session_start, page_view or heartbeat (the same events
-- DAU counts). Members who stay signed in through the refresh cookie have no login row, so a login
-- row must not be required.
-- 'no data yet' = no tracked activity at all (signed up before tracking shipped, or never opened it).
-- 'never returned' = tracked activity on a single day only (Chicago time); `day` is that day.
WITH activity AS (
  SELECT user_id, (created_at AT TIME ZONE 'America/Chicago')::date AS day
  FROM (
    SELECT user_id, created_at FROM audit_log WHERE action = 'login'
    UNION ALL
    SELECT user_id, created_at FROM usage_events WHERE action IN ('session_start', 'page_view', 'heartbeat')
  ) e
  WHERE user_id IS NOT NULL
), span AS (
  SELECT user_id, min(day) AS first_day, max(day) AS last_day FROM activity GROUP BY user_id
)
SELECT u.id::text AS user_id,
       CASE WHEN s.user_id IS NULL THEN 'no data yet' ELSE 'never returned' END AS status,
       s.last_day::text AS day
FROM users u
LEFT JOIN span s ON s.user_id = u.id
WHERE lower(u.email) NOT IN ({{EXCLUDE}})
  AND (s.user_id IS NULL OR s.last_day = s.first_day);
