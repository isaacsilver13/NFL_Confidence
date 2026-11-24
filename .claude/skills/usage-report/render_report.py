"""Render the usage report as one self-contained HTML file (stdlib only, inline SVG, no scripts).

CLI: python render_report.py data.json report.html
`data` maps each query name in queries.sql to a list of row dicts. An optional
`"window": {"since": "YYYY-MM-DD", "until": "YYYY-MM-DD"}` labels the period; without it the
report reads as "since tracking began".
"""

import json
import math
import sys
from datetime import date
from html import escape

QUERY_NAMES = [
    "users",
    "logins_per_user",
    "active_buckets_per_user",
    "page_views",
    "section_opens",
    "dau",
    "device_split",
    "feature_adoption",
    "never_returned",
]
HEARTBEAT_SECONDS = 30  # must match the frontend heartbeat interval
HISTORY_SUFFIX = "(all-time)"  # feature rows that come from the picks tables, not tracking

CSS = """
:root{--bg:#fbfaf8;--panel:#fff;--fg:#1c1f24;--muted:#626a75;--line:#e3e1dc;--accent:#2b6a5e;
--ok:#2b7a4b;--warn:#a2610f;--grid:#ebe9e4}
@media (prefers-color-scheme:dark){:root{--bg:#15181b;--panel:#1c2024;--fg:#e9eaec;--muted:#98a1ab;
--line:#2d333a;--accent:#5fc2ad;--ok:#6fcf97;--warn:#f0b363;--grid:#262b31}}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}
main{max-width:980px;margin:0 auto;padding:24px max(16px,env(safe-area-inset-right)) 48px max(16px,env(safe-area-inset-left));
display:flex;flex-direction:column;gap:32px}
h1{font-size:28px;font-weight:600;margin:0;letter-spacing:-.01em}
h2{font-size:17px;font-weight:600;margin:0}
p{margin:0}.lede{font-size:18px;max-width:60ch;margin-top:8px}.muted{color:var(--muted);font-size:13px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.tile,.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px;min-width:0}
.tile .big{font-size:34px;font-weight:600;line-height:1.1;font-variant-numeric:tabular-nums;margin-top:6px}
.tile .big small{font-size:15px;font-weight:400;color:var(--muted)}
section{display:flex;flex-direction:column;gap:12px;min-width:0}
.scroll{overflow-x:auto;padding:0}
table{border-collapse:collapse;width:100%}
th,td{padding:9px 14px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap;font-variant-numeric:tabular-nums}
th{font-size:12px;font-weight:600;color:var(--muted)}tr:last-child td{border-bottom:0}
td.n,th.n{text-align:right}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--accent);margin-right:8px;vertical-align:middle}
.pill{display:inline-block;padding:1px 10px;border-radius:999px;font-size:12px;border:1px solid var(--line);color:var(--muted)}
.pill.Active{color:var(--ok);border-color:currentColor}.pill.Quiet{color:var(--warn);border-color:currentColor}
.feat{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px}
.feat li{display:grid;grid-template-columns:minmax(120px,230px) 1fr 2.5rem;gap:12px;align-items:center}
.track{height:10px;border-radius:5px;background:var(--grid);overflow:hidden}.fill{height:100%;background:var(--accent)}
.cnt{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.chip{border:1px solid var(--line);border-radius:999px;padding:3px 12px;background:var(--bg)}
svg{display:block;width:100%;height:auto}svg text{font-size:11px;fill:var(--muted)}
.grid{stroke:var(--grid)}.line{fill:none;stroke:var(--accent);stroke-width:2}.area{fill:var(--accent);opacity:.12}.dot{fill:var(--accent)}
details{color:var(--muted);font-size:14px}summary{cursor:pointer;color:var(--fg)}
details ul{margin:8px 0 0;padding-left:20px;display:flex;flex-direction:column;gap:4px;max-width:70ch}
@media (max-width:520px){.feat li{grid-template-columns:1fr 2.5rem}.feat .track{grid-column:1/-1;grid-row:2}}
"""


def _day(text: str) -> str:
    d = date.fromisoformat(str(text)[:10])
    return f"{d:%b} {d.day}"


def _minutes(buckets: int) -> float:
    return buckets * HEARTBEAT_SECONDS / 60


def _num(value: float) -> str:
    return f"{value:g}" if value < 1000 else f"{value:,.0f}"


def _tiles(active: int, total: int, buckets: int, views: int, devices: list[dict]) -> str:
    minutes = _minutes(buckets)
    time_label = f"{minutes / 60:.1f} <small>hours</small>" if minutes >= 60 else f"{_num(minutes)} <small>min</small>"
    sessions = sum(int(r["sessions"]) for r in devices)
    phone = sum(int(r["sessions"]) for r in devices if r["device"] == "phone")
    phone_label = f"{round(100 * phone / sessions)}<small>%</small>" if sessions else "—"
    cells = [
        ("Members active", f"{active} <small>of {total}</small>"),
        ("Time in the app", time_label),
        ("Page views", f"{views:,}"),
        ("Sessions on a phone", phone_label),
    ]
    return "".join(f"<div class='tile'><span class='muted'>{k}</span><div class='big'>{v}</div></div>" for k, v in cells)


def _daily_chart(rows: list[dict]) -> str:
    if not rows:
        return "<p class='muted'>No activity in this period.</p>"
    w, h, ml, mr, mt, mb = 640, 220, 30, 26, 18, 28
    counts = [int(r["users"]) for r in rows]
    step = max(1, math.ceil(max(counts) / 4))
    ymax = max(step, math.ceil(max(counts) / step) * step)
    n = len(rows)
    xs = [ml + (w - ml - mr) * (i / (n - 1) if n > 1 else 0.5) for i in range(n)]
    ys = [mt + (h - mt - mb) * (1 - c / ymax) for c in counts]
    grid = "".join(
        f"<line class='grid' x1='{ml}' x2='{w - mr}' y1='{mt + (h - mt - mb) * (1 - t / ymax):.1f}' "
        f"y2='{mt + (h - mt - mb) * (1 - t / ymax):.1f}'/>"
        f"<text x='{ml - 8}' y='{mt + (h - mt - mb) * (1 - t / ymax) + 4:.1f}' text-anchor='end'>{t}</text>"
        for t in range(0, ymax + 1, step)
    )
    every = max(1, math.ceil(n / 8))
    labels = "".join(
        f"<text x='{xs[i]:.1f}' y='{h - 8}' text-anchor='middle'>{escape(_day(r['day']))}</text>"
        for i, r in enumerate(rows)
        if i % every == 0 or i == n - 1
    )
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{h - mb} {pts} {xs[-1]:.1f},{h - mb}"
    dots = "".join(
        f"<circle class='dot' cx='{x:.1f}' cy='{y:.1f}' r='{5 if i == n - 1 else 3}'>"
        f"<title>{escape(_day(r['day']))}: {c} members active</title></circle>"
        for i, (x, y, c, r) in enumerate(zip(xs, ys, counts, rows))
    )
    end = f"<text x='{xs[-1]:.1f}' y='{ys[-1] - 10:.1f}' text-anchor='end' style='font-weight:600;fill:var(--fg)'>{counts[-1]}</text>"
    label = f"Members active per day, {_day(rows[0]['day'])} to {_day(rows[-1]['day'])}, peak {max(counts)}"
    return (
        f"<svg viewBox='0 0 {w} {h}' role='img' aria-label='{escape(label)}'>{grid}"
        f"<polygon class='area' points='{area}'/><polyline class='line' points='{pts}'/>{dots}{end}{labels}</svg>"
    )


def _features(rows: list[dict], total: int, history: bool) -> str:
    picked = [r for r in rows if r["feature"].endswith(HISTORY_SUFFIX) == history]
    if not picked:
        return "<p class='muted'>No data in this period.</p>"
    items = "".join(
        f"<li title='{int(r['events'])} times in total'><span>{escape(r['feature'])}</span>"
        f"<span class='track'><span class='fill' style='display:block;width:{100 * int(r['users']) / (total or 1):.0f}%'></span></span>"
        f"<span class='cnt'>{int(r['users'])}</span></li>"
        for r in sorted(picked, key=lambda r: -int(r["users"]))
    )
    return f"<ul class='feat'>{items}</ul>"


def _chips(names: list[str]) -> str:
    if not names:
        return "<p class='muted' style='margin-top:8px'>Nobody</p>"
    return "<div class='chips'>" + "".join(f"<span class='chip'>{escape(n)}</span>" for n in names) + "</div>"


def render(data: dict, out_path: str) -> None:
    window = data.get("window") or {}
    data = {name: data.get(name, []) for name in QUERY_NAMES}
    users = data["users"]
    total = len(users)
    logins = {r["user_id"]: r for r in data["logins_per_user"]}
    buckets = {r["user_id"]: int(r["buckets"]) for r in data["active_buckets_per_user"]}
    views: dict[str, int] = {}
    for r in data["page_views"]:
        views[r["user_id"]] = views.get(r["user_id"], 0) + int(r["views"])
    opens: dict[str, int] = {}
    for r in data["section_opens"]:
        opens[r["user_id"]] = opens.get(r["user_id"], 0) + int(r["opens"])
    no_data = {r["user_id"] for r in data["never_returned"] if r["status"] == "no data yet"}
    active_ids = set(logins) | set(buckets) | set(views) | set(opens)
    n_active = len(active_ids & {u["user_id"] for u in users})

    def status(uid: str) -> str:
        return "Active" if uid in active_ids else "No data yet" if uid in no_data else "Quiet"

    ranked = sorted(users, key=lambda u: (-buckets.get(u["user_id"], 0), -views.get(u["user_id"], 0), u["display_name"]))
    max_buckets = max(buckets.values(), default=0) or 1
    rows = "".join(
        "<tr>"
        f"<td>{escape(u['display_name'])}</td>"
        f"<td><span class='pill {status(u['user_id']).replace(' ', '')}'>{status(u['user_id'])}</span></td>"
        f"<td class='n'><span class='bar' style='width:{round(60 * buckets.get(u['user_id'], 0) / max_buckets)}px'></span>"
        f"{_num(_minutes(buckets.get(u['user_id'], 0)))}</td>"
        f"<td class='n'>{int(logins.get(u['user_id'], {}).get('login_count', 0))}</td>"
        f"<td class='n'>{_day(logins[u['user_id']]['last_login']) if u['user_id'] in logins else '—'}</td>"
        f"<td class='n'>{views.get(u['user_id'], 0)}</td></tr>"
        for u in ranked
    )
    table = (
        "<table><thead><tr><th>Member</th><th>Status</th><th class='n'>Active minutes</th><th class='n'>Logins</th>"
        f"<th class='n'>Last login</th><th class='n'>Page views</th></tr></thead><tbody>{rows}</tbody></table>"
        if users
        else "<p class='muted' style='padding:16px'>No members.</p>"
    )
    quiet = [u["display_name"] for u in users if status(u["user_id"]) == "Quiet"]
    silent = [u["display_name"] for u in users if status(u["user_id"]) == "No data yet"]
    period = (
        f"{_day(window['since'])} to {_day(window['until'])}"
        if window.get("since") and window.get("until")
        else "since tracking began"
    )
    scope = "in this period" if window else "since tracking began"
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>NFL Confidence usage report</title><style>{CSS}</style></head><body><main>"
        "<header><h1>NFL Confidence member usage</h1>"
        f"<p class='lede'>{n_active} of {total} members used the app {scope}. "
        f"{len(quiet)} were quiet and {len(silent)} have no tracked activity at all.</p>"
        f"<p class='muted' style='margin-top:8px'>{escape(period[0].upper() + period[1:])}. Days are Chicago time.</p></header>"
        f"<div class='tiles'>{_tiles(n_active, total, sum(buckets.values()), sum(views.values()), data['device_split'])}</div>"
        f"<section><h2>Members active each day</h2><div class='card'>{_daily_chart(data['dau'])}</div></section>"
        f"<section><h2>Every member</h2><p class='muted'>Sorted by time in the app. Active time is a floor: reading without touching the screen does not count.</p>"
        f"<div class='card scroll'>{table}</div></section>"
        f"<section><h2>What members use</h2><p class='muted'>Members who used each part at least once, out of {total}.</p>"
        f"<div class='card'>{_features(data['feature_adoption'], total, False)}</div>"
        "<p class='muted'>From the picks tables, so these cover all weeks, not only this period:</p>"
        f"<div class='card'>{_features(data['feature_adoption'], total, True)}</div></section>"
        "<section><h2>Who to follow up with</h2><div class='two'>"
        f"<div class='card'><span class='muted'>Quiet {scope}, but active earlier</span>{_chips(quiet)}</div>"
        f"<div class='card'><span class='muted'>No tracked activity at all</span>{_chips(silent)}</div></div></section>"
        "<details><summary>How to read these numbers</summary><ul>"
        "<li>Tracking started on 14 November 2026, so nothing earlier is counted.</li>"
        "<li>Active time counts 30-second heartbeats while the tab is visible and the member touched the screen in the last 2 minutes.</li>"
        "<li>Logins are only recorded on a real sign-in. Members who stay signed in show activity with zero logins.</li>"
        "<li>Active means a login, session start, page view or heartbeat that day.</li></ul></details>"
        "</main></body></html>"
    )
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(page)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as src:
        render(json.load(src), sys.argv[2])
    print(sys.argv[2])
