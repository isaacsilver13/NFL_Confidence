"""Shared pytest fixtures for database-backed tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import Base, get_db
from app.main import app

# Import models so they're registered on Base.metadata before create_all runs.
from app.models import *  # noqa: F401,F403


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


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
