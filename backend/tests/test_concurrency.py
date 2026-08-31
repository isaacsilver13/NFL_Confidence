"""Regression tests for concurrent writes that share database invariants."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.db.session import Base
from app.models import Invite, League, LeagueMember, NflGame, NflWeek, Pick, User
from app.models.enums import WeekStatus
from app.services import league_service, picks_service
from app.services.picks_service import PickSubmission


def _get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    assert user is not None
    return user


def _make_users(db: Session, *, prefix: str, count: int) -> list[User]:
    users = [
        User(
            google_id=f"{prefix}-google-{uuid4().hex}",
            email=f"{prefix}-{uuid4().hex}@example.com",
            display_name=f"{prefix} user {index}",
        )
        for index in range(count)
    ]
    db.add_all(users)
    db.flush()
    return users


@pytest.fixture(autouse=True)
def clean_database(db_engine):
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with db_engine.begin() as db_connection:
        db_connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    yield
    with db_engine.begin() as db_connection:
        db_connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))


def _run_concurrently(db_engine, worker, count: int = 2) -> list[object]:
    barrier = Barrier(count)

    def run(worker_index: int) -> object:
        with Session(bind=db_engine) as db:
            barrier.wait(timeout=10)
            try:
                return worker(db, worker_index)
            except Exception as exc:  # Return errors so both transactions can finish.
                return exc

    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(run, worker_index) for worker_index in range(count)]
        return [future.result(timeout=20) for future in futures]


def _make_current_week(db: Session, *, owner: User) -> tuple[NflWeek, list[NflGame]]:
    league = league_service.create_league(
        db, owner=owner, name=f"Concurrency {uuid4().hex[:8]}", season=2099
    )
    now = datetime.now(timezone.utc)
    week = NflWeek(
        season=league.season,
        week_number=1,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=7),
        status=WeekStatus.REGULAR,
    )
    db.add(week)
    db.flush()
    games = [
        NflGame(
            week_id=week.id,
            espn_game_id=f"concurrency-{uuid4().hex}",
            kickoff_time=now + timedelta(days=index),
            home_team=home_team,
            away_team=away_team,
        )
        for index, (away_team, home_team) in enumerate((("BUF", "KC"), ("GB", "CHI")), start=1)
    ]
    db.add_all(games)
    db.commit()
    return week, games


def test_same_user_concurrent_pick_batches_are_atomic(db_engine) -> None:
    with Session(bind=db_engine) as setup_db:
        user = _make_users(setup_db, prefix="pick", count=1)[0]
        week, games = _make_current_week(setup_db, owner=user)
        week_number = week.week_number
        user_id = user.id
        game_ids = [(game.id, game.home_team, game.away_team) for game in games]

    first_batch = [
        PickSubmission(game_id=game_id, team=home_team, confidence=index)
        for index, (game_id, home_team, _) in enumerate(game_ids, start=1)
    ]
    second_batch = [
        PickSubmission(game_id=game_id, team=away_team, confidence=3 - index)
        for index, (game_id, _, away_team) in enumerate(game_ids, start=1)
    ]

    results = _run_concurrently(
        db_engine,
        lambda db, worker_index: picks_service.create_picks(
            db,
            user=_get_user(db, user_id),
            week_number=week_number,
            submissions=[first_batch, second_batch][worker_index],
        ),
    )

    assert all(isinstance(result, list) for result in results)
    with Session(bind=db_engine) as verify_db:
        saved = list(
            verify_db.scalars(select(Pick).where(Pick.user_id == user_id).order_by(Pick.game_id))
        )
    assert len(saved) == len(games)
    assert {pick.picked_team for pick in saved} in ({"KC", "CHI"}, {"BUF", "GB"})


def test_different_users_can_submit_picks_concurrently(db_engine) -> None:
    with Session(bind=db_engine) as setup_db:
        users = _make_users(setup_db, prefix="parallel", count=2)
        week, games = _make_current_week(setup_db, owner=users[0])
        week_number = week.week_number
        user_ids = [user.id for user in users]
        submissions = [
            PickSubmission(game_id=game.id, team=game.home_team, confidence=index)
            for index, game in enumerate(games, start=1)
        ]

    def submit(db: Session, user_id: UUID) -> list[Pick]:
        return picks_service.create_picks(
            db,
            user=_get_user(db, user_id),
            week_number=week_number,
            submissions=submissions,
        )

    results = _run_concurrently(
        db_engine,
        lambda db, worker_index: submit(db, user_ids[worker_index]),
    )
    assert all(isinstance(result, list) for result in results)

    with Session(bind=db_engine) as verify_db:
        picks = list(verify_db.scalars(select(Pick)))
    assert len(picks) == len(user_ids) * len(games)


def test_concurrent_league_creation_returns_one_conflict(db_engine) -> None:
    with Session(bind=db_engine) as setup_db:
        users = _make_users(setup_db, prefix="league", count=2)
        user_ids = [user.id for user in users]
        setup_db.commit()

    def create(db: Session, user_id: UUID) -> object:
        return league_service.create_league(
            db,
            owner=_get_user(db, user_id),
            name=f"Race {user_id}",
            season=2099,
        )

    results = _run_concurrently(
        db_engine,
        lambda db, worker_index: create(db, user_ids[worker_index]),
    )
    assert sum(isinstance(result, League) for result in results) == 1
    assert sum(isinstance(result, ConflictError) for result in results) == 1

    with Session(bind=db_engine) as verify_db:
        assert verify_db.scalar(select(League.id).where(League.is_active.is_(True))) is not None
        assert (
            verify_db.scalar(select(League.id).where(League.is_active.is_(True)).offset(1)) is None
        )


def test_concurrent_invite_acceptance_returns_one_conflict(db_engine) -> None:
    with Session(bind=db_engine) as setup_db:
        owner, joiner_one, joiner_two = _make_users(setup_db, prefix="invite", count=3)
        league = league_service.create_league(
            setup_db, owner=owner, name="Invite Race", season=2099
        )
        invite = league_service.create_invite(
            setup_db, league=league, inviter=owner, email=joiner_one.email
        )
        user_ids = [joiner_one.id, joiner_two.id]
        token = invite.token

    def join(db: Session, user_id: UUID) -> object:
        return league_service.join_league(db, user=_get_user(db, user_id), token=token)

    results = _run_concurrently(
        db_engine,
        lambda db, worker_index: join(db, user_ids[worker_index]),
    )

    assert sum(isinstance(result, LeagueMember) for result in results) == 1
    assert sum(isinstance(result, ConflictError) for result in results) == 1
    with Session(bind=db_engine) as verify_db:
        assert (
            verify_db.scalar(select(LeagueMember.id).where(LeagueMember.league_id == league.id))
            is not None
        )
        assert (
            verify_db.scalar(select(Invite.accepted_at).where(Invite.id == invite.id)) is not None
        )
