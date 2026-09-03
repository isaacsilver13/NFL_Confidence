"""Tests for Phase 2B: Concurrency-safe weekly results."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.models.user import User
from app.services.scoring_service import score_week


class TestWeeklyResultsConcurrency:
    """Tests for concurrent weekly result scoring."""

    def test_concurrent_score_week_calls_dont_duplicate_results(
        self, db_session: Session, owner_user: User, another_user: User
    ) -> None:
        """Multiple concurrent score_week calls should not create duplicate weekly results."""
        # Setup league
        import secrets

        league = League(
            name="Concurrency Test League",
            owner_id=owner_user.id,
            season=2025,
            invite_code=secrets.token_urlsafe(16),
        )
        db_session.add(league)
        db_session.flush()

        # Add members
        for user in [owner_user, another_user]:
            member = LeagueMember(
                league_id=league.id,
                user_id=user.id,
                role=LeagueRole.OWNER if user.id == owner_user.id else LeagueRole.MEMBER,
            )
            db_session.add(member)
        db_session.flush()

        # Create week with games
        now = datetime.now(timezone.utc)
        week = NflWeek(
            season=2025,
            week_number=1,
            start_date=now,
            end_date=now + timedelta(days=7),
            status=WeekStatus.REGULAR,
        )
        db_session.add(week)
        db_session.flush()

        # Create games with final scores
        for i in range(3):
            game = NflGame(
                espn_game_id=f"concurrent-game-{i}",
                week_id=week.id,
                kickoff_time=now - timedelta(hours=2),  # Already finished
                away_team="T00",
                home_team="T01",
                game_status=GameStatus.FINAL,
                winning_team="T01" if i % 2 == 0 else "T00",
            )
            db_session.add(game)
        db_session.flush()

        # Create picks for both users
        games = db_session.query(NflGame).filter(NflGame.week_id == week.id).all()
        for idx, game in enumerate(games):
            for user in [owner_user, another_user]:
                pick = Pick(
                    user_id=user.id,
                    game_id=game.id,
                    picked_team=game.winning_team,
                    confidence_value=idx + 1,
                )
                db_session.add(pick)
        db_session.flush()

        # Call score_week multiple times in sequence (simulating concurrent calls)
        # In a real concurrent scenario, these would be in different transactions
        score_week(db_session, league=league, week_id=week.id)
        score_week(db_session, league=league, week_id=week.id)
        score_week(db_session, league=league, week_id=week.id)

        db_session.commit()

        # Verify only one weekly result per user (not duplicated)
        from app.models.weekly_result import WeeklyResult

        results = (
            db_session.query(WeeklyResult)
            .filter(WeeklyResult.league_id == league.id, WeeklyResult.week_id == week.id)
            .all()
        )

        assert len(results) == 2, f"Expected 2 weekly results (one per user), got {len(results)}"

        # Verify both users have a result
        result_user_ids = {r.user_id for r in results}
        assert result_user_ids == {owner_user.id, another_user.id}

    def test_repeated_score_week_produces_consistent_results(
        self, db_session: Session, owner_user: User
    ) -> None:
        """Calling score_week multiple times should produce identical results."""
        import secrets

        league = League(
            name="Consistency Test League",
            owner_id=owner_user.id,
            season=2025,
            invite_code=secrets.token_urlsafe(16),
        )
        db_session.add(league)
        db_session.flush()

        member = LeagueMember(
            league_id=league.id,
            user_id=owner_user.id,
            role=LeagueRole.OWNER,
        )
        db_session.add(member)
        db_session.flush()

        now = datetime.now(timezone.utc)
        week = NflWeek(
            season=2025,
            week_number=1,
            start_date=now,
            end_date=now + timedelta(days=7),
            status=WeekStatus.REGULAR,
        )
        db_session.add(week)
        db_session.flush()

        # Create 5 games with final scores
        for i in range(5):
            game = NflGame(
                espn_game_id=f"consistency-game-{i}",
                week_id=week.id,
                kickoff_time=now - timedelta(hours=2),
                away_team="T00",
                home_team="T01",
                game_status=GameStatus.FINAL,
                winning_team="T01" if i % 2 == 0 else "T00",
            )
            db_session.add(game)
        db_session.flush()

        # Create picks
        games = db_session.query(NflGame).filter(NflGame.week_id == week.id).all()
        for idx, game in enumerate(games):
            pick = Pick(
                user_id=owner_user.id,
                game_id=game.id,
                picked_team=game.winning_team if idx < 3 else "T00",
                confidence_value=idx + 1,
            )
            db_session.add(pick)
        db_session.flush()

        # Score the week three times
        score_week(db_session, league=league, week_id=week.id)
        db_session.commit()

        from app.models.weekly_result import WeeklyResult

        result1 = (
            db_session.query(WeeklyResult)
            .filter(
                WeeklyResult.league_id == league.id,
                WeeklyResult.week_id == week.id,
                WeeklyResult.user_id == owner_user.id,
            )
            .one()
        )
        points1 = result1.total_points
        correct1 = result1.correct_picks

        # Score again (should update, not create duplicate)
        score_week(db_session, league=league, week_id=week.id)
        db_session.commit()

        result2 = (
            db_session.query(WeeklyResult)
            .filter(
                WeeklyResult.league_id == league.id,
                WeeklyResult.week_id == week.id,
                WeeklyResult.user_id == owner_user.id,
            )
            .one()
        )

        assert result2.total_points == points1
        assert result2.correct_picks == correct1

        # Third call should be identical
        score_week(db_session, league=league, week_id=week.id)
        db_session.commit()

        result3 = (
            db_session.query(WeeklyResult)
            .filter(
                WeeklyResult.league_id == league.id,
                WeeklyResult.week_id == week.id,
                WeeklyResult.user_id == owner_user.id,
            )
            .one()
        )

        assert result3.total_points == points1
        assert result3.correct_picks == correct1

    def test_unique_constraint_prevents_duplicate_results(
        self, db_session: Session, owner_user: User
    ) -> None:
        """The database constraint should prevent duplicate weekly results."""
        import secrets

        from sqlalchemy.exc import IntegrityError

        from app.models.weekly_result import WeeklyResult

        league = League(
            name="Constraint Test League",
            owner_id=owner_user.id,
            season=2025,
            invite_code=secrets.token_urlsafe(16),
        )
        db_session.add(league)
        db_session.flush()

        now = datetime.now(timezone.utc)
        week = NflWeek(
            season=2025,
            week_number=1,
            start_date=now,
            end_date=now + timedelta(days=7),
            status=WeekStatus.REGULAR,
        )
        db_session.add(week)
        db_session.flush()

        # Create two weekly results with identical (league_id, week_id, user_id)
        result1 = WeeklyResult(
            league_id=league.id,
            week_id=week.id,
            user_id=owner_user.id,
            total_points=10,
        )
        db_session.add(result1)
        db_session.flush()

        # Try to create duplicate
        result2 = WeeklyResult(
            league_id=league.id,
            week_id=week.id,
            user_id=owner_user.id,
            total_points=20,
        )
        db_session.add(result2)

        # Should raise IntegrityError on commit
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_weekly_result_scores_correctly_with_partial_picks(
        self, db_session: Session, owner_user: User
    ) -> None:
        """Weekly results should reflect only completed games (not partial picks)."""
        import secrets

        league = League(
            name="Partial Picks League",
            owner_id=owner_user.id,
            season=2025,
            invite_code=secrets.token_urlsafe(16),
        )
        db_session.add(league)
        db_session.flush()

        member = LeagueMember(
            league_id=league.id,
            user_id=owner_user.id,
            role=LeagueRole.OWNER,
        )
        db_session.add(member)
        db_session.flush()

        now = datetime.now(timezone.utc)
        week = NflWeek(
            season=2025,
            week_number=1,
            start_date=now,
            end_date=now + timedelta(days=7),
            status=WeekStatus.REGULAR,
        )
        db_session.add(week)
        db_session.flush()

        # Create 3 finished games and 1 pending game
        finished_games = []
        for i in range(3):
            game = NflGame(
                espn_game_id=f"partial-finished-{i}",
                week_id=week.id,
                kickoff_time=now - timedelta(hours=2),
                away_team="T00",
                home_team="T01",
                game_status=GameStatus.FINAL,
                winning_team="T01",
            )
            db_session.add(game)
            finished_games.append(game)
        db_session.flush()

        pending_game = NflGame(
            espn_game_id="partial-pending-1",
            week_id=week.id,
            kickoff_time=now + timedelta(hours=2),
            away_team="T02",
            home_team="T03",
            game_status=GameStatus.SCHEDULED,
        )
        db_session.add(pending_game)
        db_session.flush()

        # Create picks: 2 correct, 1 incorrect, 1 pending
        for i, game in enumerate(finished_games[:2]):
            pick = Pick(
                user_id=owner_user.id,
                game_id=game.id,
                picked_team="T01",  # Correct
                confidence_value=i + 1,
            )
            db_session.add(pick)

        pick_incorrect = Pick(
            user_id=owner_user.id,
            game_id=finished_games[2].id,
            picked_team="T00",  # Incorrect
            confidence_value=3,
        )
        db_session.add(pick_incorrect)

        pick_pending = Pick(
            user_id=owner_user.id,
            game_id=pending_game.id,
            picked_team="T02",
            confidence_value=4,
        )
        db_session.add(pick_pending)
        db_session.flush()

        score_week(db_session, league=league, week_id=week.id)
        db_session.commit()

        from app.models.weekly_result import WeeklyResult

        result = (
            db_session.query(WeeklyResult)
            .filter(
                WeeklyResult.league_id == league.id,
                WeeklyResult.week_id == week.id,
                WeeklyResult.user_id == owner_user.id,
            )
            .one()
        )

        # Should have 2 correct (confidence 1 + 2 = 3 points) and 1 incorrect
        assert result.correct_picks == 2
        assert result.incorrect_picks == 1
        assert result.total_points == 3  # 1 + 2
        assert result.highest_confidence_win == 2  # confidence value of 2nd correct pick
