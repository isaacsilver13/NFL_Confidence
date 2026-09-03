"""SQLAlchemy engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Configure connection pool for production concurrency
# - pool_size: Base number of connections to keep in the pool
# - max_overflow: Allow up to this many additional connections during spikes
# - pool_pre_ping: Verify connection is still valid before reusing
# - pool_recycle: Refresh connections after this many seconds (prevents stale connections)
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
)


@event.listens_for(engine, "connect")
def set_public_search_path(dbapi_connection, _connection_record) -> None:
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO public")


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
