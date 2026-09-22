"""Tests for the commissioner's weekly pick-submission status view."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models import League, LeagueMember, NflGame, NflWeek, User
from app.models.enums import GameStatus, LeagueRole, WeekStatus


def _user(db_session: Session, label: str) -> User:
    suffix = uuid.uuid4().hex
    user = User(
        google_id=f"submissions-{label}-{suffix}",
        email=f"submissions-{label}-{suffix}@example.com",
        display_name=label,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _fixture(db_session: Session, client) -> tuple[User, User, NflWeek, NflGame]:
    owner = _user(db_session, "Owner")
    member = _user(db_session, "Member")
    league_response = client.post(
        "/api/v1/league",
        json={"name": "Submissions League", "season": 2026},
        headers=_headers(owner),
    )
    assert league_response.status_code == 200
    league = db_session.query(League).one()
    db_session.add(LeagueMember(league_id=league.id, user_id=member.id, role=LeagueRole.MEMBER))
    now = datetime.now(timezone.utc)
    week = NflWeek(
        season=2026,
        week_number=1,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(days=6),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()
    game = NflGame(
        week_id=week.id,
        espn_game_id=f"submissions-{uuid.uuid4().hex}",
        kickoff_time=now + timedelta(days=1),
        away_team="BUF",
        home_team="KC",
        game_status=GameStatus.SCHEDULED,
    )
    db_session.add(game)
    db_session.commit()
    return owner, member, week, game


def test_only_commissioner_can_view_submission_statuses(client, db_session: Session):
    owner, member, week, _game = _fixture(db_session, client)

    forbidden = client.get(
        f"/api/v1/league/submissions?week={week.week_number}", headers=_headers(member)
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    allowed = client.get(
        f"/api/v1/league/submissions?week={week.week_number}", headers=_headers(owner)
    )
    assert allowed.status_code == 200


def test_submission_statuses_reflect_submitted_and_unsubmitted_members(client, db_session: Session):
    owner, member, week, game = _fixture(db_session, client)

    statuses = client.get(
        f"/api/v1/league/submissions?week={week.week_number}", headers=_headers(owner)
    ).json()["data"]["members"]
    member_status = next(s for s in statuses if s["userId"] == str(member.id))
    assert member_status["submittedAt"] is None
    assert member_status["pickCount"] == 0

    save_response = client.post(
        "/api/v1/picks",
        json={
            "week": week.week_number,
            "picks": [{"gameId": str(game.id), "team": game.home_team, "confidence": 1}],
        },
        headers=_headers(member),
    )
    assert save_response.status_code == 200
    submit_response = client.post(
        "/api/v1/picks/submit",
        json={"week": week.week_number},
        headers=_headers(member),
    )
    assert submit_response.status_code == 200

    statuses = client.get(
        f"/api/v1/league/submissions?week={week.week_number}", headers=_headers(owner)
    ).json()["data"]["members"]
    member_status = next(s for s in statuses if s["userId"] == str(member.id))
    assert member_status["submittedAt"] is not None
    assert member_status["pickCount"] == 1

    owner_status = next(s for s in statuses if s["userId"] == str(owner.id))
    assert owner_status["submittedAt"] is None
