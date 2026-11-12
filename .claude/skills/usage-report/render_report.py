"""Render the usage report as one self-contained HTML file (stdlib only, inline SVG charts).

CLI: python render_report.py data.json report.html
`data` maps each query name in queries.sql to a list of row dicts.
"""

import json
import sys
from collections import defaultdict
from html import escape

QUERY_NAMES = [
    "users",
    "logins_per_user",
    "active_buckets_per_user",
    "page_views",
    "section_opens",
    "dau",
    "wau",
    "login_series",
    "device_split",
    "feature_adoption",
    "never_returned",
]
HEARTBEAT_SECONDS = 30  # must match the frontend heartbeat interval

CSS = """
:root{--bg:#fff;--fg:#1a1d21;--muted:#5b6470;--line:#d9dee5;--accent:#1f5fbf;--warn:#b45309}
@media (prefers-color-scheme:dark){:root{--bg:#14171b;--fg:#e8eaed;--muted:#9aa3ad;--line:#2c333b;--accent:#6aa3ff;--warn:#f0a35c}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:960px;padding:16px}
h1{font-size:22px}h2{font-size:17px;margin-top:32px}table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}th{color:var(--muted);font-weight:600}
td.n,th.n{text-align:right}.muted{color:var(--muted)}.warn{color:var(--warn)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
svg{width:100%;height:auto}.axis{stroke:var(--line)}.bar{fill:var(--accent)}.lbl{fill:var(--muted);font-size:10px}
.line{fill:none;stroke:var(--accent);stroke-width:2}
"""


def _fmt_minutes(seconds: int) -> str:
    return f"{seconds // 60}m" if seconds >= 60 else f"{seconds}s"


def _line_chart(rows: list[dict], x_key: str, title: str) -> str:
    if not rows:
        return f"<h3>{escape(title)}</h3><p class='muted'>No data yet.</p>"
    w, h, pad = 600, 160, 24
    top = max(int(r["users"]) for r in rows) or 1
    step = (w - 2 * pad) / max(len(rows) - 1, 1)
    pts = " ".join(
        f"{pad + i * step:.1f},{h - pad - (int(r['users']) / top) * (h - 2 * pad):.1f}"
        for i, r in enumerate(rows)
    )
    first, last = escape(str(rows[0][x_key])), escape(str(rows[-1][x_key]))
    return (
        f"<h3>{escape(title)}</h3><svg viewBox='0 0 {w} {h}' role='img' aria-label='{escape(title)}'>"
        f"<line class='axis' x1='{pad}' y1='{h - pad}' x2='{w - pad}' y2='{h - pad}'/>"
        f"<polyline class='line' points='{pts}'/>"
        f"<text class='lbl' x='{pad}' y='{h - 6}'>{first}</text>"
        f"<text class='lbl' x='{w - pad}' y='{h - 6}' text-anchor='end'>{last}</text>"
        f"<text class='lbl' x='{pad}' y='12'>max {top}</text></svg>"
    )


def _login_bars(name: str, series: list[dict], days: list[str]) -> str:
    counts = {r["day"]: int(r["logins"]) for r in series}
    top = max(counts.values(), default=0) or 1
    w, h, pad = 260, 70, 4
    bar_w = (w - 2 * pad) / max(len(days), 1)
    bars = "".join(
        f"<rect class='bar' x='{pad + i * bar_w:.1f}' width='{max(bar_w - 1, 1):.1f}' "
        f"y='{h - 14 - (counts[d] / top) * (h - 24):.1f}' height='{(counts[d] / top) * (h - 24):.1f}'/>"
        for i, d in enumerate(days)
        if d in counts
    )
    total = sum(counts.values())
    return (
        f"<div><strong>{escape(name)}</strong> <span class='muted'>{total} logins</span>"
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='Logins per day for {escape(name)}'>"
        f"<line class='axis' x1='0' y1='{h - 14}' x2='{w}' y2='{h - 14}'/>{bars}"
        f"<text class='lbl' x='{pad}' y='{h - 2}'>{escape(days[0]) if days else ''}</text>"
        f"<text class='lbl' x='{w - pad}' y='{h - 2}' text-anchor='end'>{escape(days[-1]) if days else ''}</text>"
        "</svg></div>"
    )


def _user_table(data: dict) -> str:
    users = data["users"]
    if not users:
        return "<p class='muted'>No data yet.</p>"
    logins = {r["user_id"]: r for r in data["logins_per_user"]}
    buckets = {r["user_id"]: int(r["buckets"]) for r in data["active_buckets_per_user"]}
    pages: dict[str, list[str]] = defaultdict(list)
    for r in sorted(data["page_views"], key=lambda r: -int(r["views"])):
        pages[r["user_id"]].append(f"{r['path']} ({r['views']})")
    sections: dict[str, list[str]] = defaultdict(list)
    for r in sorted(data["section_opens"], key=lambda r: -int(r["opens"])):
        sections[r["user_id"]].append(f"{r['section']} ({r['opens']})")
    rows = []
    for u in users:
        uid = u["user_id"]
        lg = logins.get(uid, {})
        rows.append(
            "<tr>"
            f"<td>{escape(u['display_name'])}</td>"
            f"<td class='n'>{int(lg.get('login_count', 0))}</td>"
            f"<td>{escape(str(lg.get('last_login') or '-')[:16])}</td>"
            f"<td class='n'>{_fmt_minutes(buckets.get(uid, 0) * HEARTBEAT_SECONDS)}</td>"
            f"<td>{escape(', '.join(pages[uid][:4]) or '-')}</td>"
            f"<td>{escape(', '.join(sections[uid][:4]) or '-')}</td></tr>"
        )
    return (
        "<table><tr><th>Member</th><th class='n'>Logins</th><th>Last login (UTC)</th>"
        "<th class='n'>Active time</th><th>Top pages</th><th>Sections opened</th></tr>"
        + "".join(rows)
        + "</table><p class='muted'>Active time is a floor: it counts 30-second heartbeats while "
        "the tab is visible and the user recently interacted.</p>"
    )


def _features(rows: list[dict]) -> str:
    if not rows:
        return "<p class='muted'>No data yet.</p>"
    body = "".join(
        f"<tr><td>{escape(r['feature'])}</td><td class='n'>{r['users']}</td>"
        f"<td class='n'>{r['events']}</td>"
        f"<td>{'<span class=warn>ignored</span>' if int(r['users']) == 0 else 'used'}</td></tr>"
        for r in sorted(rows, key=lambda r: -int(r["users"]))
    )
    return (
        "<table><tr><th>Feature</th><th class='n'>Members</th><th class='n'>Events</th>"
        f"<th>Status</th></tr>{body}</table>"
    )


def render(data: dict, out_path: str) -> None:
    data = {name: data.get(name, []) for name in QUERY_NAMES}
    names = {u["user_id"]: u["display_name"] for u in data["users"]}
    days = sorted({r["day"] for r in data["dau"]} | {r["day"] for r in data["login_series"]})
    by_user: dict[str, list[dict]] = defaultdict(list)
    for r in data["login_series"]:
        by_user[r["user_id"]].append(r)
    small_multiples = "".join(
        _login_bars(names.get(uid, "Unknown"), by_user.get(uid, []), days) for uid in names
    )
    never = "".join(
        f"<li>{escape(names.get(r['user_id'], 'Unknown'))} — {escape(r['status'])}</li>"
        for r in data["never_returned"]
    )
    devices = ", ".join(f"{escape(r['device'])}: {r['sessions']}" for r in data["device_split"])
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>NFL Confidence usage report</title><style>{CSS}</style></head><body>"
        "<h1>NFL Confidence usage report</h1>"
        "<h2>Members</h2>" + _user_table(data) + "<h2>Active members over time</h2>"
        + _line_chart(data["dau"], "day", "Daily active members")
        + _line_chart(data["wau"], "week_start", "Weekly active members")
        + "<h2>Logins per member</h2>"
        + (f"<div class='grid'>{small_multiples}</div>" if names and days else "<p class='muted'>No data yet.</p>")
        + "<h2>Features</h2>" + _features(data["feature_adoption"])
        + "<h2>Devices</h2>" + (f"<p>{devices}</p>" if devices else "<p class='muted'>No data yet.</p>")
        + "<h2>Not coming back</h2>" + (f"<ul>{never}</ul>" if never else "<p class='muted'>No data yet.</p>")
        + "</body></html>"
    )
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(page)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as src:
        render(json.load(src), sys.argv[2])
    print(sys.argv[2])
