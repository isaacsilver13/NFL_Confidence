"""Shared pytest fixtures for database-backed tests."""

from collections.abc import Generator
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import Base, get_db
from app.main import app

# Import models so they're registered on Base.metadata before create_all runs.
from app.models import *  # noqa: F401,F403
from app.models.user import User


# Mock email sending globally for all tests to prevent real emails
@pytest.fixture(autouse=True)
def mock_email_service():
    """Auto-use fixture that mocks email sending for all tests."""
    with patch("app.services.email_service.send_email") as mock_send:
        mock_send.return_value = None
        yield mock_send


@pytest.fixture(autouse=True)
def local_auth_settings():
    """Keep auth tests independent of credentials in a developer .env file."""
    from app.api import auth
    from app.auth import oauth

    auth.settings.google_client_id = ""
    auth.settings.google_client_secret = ""
    oauth.settings.google_client_id = ""
    oauth.settings.google_client_secret = ""


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    settings = get_settings()
    schema = f"test_{uuid4().hex}"
    admin_engine = create_engine(settings.database_url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    admin_engine.dispose()

    engine = create_engine(settings.database_url)

    @event.listens_for(engine, "connect")
    def set_test_search_path(dbapi_connection, _connection_record) -> None:
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f'SET search_path TO "{schema}"')

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()
        admin_engine = create_engine(settings.database_url)
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture()
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint" lets service-layer code call session.commit()
    # (e.g. app.services.auth_service) without ending the outer transaction: commits become
    # SAVEPOINT releases, and the whole thing still rolls back when the test finishes.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient whose `get_db` dependency is overridden to use the rollback-wrapped
    `db_session`, so requests made through it participate in the same per-test transaction
    as direct ORM calls and are rolled back automatically.
    """

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def owner_user(db_session: Session) -> User:
    """Fixture providing an owner/commissioner user."""
    user = User(
        google_id="g-owner-123",
        email="owner@example.com",
        display_name="League Owner",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def another_user(db_session: Session) -> User:
    """Fixture providing a second user for testing invitations and multi-user scenarios."""
    user = User(
        google_id="g-another-456",
        email="another@example.com",
        display_name="Another User",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def league_with_owner(db_session: Session, owner_user: User):
    """Fixture providing a league with owner_user as the owner."""
    import secrets

    from app.models.enums import LeagueRole
    from app.models.league import League
    from app.models.league_member import LeagueMember

    league = League(
        name="Test League",
        owner_id=owner_user.id,
        season=2025,
        invite_code=secrets.token_urlsafe(16),
    )
    db_session.add(league)
    db_session.flush()

    # Add owner as member
    member = LeagueMember(
        league_id=league.id,
        user_id=owner_user.id,
        role=LeagueRole.OWNER,
    )
    db_session.add(member)
    db_session.flush()

    return league


@pytest.fixture()
def current_week_with_games(db_session: Session, league_with_owner):
    """Fixture providing current NFL week with 17 games."""
    from datetime import datetime, timedelta, timezone

    from app.models.enums import GameStatus, WeekStatus
    from app.models.nfl_game import NflGame
    from app.models.nfl_week import NflWeek

    # Create current week
    now = datetime.now(timezone.utc)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = NflWeek(
        season=2025,
        week_number=1,
        start_date=week_start,
        end_date=week_start + timedelta(days=7),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()

    # Create 17 games spread throughout the week
    games = []
    for i in range(17):
        # Thursday game at hour 20 (8pm)
        # Sunday games at hours 13, 16 (1pm, 4pm ET)
        # Monday game at hour 20 (8pm)
        if i == 0:  # Thursday
            kickoff = week_start + timedelta(hours=20)
        elif i < 8:  # Sunday afternoon (spread across 3 hours)
            kickoff = week_start + timedelta(
                days=2, hours=13 + (i - 1) // 4, minutes=30 * ((i - 1) % 4)
            )
        elif i < 14:  # Sunday/Monday night
            kickoff = week_start + timedelta(
                days=2, hours=20 + ((i - 8) // 3), minutes=15 * ((i - 8) % 3)
            )
        else:  # Monday night and late games
            kickoff = week_start + timedelta(
                days=3, hours=20 + ((i - 14) // 2), minutes=30 * ((i - 14) % 2)
            )

        game = NflGame(
            espn_game_id=f"game-{i}",
            week_id=week.id,
            kickoff_time=kickoff,
            away_team=f"T{i*2:02d}",
            home_team=f"T{i*2+1:02d}",
            game_status=GameStatus.SCHEDULED,
        )
        db_session.add(game)
        games.append(game)

    db_session.flush()
    return (week, games)
