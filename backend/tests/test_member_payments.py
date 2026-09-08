"""Tests for commissioner weekly payment and unpaid-pick controls."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models import League, LeagueMember, NflGame, NflWeek, Pick, User
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.services import scoring_service


def _user(db_session: Session, label: str) -> User:
    suffix = uuid.uuid4().hex
    user = User(
        google_id=f"payments-{label}-{suffix}",
        email=f"payments-{label}-{suffix}@example.com",
        display_name=label,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _fixture(db_session: Session, client) -> tuple[User, User, NflWeek, Pick]:
    owner = _user(db_session, "Owner")
    member = _user(db_session, "Member")
    league_response = client.post(
        "/api/v1/league",
        json={"name": "Payments League", "season": 2026},
        headers=_headers(owner),
    )
    assert league_response.status_code == 200
    league = db_session.query(League).one()
    db_session.add(LeagueMember(league_id=league.id, user_id=member.id, role=LeagueRole.MEMBER))
    now = datetime.now(timezone.utc)
    week = NflWeek(
        season=2026,
        week_number=1,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=6),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()
    game = NflGame(
        week_id=week.id,
        espn_game_id=f"payments-{uuid.uuid4().hex}",
        kickoff_time=now - timedelta(hours=2),
        away_team="BUF",
        home_team="KC",
        winning_team="KC",
        game_status=GameStatus.FINAL,
    )
    db_session.add(game)
    db_session.flush()
    pick = Pick(
        user_id=member.id,
        game_id=game.id,
        picked_team="KC",
        confidence_value=1,
    )
    db_session.add(pick)
    db_session.commit()
    return owner, member, week, pick


def test_only_commissioner_can_manage_payments_and_void_unpaid_picks(
    client, db_session: Session
):
    owner, member, week, pick = _fixture(db_session, client)

    forbidden = client.get(
        f"/api/v1/league/payments?week={week.week_number}", headers=_headers(member)
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    marked_paid = client.patch(
        f"/api/v1/league/payments/{member.id}",
        json={"week": week.week_number, "isPaid": True},
        headers=_headers(owner),
    )
    assert marked_paid.status_code == 200

    statuses = client.get(
        f"/api/v1/league/payments?week={week.week_number}", headers=_headers(owner)
    )
    assert statuses.status_code == 200
    member_status = next(
        status
        for status in statuses.json()["data"]["members"]
        if status["userId"] == str(member.id)
    )
    assert member_status["isPaid"] is True

    marked_unpaid = client.patch(
        f"/api/v1/league/payments/{member.id}",
        json={"week": week.week_number, "isPaid": False},
        headers=_headers(owner),
    )
    assert marked_unpaid.status_code == 200

    voided = client.post(
        "/api/v1/league/payments/void-unpaid",
        json={"week": week.week_number},
        headers=_headers(owner),
    )
    assert voided.status_code == 200
    assert voided.json()["data"] == {
        "week": 1,
        "voidedPickCount": 1,
        "affectedMemberCount": 1,
    }
    db_session.refresh(pick)
    assert pick.voided_at is not None
    assert pick.points_earned is None

    league = db_session.query(League).one()
    scoring_service.score_week(db_session, league=league, week_id=week.id)
    db_session.refresh(pick)
    assert pick.voided_at is not None
    assert pick.points_earned is None