"""Self-check for render_report.py. Run: python .claude/skills/usage-report/test_render.py"""

import os
import re
import tempfile

import render_report

EMPTY = {name: [] for name in render_report.QUERY_NAMES}

SAMPLE = {
    **EMPTY,
    "users": [
        {"user_id": "u1", "display_name": "Alice <b>"},
        {"user_id": "u2", "display_name": "Bob"},
        {"user_id": "u3", "display_name": "Cara"},
    ],
    "logins_per_user": [
        {"user_id": "u1", "login_count": 5, "last_login": "2026-11-10T14:00:00+00:00"},
        {"user_id": "u2", "login_count": 1, "last_login": "2026-11-08T14:00:00+00:00"},
    ],
    "active_buckets_per_user": [{"user_id": "u1", "buckets": 10}],
    "page_views": [{"user_id": "u1", "path": "/picks", "views": 7}],
    "section_opens": [{"user_id": "u1", "section": "standings", "opens": 2}],
    "dau": [
        {"day": "2026-11-08", "users": 1},
        {"day": "2026-11-09", "users": 0},
        {"day": "2026-11-10", "users": 2},
    ],
    "wau": [{"week_start": "2026-11-02", "users": 1}, {"week_start": "2026-11-09", "users": 2}],
    "login_series": [
        {"user_id": "u1", "day": "2026-11-08", "logins": 2},
        {"user_id": "u1", "day": "2026-11-10", "logins": 3},
        {"user_id": "u2", "day": "2026-11-08", "logins": 1},
    ],
    "device_split": [{"device": "phone", "sessions": 9}, {"device": "desktop", "sessions": 1}],
    "feature_adoption": [
        {"feature": "Picks page", "users": 2, "events": 9},
        {"feature": "Standings section", "users": 0, "events": 0},
    ],
    "never_returned": [
        {"user_id": "u2", "status": "never returned"},
        {"user_id": "u3", "status": "no data yet"},
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
    assert "No data yet" in html
    assert html.startswith("<!doctype html>")


def test_renders_sample() -> None:
    html = render(SAMPLE)
    for name in ("Bob", "Cara"):
        assert name in html
    assert "<svg" in html
    # 10 heartbeat buckets x 30 s = 5 minutes of active time for Alice
    assert "5m" in html
    assert "never returned" in html and "no data yet" in html


def test_escapes_display_names() -> None:
    html = render(SAMPLE)
    assert "Alice <b>" not in html
    assert "Alice &lt;b&gt;" in html


def test_ignored_features_are_listed() -> None:
    html = render(SAMPLE)
    assert "Standings section" in html
    assert "ignored" in html.lower()


def test_no_external_requests() -> None:
    html = render(SAMPLE)
    assert not re.search(r"https?://", html)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
