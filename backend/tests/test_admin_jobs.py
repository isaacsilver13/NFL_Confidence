"""Admin job routes: commissioners only, and manual runs go through the tick's slot claim."""

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models import LeagueMember, User
from app.models.enums import LeagueRole
from tests.test_internal_tick import calls, executions  # noqa: F401


def _auth(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_member_cannot_reach_admin_jobs(client, db_session: Session, league_with_owner) -> None:
    member = User(google_id="g-admin-member", email="m@ex.com", display_name="Member")
    db_session.add(member)
    db_session.flush()
    db_session.add(
        LeagueMember(league_id=league_with_owner.id, user_id=member.id, role=LeagueRole.MEMBER)
    )
    db_session.flush()

    for method, path in (
        ("get", "/api/v1/admin/jobs/status"),
        ("get", "/api/v1/admin/jobs/runs"),
        ("post", "/api/v1/admin/jobs/weekly_picks_reminder/trigger"),
    ):
        assert getattr(client, method)(path, headers=_auth(member)).status_code == 403


def test_co_commissioner_triggers_once_per_minute_and_it_is_logged(
    client, db_session: Session, league_with_owner, calls  # noqa: F811
) -> None:
    co = User(google_id="g-admin-co", email="co@ex.com", display_name="Co")
    db_session.add(co)
    db_session.flush()
    db_session.add(
        LeagueMember(league_id=league_with_owner.id, user_id=co.id, role=LeagueRole.OWNER)
    )
    db_session.flush()
    url = "/api/v1/admin/jobs/weekly_picks_reminder/trigger"

    first = client.post(url, headers=_auth(co))
    second = client.post(url, headers=_auth(co))

    assert first.status_code == 200 and first.json()["data"]["status"] == "success"
    assert second.status_code == 409
    assert calls == {"weekly_picks_reminder": 1}
    [run] = executions(db_session)
    assert run.slot_key.startswith("manual:") and run.status == "success"
    runs = client.get("/api/v1/admin/jobs/runs", headers=_auth(co)).json()["data"]["runs"]
    assert [r["job_name"] for r in runs] == ["weekly_picks_reminder"]


def test_unknown_job_is_rejected(client, owner_user, league_with_owner) -> None:
    response = client.post("/api/v1/admin/jobs/nope/trigger", headers=_auth(owner_user))
    assert response.status_code == 400
