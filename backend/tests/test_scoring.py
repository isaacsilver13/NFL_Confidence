"""Tests for idempotent NFL confidence scoring."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import League, LeagueMember, NflGame, NflWeek, Pick, User
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.services import scoring_service


def _user(db: Session, name: str) -> User:
    user = User(
        google_id=f"scoring-test-{uuid.uuid4().hex}",
        email=f"{uuid.uuid4().hex}@example.com",
        display_name=name,
    )
    db.add(user)
    db.flush()
    return user


def test_score_week_recomputes_points_and_is_idempotent(db_session: Session) -> None:
    owner = _user(db_session, "Owner")
    challenger = _user(db_session, "Challenger")
    league = League(
        name="Scoring Test League",
        owner_id=owner.id,
        season=2026,
        invite_code=f"scoring-{uuid.uuid4().hex[:24]}",
        is_active=True,
    )
    db_session.add(league)
    db_session.flush()
    db_session.add_all(
        [
            LeagueMember(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER),
            LeagueMember(league_id=league.id, user_id=challenger.id, role=LeagueRole.MEMBER),
        ]
    )
    week = NflWeek(
        season=2026,
        week_number=1,
        start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 9, 8, tzinfo=timezone.utc),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()
    games = [
        NflGame(
            week_id=week.id,
            espn_game_id=f"scoring-game-{uuid.uuid4().hex}",
            kickoff_time=week.start_date + timedelta(hours=index),
            away_team=away,
            home_team=home,
            home_score=24,
            away_score=17,
            winning_team=home,
            game_status=GameStatus.FINAL,
            is_tie=False,
        )
        for index, (away, home) in enumerate((("BUF", "KC"), ("GB", "CHI")), start=1)
    ]
    db_session.add_all(games)
    db_session.flush()
    db_session.add_all(
        [
            Pick(user_id=owner.id, game_id=games[0].id, picked_team="KC", confidence_value=2),
            Pick(user_id=owner.id, game_id=games[1].id, picked_team="GB", confidence_value=1),
            Pick(
                user_id=challenger.id,
                game_id=games[0].id,
                picked_team="BUF",
                confidence_value=2,
            ),
            Pick(
                user_id=challenger.id,
                game_id=games[1].id,
                picked_team="CHI",
                confidence_value=1,
            ),
        ]
    )
    db_session.flush()

    assert scoring_service.score_week(db_session, league=league, week_id=week.id) == 2
    first_run = {
        result.user_id: (result.total_points, result.correct_picks, result.weekly_rank)
        for result in league.weekly_results
    }
    assert first_run[owner.id] == (2, 1, 1)
    assert first_run[challenger.id] == (1, 1, 2)
    assert week.status == WeekStatus.COMPLETE
    assert len(league.season_results) == 2

    scoring_service.score_week(db_session, league=league, week_id=week.id)

    assert db_session.query(Pick).filter(Pick.points_earned.is_not(None)).count() == 4
    assert (
        db_session.query(league.weekly_results[0].__class__).filter_by(week_id=week.id).count() == 2
    )
    assert db_session.query(league.season_results[0].__class__).filter_by(season=2026).count() == 2
