"""Tests for week-level pick locking.

Changed from per-game to week-level locking:
- ALL picks lock when the EARLIEST game (first kickoff) occurs
- Users must submit complete picks before first kickoff
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.league import League
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.user import User
from app.services.picks_service import PickSubmission, create_picks


class TestWeekLevelPickLocking:
    """Tests for week-level pick locking."""

    def test_partial_card_submission_before_first_kickoff(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """User can submit picks for a subset of games before ANY game kicks off."""
        week, games = current_week_with_games

        submissions = [
            PickSubmission(game_id=games[i].id, team=games[i].home_team, confidence=i + 1)
            for i in range(5)
        ]

        picks = create_picks(
            db_session, user=owner_user, week_number=week.week_number, submissions=submissions
        )

        assert len(picks) == 5

    def test_no_picks_after_earliest_game_kickoff(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """NO picks can be submitted after earliest game kicks off."""
        week, games = current_week_with_games

        earliest_game = games[0]
        earliest_game.kickoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
        db_session.commit()

        sunday_submission = PickSubmission(
            game_id=games[5].id, team=games[5].home_team, confidence=1
        )

        with pytest.raises(ValidationError, match="Picks are locked.*earliest game"):
            create_picks(
                db_session,
                user=owner_user,
                week_number=week.week_number,
                submissions=[sunday_submission],
            )

    def test_no_sunday_picks_after_thursday(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Cannot submit Sunday games after Thursday game has kicked off."""
        week, games = current_week_with_games

        thursday_game = games[0]
        thursday_game.kickoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
        db_session.commit()

        submissions = [
            PickSubmission(game_id=games[5].id, team=games[5].home_team, confidence=1),
            PickSubmission(game_id=games[6].id, team=games[6].home_team, confidence=2),
        ]

        with pytest.raises(ValidationError, match="Picks are locked"):
            create_picks(
                db_session, user=owner_user, week_number=week.week_number, submissions=submissions
            )

    def test_cannot_update_after_week_locks(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Cannot update picks after the week locks."""
        week, games = current_week_with_games

        first_submissions = [
            PickSubmission(game_id=games[i].id, team=games[i].home_team, confidence=i + 1)
            for i in range(5)
        ]
        create_picks(
            db_session, user=owner_user, week_number=week.week_number, submissions=first_submissions
        )

        games[0].kickoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        updated_submission = PickSubmission(
            game_id=games[4].id, team=games[4].away_team, confidence=5
        )

        with pytest.raises(ValidationError, match="Picks are locked"):
            create_picks(
                db_session,
                user=owner_user,
                week_number=week.week_number,
                submissions=[updated_submission],
            )

    def test_confidence_uniqueness_within_submission(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Confidence values must be unique within a single submission."""
        week, games = current_week_with_games

        submissions = [
            PickSubmission(game_id=games[0].id, team=games[0].home_team, confidence=1),
            PickSubmission(game_id=games[1].id, team=games[1].home_team, confidence=1),
        ]

        with pytest.raises(ValidationError, match="Confidence values must be unique"):
            create_picks(
                db_session, user=owner_user, week_number=week.week_number, submissions=submissions
            )

    def test_confidence_uniqueness_with_existing_picks(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Confidence values must be unique across existing picks + new submissions."""
        week, games = current_week_with_games

        first_submissions = [
            PickSubmission(game_id=games[i].id, team=games[i].home_team, confidence=i + 1)
            for i in range(5)
        ]
        create_picks(
            db_session, user=owner_user, week_number=week.week_number, submissions=first_submissions
        )

        second_submissions = [
            PickSubmission(game_id=games[5].id, team=games[5].home_team, confidence=1)
        ]

        with pytest.raises(ValidationError, match="Confidence values must be unique"):
            create_picks(
                db_session,
                user=owner_user,
                week_number=week.week_number,
                submissions=second_submissions,
            )

    def test_confidence_range_validation(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Confidence values must be in valid range."""
        week, games = current_week_with_games
        total_games = len(games)

        submissions = [
            PickSubmission(game_id=games[0].id, team=games[0].home_team, confidence=0),
        ]

        with pytest.raises(ValidationError, match="Confidence values must be between"):
            create_picks(
                db_session, user=owner_user, week_number=week.week_number, submissions=submissions
            )

        submissions = [
            PickSubmission(
                game_id=games[0].id, team=games[0].home_team, confidence=total_games + 1
            ),
        ]

        with pytest.raises(ValidationError, match="Confidence values must be between"):
            create_picks(
                db_session, user=owner_user, week_number=week.week_number, submissions=submissions
            )

    def test_game_not_in_week(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Error when trying to pick a game not in the current week."""
        week, games = current_week_with_games

        other_week = NflWeek(
            season=week.season,
            week_number=week.week_number + 1,
            start_date=week.start_date + timedelta(days=7),
            end_date=week.end_date + timedelta(days=7),
        )
        db_session.add(other_week)
        db_session.flush()

        other_game = NflGame(
            week_id=other_week.id,
            espn_game_id="future-game",
            kickoff_time=datetime.now(timezone.utc) + timedelta(days=14),
            home_team="HOU",
            away_team="KC",
        )
        db_session.add(other_game)
        db_session.commit()

        submissions = [
            PickSubmission(game_id=other_game.id, team="HOU", confidence=1),
        ]

        with pytest.raises(ValidationError, match="not in the current week"):
            create_picks(
                db_session, user=owner_user, week_number=week.week_number, submissions=submissions
            )

    def test_week_mismatch(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Error when submitting picks for wrong week."""
        week, games = current_week_with_games

        submissions = [
            PickSubmission(game_id=games[0].id, team=games[0].home_team, confidence=1),
        ]

        with pytest.raises(ValidationError, match="current NFL week"):
            create_picks(
                db_session,
                user=owner_user,
                week_number=week.week_number + 1,
                submissions=submissions,
            )

    def test_duplicate_games_in_submission_fails(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Cannot submit two picks for the same game in one request."""
        week, games = current_week_with_games

        submissions = [
            PickSubmission(game_id=games[0].id, team=games[0].home_team, confidence=1),
            PickSubmission(game_id=games[0].id, team=games[0].away_team, confidence=2),
        ]

        with pytest.raises(ValidationError, match="Each game may only be picked once"):
            create_picks(
                db_session, user=owner_user, week_number=week.week_number, submissions=submissions
            )

    def test_invalid_team_selection_fails(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Cannot pick a team that is not in the game."""
        week, games = current_week_with_games
        game = games[0]

        submissions = [PickSubmission(game_id=game.id, team="XXX", confidence=1)]

        with pytest.raises(ValidationError, match="is not a team in game"):
            create_picks(
                db_session, user=owner_user, week_number=week.week_number, submissions=submissions
            )

    def test_upsert_existing_pick(
        self,
        db_session: Session,
        owner_user: User,
        league_with_owner: League,
        current_week_with_games: tuple,
    ) -> None:
        """Updating an existing pick for an unlocked game succeeds."""
        week, games = current_week_with_games
        game = games[0]

        submissions1 = [PickSubmission(game_id=game.id, team=game.home_team, confidence=1)]
        picks1 = create_picks(
            db_session, user=owner_user, week_number=week.week_number, submissions=submissions1
        )
        pick_id_1 = picks1[0].id

        submissions2 = [PickSubmission(game_id=game.id, team=game.away_team, confidence=2)]
        picks2 = create_picks(
            db_session, user=owner_user, week_number=week.week_number, submissions=submissions2
        )

        assert picks2[0].id == pick_id_1
        assert picks2[0].picked_team == game.away_team
        assert picks2[0].confidence_value == 2
