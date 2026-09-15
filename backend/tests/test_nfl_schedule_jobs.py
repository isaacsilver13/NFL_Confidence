"""Tests for the live-scheduler NFL sync job."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.jobs import nfl_schedule
from app.models import NflGame, NflWeek, User
from app.models.enums import GameStatus, WeekStatus
from app.services import league_service


def _user(db: Session) -> User:
    suffix = uuid.uuid4().hex
    user = User(
        google_id=f"nfl-schedule-test-{suffix}",
        email=f"nfl-schedule-test-{suffix}@example.com",
        display_name="NFL Schedule Test User",
    )
    db.add(user)
    db.flush()
    return user


def test_run_current_week_sync_completes_a_week_that_is_no_longer_current(
    db_session: Session, monkeypatch
) -> None:
    """`run_current_week_sync` used to only ever resync `get_current_week`'s
    result, so a week whose games all finished after the calendar rolled
    into the next week never got a chance to complete again. It should now
    re-check every incomplete week instead.
    """
    owner = _user(db_session)
    league = league_service.create_league(
        db_session, owner=owner, name="Schedule Job Test League", season=2026
    )
    now = datetime.now(timezone.utc)

    orphaned_week = NflWeek(
        season=league.season,
        week_number=1,
        start_date=now - timedelta(days=15),
        end_date=now - timedelta(days=8),
        status=WeekStatus.REGULAR,
    )
    db_session.add(orphaned_week)
    db_session.flush()
    db_session.add(
        NflGame(
            week_id=orphaned_week.id,
            espn_game_id=f"nfl-schedule-game-{uuid.uuid4().hex}",
            kickoff_time=orphaned_week.start_date,
            away_team="BUF",
            home_team="KC",
            home_score=24,
            away_score=17,
            winning_team="KC",
            game_status=GameStatus.FINAL,
            is_tie=False,
        )
    )

    current_week = NflWeek(
        season=league.season,
        week_number=2,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(days=6),
        status=WeekStatus.REGULAR,
    )
    db_session.add(current_week)
    db_session.commit()

    monkeypatch.setattr(nfl_schedule, "SessionLocal", lambda: Session(bind=db_session.get_bind()))

    with (
        patch.object(nfl_schedule, "fetch_schedule", return_value=[]),
        patch.object(nfl_schedule, "import_games", return_value=0),
    ):
        nfl_schedule.run_current_week_sync()

    db_session.refresh(orphaned_week)
    assert orphaned_week.status == WeekStatus.COMPLETE
