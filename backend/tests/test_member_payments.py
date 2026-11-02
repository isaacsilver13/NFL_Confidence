"""Tests for commissioner weekly payment and unpaid-pick controls."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models import League, LeagueMember, NflGame, NflWeek, Pick, User
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.models.week_submission import WeekSubmission
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


def test_only_commissioner_can_manage_payments_and_void_unpaid_picks(client, db_session: Session):
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


def test_league_pot_reflects_submitted_member_count_and_clamps_first_place(
    client, db_session: Session
):
    owner, member, week, _pick = _fixture(db_session, client)
    league = db_session.query(League).one()

    extra_members = [_user(db_session, f"Extra{i}") for i in range(4)]
    for extra in extra_members:
        db_session.add(LeagueMember(league_id=league.id, user_id=extra.id, role=LeagueRole.MEMBER))
    db_session.flush()

    now = datetime.now(timezone.utc)
    for submitted_user in [owner, member, *extra_members]:
        db_session.add(
            WeekSubmission(
                week_id=week.id,
                user_id=submitted_user.id,
                submitted_at=now,
            )
        )
    db_session.commit()

    response = client.get("/api/v1/league/pot", headers=_headers(member))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["submittedMemberCount"] == 6
    assert data["potCents"] == 6000
    assert data["firstPlaceCents"] == 3000
    assert data["secondPlaceCents"] == 2000
    assert data["thirdPlaceCents"] == 1000
    assert data["isVisible"] is True

    # Below $60 (fewer than 6 submitted members), the small-pot table applies
    # instead of the standard $20/$10 second/third split.
    db_session.query(WeekSubmission).filter(WeekSubmission.user_id == extra_members[0].id).delete(
        synchronize_session=False
    )
    db_session.commit()

    response = client.get("/api/v1/league/pot", headers=_headers(member))
    data = response.json()["data"]
    assert data["submittedMemberCount"] == 5
    assert data["potCents"] == 5000
    assert data["firstPlaceCents"] == 3000
    assert data["secondPlaceCents"] == 1000
    assert data["thirdPlaceCents"] == 1000

    db_session.query(WeekSubmission).filter(WeekSubmission.user_id == extra_members[1].id).delete(
        synchronize_session=False
    )
    db_session.commit()

    response = client.get("/api/v1/league/pot", headers=_headers(member))
    data = response.json()["data"]
    assert data["submittedMemberCount"] == 4
    assert data["potCents"] == 4000
    assert data["firstPlaceCents"] == 2000
    assert data["secondPlaceCents"] == 1000
    assert data["thirdPlaceCents"] == 1000

    db_session.query(WeekSubmission).filter(
        WeekSubmission.user_id.in_([extra.id for extra in extra_members[1:]])
    ).delete(synchronize_session=False)
    db_session.commit()

    response = client.get("/api/v1/league/pot", headers=_headers(member))
    data = response.json()["data"]
    assert data["submittedMemberCount"] == 2
    assert data["potCents"] == 2000
    assert data["firstPlaceCents"] == 2000
    assert data["secondPlaceCents"] == 0
    assert data["thirdPlaceCents"] == 0


def test_league_pot_counts_complete_autosaved_cards_but_not_partial_ones(
    client, db_session: Session
):
    owner, member, week, _pick = _fixture(db_session, client)
    league = db_session.query(League).one()
    # Second game so "complete" means both picks, not just one.
    second_game = NflGame(
        week_id=week.id,
        espn_game_id=f"payments-{uuid.uuid4().hex}",
        kickoff_time=datetime.now(timezone.utc) - timedelta(hours=1),
        away_team="DAL",
        home_team="PHI",
        game_status=GameStatus.FINAL,
    )
    db_session.add(second_game)
    db_session.flush()
    first_game_id = _pick.game_id

    autosaver = _user(db_session, "Autosaver")
    partial = _user(db_session, "Partial")
    for user in (autosaver, partial):
        db_session.add(LeagueMember(league_id=league.id, user_id=user.id, role=LeagueRole.MEMBER))
    db_session.add_all(
        [
            Pick(user_id=autosaver.id, game_id=first_game_id, picked_team="KC", confidence_value=2),
            Pick(
                user_id=autosaver.id,
                game_id=second_game.id,
                picked_team="PHI",
                confidence_value=1,
            ),
            Pick(user_id=partial.id, game_id=first_game_id, picked_team="KC", confidence_value=2),
            # member's first pick (conf 1) is now incomplete for a 2-game week; submit them.
            WeekSubmission(
                week_id=week.id, user_id=member.id, submitted_at=datetime.now(timezone.utc)
            ),
        ]
    )
    db_session.commit()

    data = client.get("/api/v1/league/pot", headers=_headers(member)).json()["data"]
    # member (submitted) + autosaver (complete card); owner has nothing, partial is incomplete.
    assert data["submittedMemberCount"] == 2
    assert data["potCents"] == 2000


def test_league_pot_not_visible_before_the_weeks_first_kickoff(client, db_session: Session):
    owner = _user(db_session, "FutureOwner")
    league_response = client.post(
        "/api/v1/league",
        json={"name": "Future Kickoff League", "season": 2026},
        headers=_headers(owner),
    )
    assert league_response.status_code == 200

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
    db_session.add(
        NflGame(
            week_id=week.id,
            espn_game_id=f"pot-future-{uuid.uuid4().hex}",
            kickoff_time=now + timedelta(days=1),
            away_team="BUF",
            home_team="KC",
            game_status=GameStatus.SCHEDULED,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/league/pot", headers=_headers(owner))
    assert response.status_code == 200
    assert response.json()["data"]["isVisible"] is False
