# ruff: noqa: E501  (embedded SQL and email HTML lines)
"""Weekly member-usage report: gather the last few days of activity and render an email.

The SQL mirrors `.claude/skills/usage-report/queries.sql` (same events, same Chicago-day
bucketing, same 30-second heartbeat buckets) with no test-account exclusion. The HTML is
email-safe on purpose: tables and inline styles, literal colors, bars built from divs. Gmail
ignores CSS variables and does not draw inline SVG.
"""

from collections import defaultdict
from datetime import date
from html import escape

from sqlalchemy import text
from sqlalchemy.orm import Session

HEARTBEAT_SECONDS = 30  # must match the frontend heartbeat interval
HISTORY_SUFFIX = "(all-time)"  # feature rows read from the picks tables, not from tracking

_SINCE = "(a.created_at AT TIME ZONE CAST(:tz AS text))::date >= CAST(:since AS date)"
_ACTIVITY = """
  SELECT user_id, created_at FROM audit_log WHERE action = 'login' AND user_id IS NOT NULL
  UNION ALL
  SELECT user_id, created_at FROM usage_events
  WHERE action IN ('session_start', 'page_view', 'heartbeat') AND user_id IS NOT NULL
"""

QUERIES: dict[str, str] = {
    "users": "SELECT id::text AS user_id, display_name FROM users ORDER BY display_name",
    "logins_per_user": f"""
        SELECT a.user_id::text AS user_id, count(*) AS login_count, max(a.created_at) AS last_login
        FROM audit_log a WHERE a.action = 'login' AND a.user_id IS NOT NULL AND {_SINCE}
        GROUP BY a.user_id""",
    "active_buckets_per_user": f"""
        SELECT a.user_id::text AS user_id,
               count(DISTINCT floor(extract(epoch FROM a.created_at) / 30)) AS buckets
        FROM usage_events a WHERE a.action = 'heartbeat' AND a.user_id IS NOT NULL AND {_SINCE}
        GROUP BY a.user_id""",
    "page_views": f"""
        SELECT a.user_id::text AS user_id, a.path, count(*) AS views
        FROM usage_events a WHERE a.action = 'page_view' AND a.user_id IS NOT NULL AND {_SINCE}
        GROUP BY 1, 2""",
    "section_opens": f"""
        SELECT a.user_id::text AS user_id, a.section, count(*) AS opens
        FROM usage_events a WHERE a.action = 'section_open' AND a.user_id IS NOT NULL AND {_SINCE}
        GROUP BY 1, 2""",
    "dau": f"""
        WITH activity AS ({_ACTIVITY}), active AS (
          SELECT (a.created_at AT TIME ZONE CAST(:tz AS text))::date AS day, a.user_id
          FROM activity a WHERE {_SINCE}
        ), bounds AS (SELECT min(day) AS lo, max(day) AS hi FROM active)
        SELECT d::date::text AS day, count(DISTINCT active.user_id) AS users
        FROM bounds, generate_series(bounds.lo, bounds.hi, interval '1 day') AS d
        LEFT JOIN active ON active.day = d::date
        GROUP BY d ORDER BY d""",
    "device_split": f"""
        SELECT a.device, count(*) AS sessions
        FROM usage_events a WHERE a.action = 'session_start' AND a.user_id IS NOT NULL AND {_SINCE}
        GROUP BY 1""",
    "feature_adoption": f"""
        WITH ev AS (
          SELECT a.user_id, a.action, a.path, a.section
          FROM usage_events a WHERE a.user_id IS NOT NULL AND {_SINCE}
        ), feats(feature, users, events) AS (
          SELECT 'Dashboard page', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'page_view' AND path = '/'
          UNION ALL SELECT 'Picks page', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'page_view' AND path = '/picks'
          UNION ALL SELECT 'Members (league settings) page', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'page_view' AND path = '/league-settings'
          UNION ALL SELECT 'Leaderboard section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'leaderboard'
          UNION ALL SELECT 'Game breakdown section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'breakdown'
          UNION ALL SELECT 'Standings section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'standings'
          UNION ALL SELECT 'Profile section', count(DISTINCT user_id), count(*) FROM ev WHERE action = 'section_open' AND section = 'profile'
          UNION ALL SELECT 'Made picks {HISTORY_SUFFIX}', count(DISTINCT user_id), count(*) FROM picks
          UNION ALL SELECT 'Submitted a week {HISTORY_SUFFIX}', count(DISTINCT user_id), count(*) FROM week_submissions
        )
        SELECT feature, users, events FROM feats""",
    # Members with no tracked activity at any time (not just inside the window).
    "no_data": f"""
        SELECT u.id::text AS user_id FROM users u
        WHERE NOT EXISTS (SELECT 1 FROM ({_ACTIVITY}) a WHERE a.user_id = u.id)""",
}


def collect(db: Session, since: date, tz: str) -> dict[str, list[dict]]:
    params = {"since": since, "tz": tz}
    return {
        name: [dict(row) for row in db.execute(text(sql), params).mappings().all()]
        for name, sql in QUERIES.items()
    }


def _day(value: date | str) -> str:
    d = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    return f"{d:%b} {d.day}"


def _minutes(buckets: int) -> float:
    return buckets * HEARTBEAT_SECONDS / 60


def _num(value: float) -> str:
    return f"{value:g}"


# --- email-safe building blocks (inline styles only) ---------------------------------------

_FONT = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
_MUTED = "color:#626a75;font-size:12px"
_CELL = "padding:7px 8px;border-bottom:1px solid #e3e1dc;font-size:14px"


def _bar(fraction: float) -> str:
    width = round(100 * max(0.0, min(1.0, fraction)))
    return (
        "<div style='background:#ebe9e4;border-radius:4px;height:10px'>"
        f"<div style='background:#2b6a5e;border-radius:4px;height:10px;width:{width}%'></div></div>"
    )


def _section(title: str, body: str) -> str:
    return (
        f"<tr><td style='padding:24px 0 8px;font-size:17px;font-weight:600'>{escape(title)}</td></tr>"
        f"<tr><td>{body}</td></tr>"
    )


def _tiles(cells: list[tuple[str, str]]) -> str:
    tds = "".join(
        f"<td width='25%' style='padding:12px;border:1px solid #e3e1dc;background:#ffffff;vertical-align:top'>"
        f"<div style='{_MUTED}'>{escape(label)}</div>"
        f"<div style='font-size:26px;font-weight:600;margin-top:4px'>{value}</div></td>"
        for label, value in cells
    )
    return f"<table role='presentation' width='100%' cellspacing='4' cellpadding='0'><tr>{tds}</tr></table>"


def _bar_rows(rows: list[tuple[str, float, str]], label_width: int) -> str:
    body = "".join(
        f"<tr><td width='{label_width}' style='{_CELL}'>{escape(label)}</td>"
        f"<td style='{_CELL}'>{_bar(fraction)}</td>"
        f"<td width='36' align='right' style='{_CELL};font-weight:600'>{escape(count)}</td></tr>"
        for label, fraction, count in rows
    )
    return f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>{body}</table>"


def _names(names: list[str]) -> str:
    return escape(", ".join(names)) if names else "Nobody"


def render_email_html(data: dict[str, list[dict]], since: date, until: date) -> str:
    users = data["users"]
    total = len(users)
    logins = {r["user_id"]: r for r in data["logins_per_user"]}
    buckets = {r["user_id"]: int(r["buckets"]) for r in data["active_buckets_per_user"]}
    views: dict[str, int] = defaultdict(int)
    for r in data["page_views"]:
        views[r["user_id"]] += int(r["views"])
    opens = {r["user_id"] for r in data["section_opens"]}
    no_data = {r["user_id"] for r in data["no_data"]}
    active = set(logins) | set(buckets) | set(views) | opens

    def status(uid: str) -> str:
        return "Active" if uid in active else "No data yet" if uid in no_data else "Quiet"

    ranked = sorted(
        users,
        key=lambda u: (-buckets.get(u["user_id"], 0), -views[u["user_id"]], u["display_name"]),
    )
    n_active = sum(1 for u in users if u["user_id"] in active)
    quiet = [u["display_name"] for u in users if status(u["user_id"]) == "Quiet"]
    silent = [u["display_name"] for u in users if status(u["user_id"]) == "No data yet"]

    minutes = _minutes(sum(buckets.values()))
    time_label = f"{minutes / 60:.1f} h" if minutes >= 60 else f"{_num(minutes)} min"
    sessions = sum(int(r["sessions"]) for r in data["device_split"])
    phone = sum(int(r["sessions"]) for r in data["device_split"] if r["device"] == "phone")
    phone_label = f"{round(100 * phone / sessions)}%" if sessions else "—"
    tiles = _tiles(
        [
            ("Members active", f"{n_active} <span style='{_MUTED}'>of {total}</span>"),
            ("Time in the app", time_label),
            ("Page views", f"{sum(views.values()):,}"),
            ("Sessions on a phone", phone_label),
        ]
    )

    dau = data["dau"]
    top = max((int(r["users"]) for r in dau), default=0) or 1
    daily = (
        _bar_rows([(_day(r["day"]), int(r["users"]) / top, str(r["users"])) for r in dau], 70)
        if dau
        else f"<p style='{_MUTED}'>No activity in this period.</p>"
    )

    head = "".join(
        f"<th align='{a}' style='{_MUTED};padding:7px 8px;border-bottom:1px solid #e3e1dc'>{h}</th>"
        for h, a in [
            ("Member", "left"),
            ("Status", "left"),
            ("Active min", "right"),
            ("Page views", "right"),
            ("Last login", "right"),
        ]
    )
    colors = {"Active": "#2b7a4b", "Quiet": "#a2610f", "No data yet": "#626a75"}
    member_rows = "".join(
        f"<tr><td style='{_CELL}'>{escape(u['display_name'])}</td>"
        f"<td style='{_CELL};color:{colors[status(u['user_id'])]}'>{status(u['user_id'])}</td>"
        f"<td align='right' style='{_CELL}'>{_num(_minutes(buckets.get(u['user_id'], 0)))}</td>"
        f"<td align='right' style='{_CELL}'>{views[u['user_id']]}</td>"
        f"<td align='right' style='{_CELL}'>"
        f"{_day(logins[u['user_id']]['last_login']) if u['user_id'] in logins else '—'}</td></tr>"
        for u in ranked
    )
    members = (
        f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>"
        f"<tr>{head}</tr>{member_rows}</table>"
    )

    def features(history: bool) -> str:
        rows = [
            r for r in data["feature_adoption"] if r["feature"].endswith(HISTORY_SUFFIX) == history
        ]
        return _bar_rows(
            [
                (r["feature"], int(r["users"]) / (total or 1), str(r["users"]))
                for r in sorted(rows, key=lambda r: -int(r["users"]))
            ],
            210,
        )

    period = f"{_day(since)} to {_day(until)}"
    body = (
        f"<tr><td style='font-size:26px;font-weight:600'>NFL Confidence member usage</td></tr>"
        f"<tr><td style='padding-top:8px;font-size:17px'>{n_active} of {total} members used the app "
        f"in this period. {len(quiet)} were quiet and {len(silent)} have no tracked activity at all.</td></tr>"
        f"<tr><td style='padding-top:6px;{_MUTED}'>{escape(period)}. Days are Chicago time.</td></tr>"
        f"<tr><td style='padding-top:16px'>{tiles}</td></tr>"
        + _section("Members active each day", daily)
        + _section("Every member", members)
        + _section("What members use", features(False))
        + f"<tr><td style='padding-top:8px;{_MUTED}'>From the picks tables, all weeks:</td></tr>"
        f"<tr><td>{features(True)}</td></tr>"
        + _section(
            "Who to follow up with",
            f"<p style='margin:0 0 8px;font-size:14px'><b>Quiet this period:</b> {_names(quiet)}</p>"
            f"<p style='margin:0;font-size:14px'><b>No tracked activity at all:</b> {_names(silent)}</p>",
        )
        + f"<tr><td style='padding-top:24px;{_MUTED}'>Active time is a floor: it counts 30-second "
        "heartbeats while the tab is visible and the member touched the screen in the last 2 minutes. "
        "Logins are only recorded on a real sign-in, so members who stay signed in show activity with "
        "zero logins. Tracking started on 14 November 2026.</td></tr>"
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
        f"<body style='margin:0;background:#fbfaf8;color:#1c1f24;font-family:{_FONT}'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr><td align='center' style='padding:24px 12px'>"
        f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='max-width:640px;text-align:left'>{body}</table>"
        "</td></tr></table></body></html>"
    )
