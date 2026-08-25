"""Tests for SQLAlchemy models: constraints, defaults, and cascade behavior."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import League, LeagueMember, NflGame, NflWeek, Pick, User
from app.models.enums import GameStatus, LeagueRole, WeekStatus


def _make_user(db_session: Session, *, google_id: str, email: str) -> User:
    user = User(google_id=google_id, email=email, display_name=email.split("@")[0])
    db_session.add(user)
    db_session.flush()
    return user


def _make_week(db_session: Session, *, season: int = 2026, week_number: int = 1) -> NflWeek:
    now = datetime.now(timezone.utc)
    week = NflWeek(
        season=season,
        week_number=week_number,
        start_date=now,
        end_date=now + timedelta(days=7),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()
    return week


def _make_game(db_session: Session, week: NflWeek, *, espn_game_id: str = "espn-1") -> NflGame:
    game = NflGame(
        week_id=week.id,
        espn_game_id=espn_game_id,
        kickoff_time=datetime.now(timezone.utc),
        home_team="KC",
        away_team="BUF",
        game_status=GameStatus.SCHEDULED,
    )
    db_session.add(game)
    db_session.flush()
    return game


def test_user_defaults(db_session: Session) -> None:
    user = _make_user(db_session, google_id="g-1", email="alice@example.com")

    assert user.id is not None
    assert user.created_at is not None
    assert user.updated_at is not None


def test_user_email_must_be_unique(db_session: Session) -> None:
    _make_user(db_session, google_id="g-1", email="dupe@example.com")
    db_session.add(User(google_id="g-2", email="dupe@example.com", display_name="Bob"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_league_member_role_default_and_uniqueness(db_session: Session) -> None:
    owner = _make_user(db_session, google_id="g-owner", email="owner@example.com")
    league = League(name="Office Pool", owner_id=owner.id, season=2026, invite_code="ABC123")
    db_session.add(league)
    db_session.flush()

    membership = LeagueMember(league_id=league.id, user_id=owner.id)
    db_session.add(membership)
    db_session.flush()

    assert membership.role == LeagueRole.MEMBER

    db_session.add(LeagueMember(league_id=league.id, user_id=owner.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_pick_unique_per_user_and_game(db_session: Session) -> None:
    user = _make_user(db_session, google_id="g-pick", email="picker@example.com")
    week = _make_week(db_session)
    game = _make_game(db_session, week)

    db_session.add(Pick(user_id=user.id, game_id=game.id, picked_team="KC", confidence_value=10))
    db_session.flush()

    db_session.add(Pick(user_id=user.id, game_id=game.id, picked_team="BUF", confidence_value=9))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_user_cascades_picks(db_session: Session) -> None:
    user = _make_user(db_session, google_id="g-cascade", email="cascade@example.com")
    week = _make_week(db_session, week_number=2)
    game = _make_game(db_session, week, espn_game_id="espn-cascade")
    pick = Pick(user_id=user.id, game_id=game.id, picked_team="KC", confidence_value=5)
    db_session.add(pick)
    db_session.flush()
    pick_id = pick.id

    db_session.delete(user)
    db_session.flush()

    assert db_session.get(Pick, pick_id) is None
