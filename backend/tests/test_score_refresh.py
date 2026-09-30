"""Tests for the commissioner-only manual score/standings refresh."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models import League, LeagueMember, NflGame, NflWeek, Pick, User, WeeklyResult
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.models.job_execution import JobExecution
from app.services import score_refresh_service, weeks_service


def _user(db_session: Session, label: str) -> User:
    suffix = uuid.uuid4().hex
    user = User(
        google_id=f"refresh-{label}-{suffix}",
        email=f"refresh-{label}-{suffix}@example.com",
        display_name=label,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _fixture(db_session: Session, client) -> tuple[User, User, Pick]:
    """A league with a FINAL game whose pick has not been scored yet."""
    owner = _user(db_session, "Owner")
    member = _user(db_session, "Member")
    response = client.post(
        "/api/v1/league",
        json={"name": "Refresh League", "season": 2026},
        headers=_headers(owner),
    )
    assert response.status_code == 200
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
        espn_game_id=f"refresh-{uuid.uuid4().hex}",
        kickoff_time=now - timedelta(hours=4),
        away_team="BUF",
        home_team="KC",
        home_score=24,
        away_score=17,
        winning_team="KC",
        game_status=GameStatus.FINAL,
        is_tie=False,
    )
    db_session.add(game)
    db_session.flush()
    pick = Pick(user_id=member.id, game_id=game.id, picked_team="KC", confidence_value=3)
    db_session.add(pick)
    db_session.commit()
    return owner, member, pick


def test_member_cannot_refresh(client, db_session: Session):
    _, member, _ = _fixture(db_session, client)

    with patch.object(score_refresh_service, "fetch_schedule", return_value=[]) as fetch:
        response = client.post("/api/v1/league/refresh", headers=_headers(member))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    fetch.assert_not_called()


def test_commissioner_refresh_scores_picks_and_records_last_refreshed(client, db_session: Session):
    owner, member, pick = _fixture(db_session, client)
    assert pick.points_earned is None
    assert weeks_service.get_last_refreshed_at(db_session) is None

    with patch.object(score_refresh_service, "fetch_schedule", return_value=[]):
        response = client.post("/api/v1/league/refresh", headers=_headers(owner))

    assert response.status_code == 200
    assert response.json()["data"] == {"weeksRefreshed": 1, "gamesFinal": 1}

    db_session.expire_all()
    assert db_session.get(Pick, pick.id).points_earned == 3
    result = db_session.scalars(select(WeeklyResult).where(WeeklyResult.user_id == member.id)).one()
    assert result.total_points == 3
    assert result.correct_picks == 1

    execution = db_session.scalars(
        select(JobExecution).where(JobExecution.job_name == "manual_score_sync")
    ).one()
    assert execution.status == "success"
    assert execution.slot_key is None
    assert execution.result_count == 1
    assert weeks_service.get_last_refreshed_at(db_session) is not None


def test_refresh_is_idempotent(client, db_session: Session):
    owner, member, pick = _fixture(db_session, client)

    with patch.object(score_refresh_service, "fetch_schedule", return_value=[]):
        first = client.post("/api/v1/league/refresh", headers=_headers(owner))
        second = client.post("/api/v1/league/refresh", headers=_headers(owner))

    assert first.status_code == second.status_code == 200
    db_session.expire_all()
    assert db_session.get(Pick, pick.id).points_earned == 3
    results = db_session.scalars(
        select(WeeklyResult).where(WeeklyResult.user_id == member.id)
    ).all()
    assert len(results) == 1
    assert results[0].total_points == 3


def test_refresh_reports_upstream_failure_and_records_failed_run(client, db_session: Session):
    owner, _, pick = _fixture(db_session, client)

    with patch.object(
        score_refresh_service, "fetch_schedule", side_effect=httpx.ConnectError("boom")
    ):
        response = client.post("/api/v1/league/refresh", headers=_headers(owner))

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"

    db_session.expire_all()
    assert db_session.get(Pick, pick.id).points_earned is None
    execution = db_session.scalars(
        select(JobExecution).where(JobExecution.job_name == "manual_score_sync")
    ).one()
    assert execution.status == "failed"
    assert "boom" in (execution.error_message or "")
    assert weeks_service.get_last_refreshed_at(db_session) is None
