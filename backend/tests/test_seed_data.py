"""Tests for deterministic leaderboard demo data."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    LeagueMember,
    NflGame,
    NflWeek,
    Pick,
    SeasonResult,
    SeedRun,
    User,
    WeeklyResult,
)
from scripts import seed_leaderboard_data as seed_script


class _SessionContext:
    def __init__(self, session: Session):
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None


def test_seed_leaderboard_data_is_idempotent(db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(seed_script, "SessionLocal", lambda: _SessionContext(db_session))
    now = datetime(2026, 8, 25, tzinfo=timezone.utc)

    first = seed_script.seed_leaderboard_data(season=2026, now=now)
    counts_after_first = {
        "users": db_session.scalar(select(func.count()).select_from(User)),
        "members": db_session.scalar(select(func.count()).select_from(LeagueMember)),
        "weeks": db_session.scalar(select(func.count()).select_from(NflWeek)),
        "games": db_session.scalar(select(func.count()).select_from(NflGame)),
        "picks": db_session.scalar(select(func.count()).select_from(Pick)),
        "weekly_results": db_session.scalar(select(func.count()).select_from(WeeklyResult)),
        "season_results": db_session.scalar(select(func.count()).select_from(SeasonResult)),
        "seed_runs": db_session.scalar(select(func.count()).select_from(SeedRun)),
    }

    second = seed_script.seed_leaderboard_data(season=2026, now=now)
    counts_after_second = {
        "users": db_session.scalar(select(func.count()).select_from(User)),
        "members": db_session.scalar(select(func.count()).select_from(LeagueMember)),
        "weeks": db_session.scalar(select(func.count()).select_from(NflWeek)),
        "games": db_session.scalar(select(func.count()).select_from(NflGame)),
        "picks": db_session.scalar(select(func.count()).select_from(Pick)),
        "weekly_results": db_session.scalar(select(func.count()).select_from(WeeklyResult)),
        "season_results": db_session.scalar(select(func.count()).select_from(SeasonResult)),
        "seed_runs": db_session.scalar(select(func.count()).select_from(SeedRun)),
    }

    assert first == second
    assert counts_after_first == counts_after_second
    assert first[1:] == (10, 5, 400)
    assert counts_after_first["seed_runs"] == 1

    fixture_weeks = list(
        db_session.execute(
            select(NflWeek).where(
                NflWeek.season == 2026,
                NflWeek.week_number.between(2, 11),
            )
        ).scalars()
    )
    fixture_games = list(
        db_session.execute(
            select(NflGame).where(NflGame.espn_game_id.like("leaderboard-demo-2026-%"))
        ).scalars()
    )
    fixture_game_ids = [game.id for game in fixture_games]
    fixture_picks = list(
        db_session.execute(select(Pick).where(Pick.game_id.in_(fixture_game_ids))).scalars()
    )

    assert len(fixture_weeks) == 10
    assert len(fixture_games) == 80
    assert len(fixture_picks) == 400
    assert all(game.game_status.value == "final" for game in fixture_games)
    assert all(
        sum(game.week_id == week.id for game in fixture_games) == 8 for week in fixture_weeks
    )
    assert db_session.get(SeedRun, seed_script.FIXTURE_KEY).game_count == 80
