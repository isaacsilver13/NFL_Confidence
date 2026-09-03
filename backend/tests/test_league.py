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

    # Authorization check returns 403 if no active league exists (doesn't reveal league status)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


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
    """Members who are not owners should receive 403 when trying to create an invite."""
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

    # Add the member to the league
    client.post(
        "/api/v1/league/invite",
        json={"email": "member1@example.com"},
        headers=_auth_header(owner),
    )
    invite = db_session.query(Invite).filter_by(email="member1@example.com").one()
    client.post("/api/v1/league/join", json={"token": invite.token}, headers=_auth_header(member))

    # Now try to create an invite as a non-owner member
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


def test_join_with_league_passcode(client, db_session: Session) -> None:
    owner = _make_user(
        db_session,
        google_id="g-owner-code",
        email="owner-code@example.com",
        display_name="Owner",
    )
    joiner = _make_user(
        db_session,
        google_id="g-joiner-code",
        email="joiner-code@example.com",
        display_name="Joiner",
    )
    db_session.commit()
    create_response = client.post(
        "/api/v1/league",
        json={"name": "Passcode League", "season": 2026},
        headers=_auth_header(owner),
    )
    code = create_response.json()["data"]["inviteCode"]

    response = client.post(
        "/api/v1/league/join-with-code",
        json={"code": f"  {code}  "},
        headers=_auth_header(joiner),
    )

    assert response.status_code == 200
    members = client.get("/api/v1/league/members", headers=_auth_header(owner)).json()["data"]
    assert {member["displayName"] for member in members} == {"Owner", "Joiner"}


def test_join_with_invalid_league_passcode_fails(client, db_session: Session) -> None:
    owner = _make_user(
        db_session,
        google_id="g-owner-bad-code",
        email="owner-bad-code@example.com",
        display_name="Owner",
    )
    joiner = _make_user(
        db_session,
        google_id="g-joiner-bad-code",
        email="joiner-bad-code@example.com",
        display_name="Joiner",
    )
    db_session.commit()
    client.post(
        "/api/v1/league",
        json={"name": "Passcode League", "season": 2026},
        headers=_auth_header(owner),
    )

    response = client.post(
        "/api/v1/league/join-with-code",
        json={"code": "wrong-code"},
        headers=_auth_header(joiner),
    )

    assert response.status_code == 422


def test_commissioner_can_remove_member(client, db_session: Session) -> None:
    owner = _make_user(
        db_session,
        google_id="g-owner-remove",
        email="owner-remove@example.com",
        display_name="Owner",
    )
    member = _make_user(
        db_session,
        google_id="g-member-remove",
        email="member-remove@example.com",
        display_name="Member",
    )
    db_session.commit()
    create_response = client.post(
        "/api/v1/league",
        json={"name": "Removal League", "season": 2026},
        headers=_auth_header(owner),
    )
    code = create_response.json()["data"]["inviteCode"]
    client.post(
        "/api/v1/league/join-with-code", json={"code": code}, headers=_auth_header(member)
    )
    member_record = next(
        item
        for item in client.get("/api/v1/league/members", headers=_auth_header(owner)).json()["data"]
        if item["userId"] == str(member.id)
    )
    response = client.delete(
        f"/api/v1/league/members/{member.id}", headers=_auth_header(owner)
    )

    assert response.status_code == 204
    assert client.get("/api/v1/league", headers=_auth_header(member)).status_code == 403
    assert member_record["displayName"] == "Member"


def test_non_commissioner_cannot_remove_member(client, db_session: Session) -> None:
    owner = _make_user(
        db_session,
        google_id="g-owner-no-remove",
        email="owner-no-remove@example.com",
        display_name="Owner",
    )
    member = _make_user(
        db_session,
        google_id="g-member-no-remove",
        email="member-no-remove@example.com",
        display_name="Member",
    )
    db_session.commit()
    create_response = client.post(
        "/api/v1/league",
        json={"name": "Removal League", "season": 2026},
        headers=_auth_header(owner),
    )
    code = create_response.json()["data"]["inviteCode"]
    client.post(
        "/api/v1/league/join-with-code", json={"code": code}, headers=_auth_header(member)
    )

    response = client.delete(
        f"/api/v1/league/members/{owner.id}", headers=_auth_header(member)
    )

    assert response.status_code == 403


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


# Tests for active-league membership authorization (Phase 1A)


def test_non_member_cannot_view_league(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /league."""
    owner = _make_user(
        db_session,
        google_id="g-owner-auth1",
        email="owner-auth1@example.com",
        display_name="Owner1",
    )
    non_member = _make_user(
        db_session,
        google_id="g-non-member1",
        email="non-member1@example.com",
        display_name="NonMember1",
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Private", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/league", headers=_auth_header(non_member))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_non_member_cannot_view_league_members(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing GET /league/members."""
    owner = _make_user(
        db_session,
        google_id="g-owner-auth2",
        email="owner-auth2@example.com",
        display_name="Owner2",
    )
    non_member = _make_user(
        db_session,
        google_id="g-non-member2",
        email="non-member2@example.com",
        display_name="NonMember2",
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Private2", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.get("/api/v1/league/members", headers=_auth_header(non_member))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_non_member_cannot_create_invite(client, db_session: Session) -> None:
    """Non-members should receive 403 when accessing POST /league/invite."""
    owner = _make_user(
        db_session,
        google_id="g-owner-auth3",
        email="owner-auth3@example.com",
        display_name="Owner3",
    )
    non_member = _make_user(
        db_session,
        google_id="g-non-member3",
        email="non-member3@example.com",
        display_name="NonMember3",
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "Private3", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.post(
        "/api/v1/league/invite",
        json={"email": "someone@example.com"},
        headers=_auth_header(non_member),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_member_can_view_league(client, db_session: Session) -> None:
    """Members should receive 200 when accessing GET /league."""
    owner = _make_user(
        db_session,
        google_id="g-owner-auth4",
        email="owner-auth4@example.com",
        display_name="Owner4",
    )
    member = _make_user(
        db_session,
        google_id="g-member-auth1",
        email="member-auth1@example.com",
        display_name="Member1",
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "MemberAccess", "season": 2026}, headers=_auth_header(owner)
    )
    client.post(
        "/api/v1/league/invite",
        json={"email": "member-auth1@example.com"},
        headers=_auth_header(owner),
    )
    invite_token = db_session.query(Invite).filter_by(email="member-auth1@example.com").one().token
    client.post("/api/v1/league/join", json={"token": invite_token}, headers=_auth_header(member))

    response = client.get("/api/v1/league", headers=_auth_header(member))

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "MemberAccess"


def test_owner_can_create_invite(client, db_session: Session) -> None:
    """Owners should receive 200 when accessing POST /league/invite."""
    owner = _make_user(
        db_session,
        google_id="g-owner-auth5",
        email="owner-auth5@example.com",
        display_name="Owner5",
    )
    db_session.commit()
    client.post(
        "/api/v1/league", json={"name": "OwnerInvite", "season": 2026}, headers=_auth_header(owner)
    )

    response = client.post(
        "/api/v1/league/invite",
        json={"email": "newmember@example.com"},
        headers=_auth_header(owner),
    )

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "newmember@example.com"


def test_member_cannot_create_invite(client, db_session: Session) -> None:
    """Non-owner members should receive 403 when accessing POST /league/invite."""
    owner = _make_user(
        db_session,
        google_id="g-owner-auth6",
        email="owner-auth6@example.com",
        display_name="Owner6",
    )
    member = _make_user(
        db_session,
        google_id="g-member-auth2",
        email="member-auth2@example.com",
        display_name="Member2",
    )
    db_session.commit()
    client.post(
        "/api/v1/league",
        json={"name": "MemberNoInvite", "season": 2026},
        headers=_auth_header(owner),
    )
    invite_token = (
        db_session.query(Invite).filter(Invite.email == "member-auth2@example.com").first()
    )
    if not invite_token:
        client.post(
            "/api/v1/league/invite",
            json={"email": "member-auth2@example.com"},
            headers=_auth_header(owner),
        )
        invite_token = (
            db_session.query(Invite).filter_by(email="member-auth2@example.com").one().token
        )
    else:
        invite_token = invite_token.token

    client.post("/api/v1/league/join", json={"token": invite_token}, headers=_auth_header(member))

    response = client.post(
        "/api/v1/league/invite",
        json={"email": "another@example.com"},
        headers=_auth_header(member),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
