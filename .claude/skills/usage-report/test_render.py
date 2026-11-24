"""Self-check for render_report.py. Run: python .claude/skills/usage-report/test_render.py"""

import os
import re
import tempfile

import render_report

EMPTY = {name: [] for name in render_report.QUERY_NAMES}

SAMPLE = {
    **EMPTY,
    "window": {"since": "2026-11-17", "until": "2026-11-24"},
    "users": [
        {"user_id": "u1", "display_name": "Alice <b>"},
        {"user_id": "u2", "display_name": "Bob"},
        {"user_id": "u3", "display_name": "Cara"},
        {"user_id": "u4", "display_name": "Dan"},
    ],
    "logins_per_user": [
        {"user_id": "u1", "login_count": 5, "last_login": "2026-11-20T14:00:00+00:00"},
        {"user_id": "u2", "login_count": 1, "last_login": "2026-11-18T14:00:00+00:00"},
    ],
    "active_buckets_per_user": [{"user_id": "u1", "buckets": 10}],
    "page_views": [{"user_id": "u1", "path": "/picks", "views": 7}],
    "section_opens": [{"user_id": "u1", "section": "standings", "opens": 2}],
    "dau": [
        {"day": "2026-11-18", "users": 1},
        {"day": "2026-11-19", "users": 0},
        {"day": "2026-11-20", "users": 2},
    ],
    "device_split": [{"device": "phone", "sessions": 9}, {"device": "desktop", "sessions": 1}],
    "feature_adoption": [
        {"feature": "Picks page", "users": 2, "events": 9},
        {"feature": "Standings section", "users": 0, "events": 0},
        {"feature": "Made picks (all-time)", "users": 4, "events": 40},
    ],
    "never_returned": [
        {"user_id": "u2", "status": "never returned", "day": "2026-11-18"},
        {"user_id": "u3", "status": "no data yet", "day": None},
    ],
}


def render(data: dict) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "report.html")
        render_report.render(data, out)
        with open(out, encoding="utf-8") as handle:
            return handle.read()


def test_renders_with_empty_data() -> None:
    html = render(EMPTY)
    assert html.startswith("<!doctype html>")
    assert "No activity in this period" in html
    assert "No members" in html


def test_renders_sample() -> None:
    html = render(SAMPLE)
    for name in ("Bob", "Cara", "Dan"):
        assert name in html
    assert "<svg" in html
    # 10 heartbeat buckets x 30 s = 5 minutes of active time for Alice
    assert "<td class='n'><span class='bar' style='width:60px'></span>5</td>" in html
    # two of four members were active; the lede and the tile agree
    assert "2 of 4 members used the app in this period" in html
    assert "Nov 17 to Nov 24" in html
    assert "90<small>%</small>" in html  # 9 of 10 sessions on a phone


def test_statuses_and_follow_up_lists() -> None:
    html = render(SAMPLE)
    assert "pill Active" in html
    assert "pill Quiet" in html  # Dan: not active in the window, but not a no-data member
    assert "pill Nodatayet" in html  # Cara
    assert "1 were quiet and 1 have no tracked activity" in html


def test_escapes_display_names() -> None:
    html = render(SAMPLE)
    assert "Alice <b>" not in html
    assert "Alice &lt;b&gt;" in html


def test_unused_features_show_zero_and_history_is_separate() -> None:
    html = render(SAMPLE)
    assert "Standings section" in html
    assert "Made picks (all-time)" in html
    assert "all weeks, not only this period" in html


def test_no_external_requests_or_scripts() -> None:
    html = render(SAMPLE)
    assert not re.search(r"https?://", html)
    assert "<script" not in html


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
