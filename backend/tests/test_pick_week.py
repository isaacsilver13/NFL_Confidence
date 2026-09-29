"""Tests for the pick-week lookup: which week members should be picking for right now.

The schedule import creates week N+1 (with start_date = the import moment) while week N
is still being played. Both weeks then cover "now", and `get_current_week` returns the
lowest-numbered one, so N+1 would stay hidden until N's window closes after Monday night.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models import NflGame, NflWeek, User
from app.models.enums import WeekStatus
from app.repositories import nfl_game_repository, nfl_week_repository
from app.services import league_service, weeks_service


def _user(db: Session) -> User:
    suffix = uuid.uuid4().hex
    user = User(
        google_id=f"pick-week-{suffix}",
        email=f"pick-week-{suffix}@example.com",
        display_name="Pick Week User",
    )
    db.add(user)
    db.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _week(
    db: Session,
    *,
    season: int,
    week_number: int,
    start: datetime,
    end: datetime,
    kickoffs: list[datetime],
) -> tuple[NflWeek, list[NflGame]]:
    week = nfl_week_repository.create(
        db, season=season, week_number=week_number, start_date=start, end_date=end
    )
    week.status = WeekStatus.REGULAR
    games = [
        nfl_game_repository.create(
            db,
            week_id=week.id,
            espn_game_id=f"pick-week-{uuid.uuid4().hex}",
            kickoff_time=kickoff,
            home_team=home,
            away_team=away,
        )
        for kickoff, (away, home) in zip(kickoffs, [("BUF", "KC"), ("GB", "CHI")] * 3, strict=False)
    ]
    return week, games


def _monday_morning(db: Session, user: User) -> tuple[NflWeek, NflWeek, list[NflGame]]:
    """Week 1 is mid-play (first kickoff long past, Monday night still ahead) and week 2 was
    imported an hour ago with every game in the future."""
    league = league_service.create_league(db, owner=user, name="Pick Week League", season=2026)
    now = datetime.now(timezone.utc)
    week_1, _ = _week(
        db,
        season=league.season,
        week_number=1,
        start=now - timedelta(days=6),
        end=now + timedelta(hours=14),
        kickoffs=[now - timedelta(days=4), now + timedelta(hours=8)],
    )
    week_2, week_2_games = _week(
        db,
        season=league.season,
        week_number=2,
        start=now - timedelta(hours=1),
        end=now + timedelta(days=9),
        kickoffs=[now + timedelta(days=3), now + timedelta(days=4)],
    )
    db.commit()
    return week_1, week_2, week_2_games


def test_current_week_alone_hides_next_week_on_monday(db_session: Session) -> None:
    """Documents why the pick-week lookup exists: the plain lookup returns week N."""
    user = _user(db_session)
    week_1, _, _ = _monday_morning(db_session, user)

    assert weeks_service.get_current_week(db_session).id == week_1.id


def test_pick_week_is_next_week_once_current_week_has_locked(db_session: Session) -> None:
    user = _user(db_session)
    _, week_2, _ = _monday_morning(db_session, user)

    assert weeks_service.get_pick_week(db_session).id == week_2.id


def test_pick_week_is_current_week_while_it_is_still_open(db_session: Session) -> None:
    user = _user(db_session)
    league = league_service.create_league(db_session, owner=user, name="Open League", season=2026)
    now = datetime.now(timezone.utc)
    week_1, _ = _week(
        db_session,
        season=league.season,
        week_number=1,
        start=now - timedelta(days=1),
        end=now + timedelta(days=8),
        kickoffs=[now + timedelta(days=2), now + timedelta(days=5)],
    )
    _week(
        db_session,
        season=league.season,
        week_number=2,
        start=now - timedelta(hours=1),
        end=now + timedelta(days=15),
        kickoffs=[now + timedelta(days=9), now + timedelta(days=12)],
    )
    db_session.commit()

    assert weeks_service.get_pick_week(db_session).id == week_1.id


def test_pick_week_is_current_week_when_next_week_is_not_imported(db_session: Session) -> None:
    user = _user(db_session)
    league = league_service.create_league(db_session, owner=user, name="Solo League", season=2026)
    now = datetime.now(timezone.utc)
    week_1, _ = _week(
        db_session,
        season=league.season,
        week_number=1,
        start=now - timedelta(days=6),
        end=now + timedelta(hours=14),
        kickoffs=[now - timedelta(days=4), now + timedelta(hours=8)],
    )
    db_session.commit()

    assert weeks_service.get_pick_week(db_session).id == week_1.id


def test_picks_card_and_save_use_the_pick_week_on_monday(client, db_session: Session) -> None:
    user = _user(db_session)
    _, week_2, week_2_games = _monday_morning(db_session, user)
    headers = _headers(user)

    card = client.get("/api/v1/picks/card/current", headers=headers)
    assert card.status_code == 200
    assert card.json()["data"]["week"]["weekNumber"] == week_2.week_number
    assert [game["id"] for game in card.json()["data"]["games"]] == [
        str(game.id) for game in week_2_games
    ]

    saved = client.post(
        "/api/v1/picks",
        json={
            "week": week_2.week_number,
            "picks": [
                {"gameId": str(week_2_games[0].id), "team": "KC", "confidence": 1},
                {"gameId": str(week_2_games[1].id), "team": "CHI", "confidence": 2},
            ],
        },
        headers=headers,
    )
    assert saved.status_code == 200

    submitted = client.post(
        "/api/v1/picks/submit", json={"week": week_2.week_number}, headers=headers
    )
    assert submitted.status_code == 200
