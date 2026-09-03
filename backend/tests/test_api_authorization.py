"""Tests for league-scoped API authorization (Phase 1A).

Verifies that non-members receive 403 for all league-scoped routes.
"""

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models.invite import Invite
from app.models.user import User


def _make_user(db_session: Session, *, google_id: str, email: str, display_name: str) -> User:
    user = User(google_id=google_id, email=email, display_name=display_name)
    db_session.add(user)
    db_session.flush()
    return user


def _auth_header(user: User) -> dict[str, str]:
    access_token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {access_token}"}


def test_non_member_gets_403_on_get_picks_current(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /picks/current."""
    owner = _make_user(
        db_session, google_id="g-owner-picks1", email="owner-picks1@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-picks1", email="non-picks1@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Picks Test", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/picks/current", headers=_auth_header(non_member))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_non_member_gets_403_on_get_picks_history(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /picks/history."""
    owner = _make_user(
        db_session, google_id="g-owner-picks2", email="owner-picks2@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-picks2", email="non-picks2@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Picks Test 2", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/picks/history", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_post_picks(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing POST /picks."""
    owner = _make_user(
        db_session, google_id="g-owner-picks3", email="owner-picks3@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-picks3", email="non-picks3@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Picks Test 3", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.post(
        "/api/v1/picks", json={"week": 1, "picks": []}, headers=_auth_header(non_member)
    )

    assert response.status_code == 403


def test_non_member_gets_403_on_get_weeks_current(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /weeks/current."""
    owner = _make_user(
        db_session, google_id="g-owner-weeks1", email="owner-weeks1@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-weeks1", email="non-weeks1@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Weeks Test", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/weeks/current", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_get_weeks_all(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /weeks."""
    owner = _make_user(
        db_session, google_id="g-owner-weeks2", email="owner-weeks2@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-weeks2", email="non-weeks2@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Weeks Test 2", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/weeks", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_get_games_current(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /games/current."""
    owner = _make_user(
        db_session, google_id="g-owner-games1", email="owner-games1@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-games1", email="non-games1@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Games Test", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/games/current", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_get_games_by_week(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /games."""
    owner = _make_user(
        db_session, google_id="g-owner-games2", email="owner-games2@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-games2", email="non-games2@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Games Test 2", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/games?week=1", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_get_leaderboard_weeks(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /leaderboard/weeks."""
    owner = _make_user(
        db_session, google_id="g-owner-lb1", email="owner-lb1@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-lb1", email="non-lb1@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "LB Test", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/leaderboard/weeks", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_get_leaderboard_week(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /leaderboard/week."""
    owner = _make_user(
        db_session, google_id="g-owner-lb2", email="owner-lb2@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-lb2", email="non-lb2@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "LB Test 2", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/leaderboard/week", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_get_leaderboard_season(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /leaderboard/season."""
    owner = _make_user(
        db_session, google_id="g-owner-lb3", email="owner-lb3@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-lb3", email="non-lb3@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "LB Test 3", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/leaderboard/season", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_non_member_gets_403_on_get_leaderboard_pick_breakdown(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /leaderboard/pick-breakdown."""
    owner = _make_user(
        db_session, google_id="g-owner-lb4", email="owner-lb4@ex.com", display_name="Owner"
    )
    non_member = _make_user(
        db_session, google_id="g-non-lb4", email="non-lb4@ex.com", display_name="NonMember"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "LB Test 4", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/leaderboard/pick-breakdown", headers=_auth_header(non_member))

    assert response.status_code == 403


def test_member_can_access_league_scoped_routes(client, db_session: Session) -> None:
    """Members should receive 200 (or appropriate success) when accessing league-scoped routes."""
    owner = _make_user(
        db_session, google_id="g-owner-member", email="owner-member@ex.com", display_name="Owner"
    )
    member = _make_user(
        db_session, google_id="g-member-access", email="member-access@ex.com", display_name="Member"
    )
    db_session.commit()
    client.post(
        "/api/v1/league",
        json={"name": "Member Access", "season": 2026},
        headers=_auth_header(owner),
    )

    # Create and accept an invite
    client.post(
        "/api/v1/league/invite",
        json={"email": "member-access@ex.com"},
        headers=_auth_header(owner),
    )
    invite = db_session.query(Invite).filter_by(email="member-access@ex.com").one()
    client.post("/api/v1/league/join", json={"token": invite.token}, headers=_auth_header(member))

    # Now test that member can access all league-scoped routes (gets 200 or 404 for data endpoints)
    assert client.get("/api/v1/league", headers=_auth_header(member)).status_code == 200
    assert client.get("/api/v1/league/members", headers=_auth_header(member)).status_code == 200
    assert client.get("/api/v1/picks/current", headers=_auth_header(member)).status_code in (
        200,
        404,
    )
    assert client.get("/api/v1/picks/history", headers=_auth_header(member)).status_code in (
        200,
        404,
    )
    assert client.get("/api/v1/weeks/current", headers=_auth_header(member)).status_code in (
        200,
        404,
    )
    assert client.get("/api/v1/weeks", headers=_auth_header(member)).status_code == 200
    assert client.get("/api/v1/games/current", headers=_auth_header(member)).status_code in (
        200,
        404,
    )
    assert client.get("/api/v1/leaderboard/weeks", headers=_auth_header(member)).status_code == 200
    assert client.get(
        "/api/v1/leaderboard/pick-breakdown", headers=_auth_header(member)
    ).status_code in (200, 404)
