"""Tests for league creation, membership listing, invites, and joining."""

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


def test_create_league_makes_creator_the_owner(client, db_session: Session) -> None:
    owner = _make_user(
        db_session, google_id="g-owner", email="owner@example.com", display_name="Owner"
    )
    db_session.commit()

    response = client.post(
        "/api/v1/league",
        json={"name": "The League", "season": 2026},
        headers=_auth_header(owner),
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["name"] == "The League"
    assert body["season"] == 2026
    assert body["memberCount"] == 1
    assert body["commissionerName"] == "Owner"
    assert body["inviteCode"]


def test_create_league_fails_when_one_already_exists(client, db_session: Session) -> None:
    owner = _make_user(
        db_session, google_id="g-owner2", email="owner2@example.com", display_name="Owner2"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "First", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.post(
        "/api/v1/league", json={"name": "Second", "season": 2026}, headers=_auth_header(owner)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_get_league_requires_a_league_to_exist(client, db_session: Session) -> None:
    user = _make_user(
        db_session, google_id="g-nobody", email="nobody@example.com", display_name="Nobody"
    )
    db_session.commit()

    response = client.get("/api/v1/league", headers=_auth_header(user))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_get_league_returns_summary(client, db_session: Session) -> None:
    owner = _make_user(
        db_session, google_id="g-owner3", email="owner3@example.com", display_name="Owner3"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "My League", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/league", headers=_auth_header(owner))

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "My League"


def test_invite_requires_commissioner_role(client, db_session: Session) -> None:
    owner = _make_user(
        db_session, google_id="g-owner4", email="owner4@example.com", display_name="Owner4"
    )
    member = _make_user(
        db_session, google_id="g-member1", email="member1@example.com", display_name="Member1"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Owned", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.post(
        "/api/v1/league/invite",
        json={"email": "friend@example.com"},
        headers=_auth_header(member),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_invite_and_join_flow(client, db_session: Session) -> None:
    owner = _make_user(
        db_session, google_id="g-owner5", email="owner5@example.com", display_name="Owner5"
    )
    joiner = _make_user(
        db_session, google_id="g-joiner", email="joiner@example.com", display_name="Joiner"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Joinable", "season": 2026}, headers=_auth_header(owner)
    )

    invite_response = client.post(
        "/api/v1/league/invite",
        json={"email": "joiner@example.com"},
        headers=_auth_header(owner),
    )
    assert invite_response.status_code == 200
    assert invite_response.json()["data"]["email"] == "joiner@example.com"

    invite = db_session.query(Invite).filter_by(email="joiner@example.com").one()

    join_response = client.post(
        "/api/v1/league/join", json={"token": invite.token}, headers=_auth_header(joiner)
    )
    assert join_response.status_code == 200

    members_response = client.get("/api/v1/league/members", headers=_auth_header(owner))
    display_names = {m["displayName"] for m in members_response.json()["data"]}
    assert display_names == {"Owner5", "Joiner"}


def test_join_with_unknown_token_returns_404(client, db_session: Session) -> None:
    owner = _make_user(
        db_session, google_id="g-owner6", email="owner6@example.com", display_name="Owner6"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Solo", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.post(
        "/api/v1/league/join", json={"token": "not-a-real-token"}, headers=_auth_header(owner)
    )

    assert response.status_code == 404


def test_join_twice_with_same_invite_fails(client, db_session: Session) -> None:
    owner = _make_user(
        db_session, google_id="g-owner7", email="owner7@example.com", display_name="Owner7"
    )
    joiner = _make_user(
        db_session, google_id="g-joiner2", email="joiner2@example.com", display_name="Joiner2"
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Reused", "season": 2026}, headers=_auth_header(owner)
    )
    client.post(
        "/api/v1/league/invite",
        json={"email": "joiner2@example.com"},
        headers=_auth_header(owner),
    )
    invite = db_session.query(Invite).filter_by(email="joiner2@example.com").one()

    first_join = client.post(
        "/api/v1/league/join", json={"token": invite.token}, headers=_auth_header(joiner)
    )
    assert first_join.status_code == 200

    second_join = client.post(
        "/api/v1/league/join", json={"token": invite.token}, headers=_auth_header(joiner)
    )
    assert second_join.status_code == 409
