"""Tests for the real-schedule dev seed (weeks from ESPN + fake users' picks)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.espn import EspnGame
from app.models import NflGame, NflWeek, Pick, User
from app.repositories import nfl_game_repository, nfl_week_repository, pick_repository
from app.services.auth_service import get_or_create_dev_user
from scripts import seed_test_data as seed_script

SEED_NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
SEASON_KICKOFF = datetime(2026, 9, 10, 20, tzinfo=timezone.utc)
TEAMS = (
    "ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC "
    "LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS"
).split()


class _SessionContext:
    def __init__(self, session: Session):
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None


def _fake_fetch_schedule(season: int, week_number: int) -> list[EspnGame]:
    # Week 5 has byes, like the real schedule, so slot counts differ by week.
    game_count = 3 if week_number == 5 else 4
    week_kickoff = SEASON_KICKOFF + timedelta(weeks=week_number - 1)
    games = []
    for index in range(game_count):
        kickoff = week_kickoff + timedelta(hours=index)
        is_final = kickoff < SEED_NOW
        away, home = TEAMS[index * 2], TEAMS[index * 2 + 1]
        games.append(
            EspnGame(
                espn_game_id=f"espn-{season}-{week_number}-{index}",
                season=season,
                week_number=week_number,
                kickoff_time=kickoff,
                away_team=away,
                home_team=home,
                game_status="final" if is_final else "scheduled",
                away_score=17 if is_final else None,
                home_score=24 if is_final else None,
                winning_team=home if is_final else None,
                is_tie=False,
                clock=None,
                period=None,
                venue_name=None,
                venue_location=None,
                spread_team=home,
                spread=-3.5,
            )
        )
    return games


def _seed(db_session: Session, monkeypatch):
    monkeypatch.setattr(seed_script, "SessionLocal", lambda: _SessionContext(db_session))
    monkeypatch.setattr(seed_script, "fetch_schedule", _fake_fetch_schedule)
    return seed_script.seed_test_data(season=2026, now=SEED_NOW)


def _fake_user_ids(db_session: Session) -> list:
    google_ids = [entry["google_id"] for entry in seed_script.FAKE_USERS]
    return list(db_session.scalars(select(User.id).where(User.google_id.in_(google_ids))))


def test_seed_imports_five_real_weeks_with_fake_picks(db_session: Session, monkeypatch) -> None:
    _, game_counts = _seed(db_session, monkeypatch)

    assert game_counts == {1: 4, 2: 4, 3: 4, 4: 4, 5: 3}
    weeks = list(db_session.scalars(select(NflWeek).where(NflWeek.season == 2026)))
    assert sorted(week.week_number for week in weeks) == [1, 2, 3, 4, 5]

    fake_user_ids = _fake_user_ids(db_session)
    assert len(fake_user_ids) == len(seed_script.FAKE_USERS)
    for week in weeks:
        games = nfl_game_repository.get_by_week_id(db_session, week.id)
        for user_id in fake_user_ids:
            picks = pick_repository.list_by_user_and_week(
                db_session, user_id=user_id, week_id=week.id
            )
            # Exactly one pick per game, with every confidence slot used once.
            assert sorted(pick.confidence_value for pick in picks) == list(range(1, len(games) + 1))
            for pick in picks:
                assert pick.picked_team in (pick.game.home_team, pick.game.away_team)
                assert (pick.locked_at is not None) == (pick.game.kickoff_time <= SEED_NOW)


def test_seed_purges_legacy_fixture_games(db_session: Session, monkeypatch) -> None:
    dev_user = get_or_create_dev_user(db_session)
    week = nfl_week_repository.create(
        db_session,
        season=2026,
        week_number=1,
        start_date=SEED_NOW - timedelta(days=1),
        end_date=SEED_NOW + timedelta(days=7),
    )
    legacy_game = nfl_game_repository.create(
        db_session,
        espn_game_id="local-test-2026-1-1",
        week_id=week.id,
        kickoff_time=SEED_NOW + timedelta(days=1),
        home_team="KC",
        away_team="BUF",
    )
    pick_repository.create(
        db_session,
        user_id=dev_user.id,
        game_id=legacy_game.id,
        picked_team="KC",
        confidence_value=17,
    )
    db_session.commit()

    _, game_counts = _seed(db_session, monkeypatch)

    assert game_counts[1] == 4
    assert nfl_game_repository.get_by_espn_game_id(db_session, "local-test-2026-1-1") is None
    db_session.refresh(week)
    # The legacy fixture's far-future end date is replaced by the real games' window.
    assert week.end_date < SEED_NOW


def test_seed_is_idempotent(db_session: Session, monkeypatch) -> None:
    def counts() -> dict[str, int]:
        return {
            "users": db_session.scalar(select(func.count()).select_from(User)),
            "weeks": db_session.scalar(select(func.count()).select_from(NflWeek)),
            "games": db_session.scalar(select(func.count()).select_from(NflGame)),
            "picks": db_session.scalar(select(func.count()).select_from(Pick)),
        }

    first = _seed(db_session, monkeypatch)
    counts_after_first = counts()
    picks_after_first = {
        (pick.user_id, pick.game_id): (pick.picked_team, pick.confidence_value)
        for pick in db_session.scalars(select(Pick))
    }

    second = _seed(db_session, monkeypatch)

    assert first == second
    assert counts() == counts_after_first
    assert {
        (pick.user_id, pick.game_id): (pick.picked_team, pick.confidence_value)
        for pick in db_session.scalars(select(Pick))
    } == picks_after_first
