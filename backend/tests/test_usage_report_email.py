"""The weekly usage report email: rendering, the job, and its SQL on seeded rows."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.jobs import usage_report
from app.models.audit_log import AuditLog
from app.models.enums import LeagueRole
from app.models.league_member import LeagueMember
from app.models.usage_event import UsageEvent
from app.models.user import User
from app.services import usage_report_service

SINCE, UNTIL = date(2026, 11, 17), date(2026, 11, 24)

DATA = {
    "users": [
        {"user_id": "u1", "display_name": "Alice <b>"},
        {"user_id": "u2", "display_name": "Bob"},
        {"user_id": "u3", "display_name": "Cara"},
        {"user_id": "u4", "display_name": "Dan"},
    ],
    "logins_per_user": [
        {"user_id": "u2", "login_count": 1, "last_login": "2026-11-18T14:00:00+00:00"}
    ],
    "active_buckets_per_user": [{"user_id": "u1", "buckets": 10}],
    "page_views": [{"user_id": "u1", "path": "/picks", "views": 7}],
    "section_opens": [{"user_id": "u1", "section": "standings", "opens": 2}],
    "dau": [{"day": "2026-11-18", "users": 2}, {"day": "2026-11-19", "users": 0}],
    "device_split": [{"device": "phone", "sessions": 9}, {"device": "desktop", "sessions": 1}],
    "feature_adoption": [
        {"feature": "Picks page", "users": 1, "events": 7},
        {"feature": "Standings section", "users": 0, "events": 0},
        {"feature": "Made picks (all-time)", "users": 4, "events": 40},
    ],
    "no_data": [{"user_id": "u3"}],
}


def test_email_html_is_email_safe_and_escaped() -> None:
    html = usage_report_service.render_email_html(DATA, SINCE, UNTIL)
    # Gmail drops CSS variables, <style> blocks it does not know, scripts and inline SVG.
    for banned in ("var(", "<svg", "<script", "<style"):
        assert banned not in html
    assert "Alice <b>" not in html
    assert "Alice &lt;b&gt;" in html
    assert "Nov 17 to Nov 24" in html


def test_email_html_summarises_the_period() -> None:
    html = usage_report_service.render_email_html(DATA, SINCE, UNTIL)
    assert "2 of 4 members used the app in this period" in html
    assert "1 were quiet and 1 have no tracked activity" in html  # Dan quiet, Cara no data
    assert "5 min" in html  # 10 heartbeat buckets x 30 s
    assert "90%" in html  # 9 of 10 sessions on a phone
    assert "Standings section" in html and "Made picks (all-time)" in html


def test_email_html_renders_with_no_activity() -> None:
    empty = {name: [] for name in DATA}
    html = usage_report_service.render_email_html(empty, SINCE, UNTIL)
    assert "0 of 0 members" in html
    assert "No activity in this period" in html


@pytest.fixture()
def sent(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> list[dict]:
    calls: list[dict] = []
    monkeypatch.setattr(usage_report, "send_email", lambda **kw: calls.append(kw))

    class _Session:  # hand the job the test transaction instead of a new connection
        def __enter__(self):
            return db_session

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(usage_report, "SessionLocal", _Session)
    return calls


def test_job_does_nothing_without_a_league(sent: list[dict]) -> None:
    assert usage_report.send_weekly_usage_report() == 0
    assert sent == []


def test_job_sends_one_email_to_every_commissioner(
    sent: list[dict], db_session: Session, league_with_owner, owner_user, another_user
) -> None:
    co = User(google_id="g-co", email="co@example.com", display_name="Co")
    db_session.add(co)
    db_session.flush()
    db_session.add(
        LeagueMember(league_id=league_with_owner.id, user_id=co.id, role=LeagueRole.OWNER)
    )
    db_session.add(
        LeagueMember(
            league_id=league_with_owner.id, user_id=another_user.id, role=LeagueRole.MEMBER
        )
    )
    db_session.flush()

    assert usage_report.send_weekly_usage_report() == 2
    assert len(sent) == 1  # one email, not one per commissioner
    assert sorted(sent[0]["to"]) == sorted([owner_user.email, "co@example.com"])
    assert another_user.email not in sent[0]["to"]  # plain members never get it
    assert sent[0]["subject"].startswith("NFL Confidence usage: ")
    assert "NFL Confidence member usage" in sent[0]["html"]


def _at(day: int, hour: int = 15, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc)


def test_collect_runs_on_seeded_rows(db_session: Session) -> None:
    alice = User(google_id="g-a", email="a@example.com", display_name="Alice")
    bob = User(google_id="g-b", email="b@example.com", display_name="Bob")
    cara = User(google_id="g-c", email="c@example.com", display_name="Cara")
    db_session.add_all([alice, bob, cara])
    db_session.flush()
    db_session.add_all(
        [
            AuditLog(user_id=alice.id, action="login", entity="auth", created_at=_at(8)),
            AuditLog(user_id=alice.id, action="login", entity="auth", created_at=_at(10)),
            UsageEvent(
                user_id=alice.id, action="session_start", device="phone", created_at=_at(10)
            ),
            UsageEvent(user_id=alice.id, action="page_view", path="/picks", created_at=_at(10)),
            UsageEvent(
                user_id=alice.id, action="section_open", section="standings", created_at=_at(10)
            ),
            UsageEvent(user_id=alice.id, action="heartbeat", created_at=_at(10, 15, 0)),
            UsageEvent(user_id=alice.id, action="heartbeat", created_at=_at(10, 15, 1)),
            UsageEvent(user_id=bob.id, action="page_view", path="/", created_at=_at(9)),
        ]
    )
    db_session.flush()

    data = usage_report_service.collect(db_session, date(2026, 11, 10), "America/Chicago")

    assert {u["display_name"] for u in data["users"]} == {"Alice", "Bob", "Cara"}
    assert {r["user_id"]: r["login_count"] for r in data["logins_per_user"]} == {str(alice.id): 1}
    assert [(r["user_id"], r["buckets"]) for r in data["active_buckets_per_user"]] == [
        (str(alice.id), 2)
    ]
    assert [r["day"] for r in data["dau"]] == ["2026-11-10"]  # Bob's 9th is before the window
    assert data["device_split"] == [{"device": "phone", "sessions": 1}]
    by_feature = {r["feature"]: r["users"] for r in data["feature_adoption"]}
    assert by_feature["Picks page"] == 1 and by_feature["Dashboard page"] == 0
    assert data["no_data"] == [{"user_id": str(cara.id)}]  # Bob has older activity, Cara none
