"""Tests for leaderboard aggregation and member trends."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import (
    League,
    LeagueMember,
    NflGame,
    NflWeek,
    Pick,
    SeasonResult,
    User,
    WeeklyResult,
    WeekSubmission,
)
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.services import leaderboard_service


def _user(db: Session, name: str) -> User:
    user = User(
        google_id=f"leaderboard-test-{uuid.uuid4().hex}",
        email=f"{uuid.uuid4().hex}@example.com",
        display_name=name,
    )
    db.add(user)
    db.flush()
    return user


def _league(db: Session, owner: User) -> League:
    league = League(
        name="Leaderboard Test League",
        owner_id=owner.id,
        season=2000 + int(uuid.uuid4().hex[:4], 16) % 100,
        invite_code=f"test-{uuid.uuid4().hex[:26]}",
        is_active=True,
    )
    db.add(league)
    db.flush()
    return league


def _week_and_games(db: Session, league: League, week_number: int) -> tuple[NflWeek, list[NflGame]]:
    start = datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(days=week_number * 7)
    week = NflWeek(
        season=league.season,
        week_number=week_number,
        start_date=start,
        end_date=start + timedelta(days=6),
        status=WeekStatus.COMPLETE,
    )
    db.add(week)
    db.flush()
    games = [
        NflGame(
            week_id=week.id,
            espn_game_id=f"leaderboard-test-{uuid.uuid4().hex}-{index}",
            kickoff_time=start + timedelta(hours=index),
            away_team=away,
            home_team=home,
            away_score=14,
            home_score=21,
            winning_team=home,
            game_status=GameStatus.FINAL,
            is_tie=False,
        )
        for index, (away, home) in enumerate((("BUF", "KC"), ("GB", "CHI")), start=1)
    ]
    db.add_all(games)
    db.flush()
    return week, games


def _submit(db: Session, *, user: User, week: NflWeek) -> None:
    """The weekly leaderboard only counts members with a WeekSubmission row."""
    db.add(WeekSubmission(user_id=user.id, week_id=week.id))
    db.flush()


def _members(db: Session, league: League) -> tuple[User, User]:
    owner = db.get(User, league.owner_id)
    assert owner is not None
    challenger = _user(db, "Challenger")
    db.add_all(
        [
            LeagueMember(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER),
            LeagueMember(league_id=league.id, user_id=challenger.id, role=LeagueRole.MEMBER),
        ]
    )
    db.flush()
    return owner, challenger


def test_weekly_leaderboard_returns_ranked_members(db_session: Session) -> None:
    owner = _user(db_session, "Owner")
    league = _league(db_session, owner)
    owner, challenger = _members(db_session, league)
    week, _ = _week_and_games(db_session, league, 2)
    _submit(db_session, user=owner, week=week)
    _submit(db_session, user=challenger, week=week)
    db_session.add_all(
        [
            WeeklyResult(
                league_id=league.id,
                week_id=week.id,
                user_id=owner.id,
                total_points=17,
                correct_picks=2,
                incorrect_picks=0,
                weekly_rank=1,
            ),
            WeeklyResult(
                league_id=league.id,
                week_id=week.id,
                user_id=challenger.id,
                total_points=8,
                correct_picks=1,
                incorrect_picks=1,
                weekly_rank=2,
            ),
        ]
    )

    result = leaderboard_service.get_weekly_leaderboard(db_session, league=league, week_number=2)

    assert [member.member_name for member in result.standings] == ["Owner", "Challenger"]
    assert [member.total_points for member in result.standings] == [17, 8]


def test_weekly_leaderboard_includes_last_two_games_picks(db_session: Session) -> None:
    owner = _user(db_session, "Owner")
    league = _league(db_session, owner)
    owner, challenger = _members(db_session, league)
    week, games = _week_and_games(db_session, league, 2)
    _submit(db_session, user=owner, week=week)
    _submit(db_session, user=challenger, week=week)
    db_session.add_all(
        [
            WeeklyResult(
                league_id=league.id,
                week_id=week.id,
                user_id=owner.id,
                total_points=17,
                correct_picks=2,
                incorrect_picks=0,
                weekly_rank=1,
            ),
            WeeklyResult(
                league_id=league.id,
                week_id=week.id,
                user_id=challenger.id,
                total_points=8,
                correct_picks=1,
                incorrect_picks=1,
                weekly_rank=2,
            ),
            Pick(
                user_id=owner.id,
                game_id=games[1].id,
                picked_team="CHI",
                confidence_value=2,
            ),
        ]
    )

    result = leaderboard_service.get_weekly_leaderboard(db_session, league=league, week_number=2)

    assert [(g.away_team, g.home_team) for g in result.last_two_games] == [
        ("BUF", "KC"),
        ("GB", "CHI"),
    ]
    owner_row = next(m for m in result.standings if m.member_name == "Owner")
    challenger_row = next(m for m in result.standings if m.member_name == "Challenger")
    assert [p.team for p in owner_row.last_two_game_picks] == [None, "CHI"]
    assert [p.confidence for p in owner_row.last_two_game_picks] == [None, 2]
    assert [p.team for p in challenger_row.last_two_game_picks] == [None, None]


def test_weekly_leaderboard_excludes_members_without_a_submission(db_session: Session) -> None:
    owner = _user(db_session, "Owner")
    league = _league(db_session, owner)
    owner, challenger = _members(db_session, league)
    week, _ = _week_and_games(db_session, league, 2)
    _submit(db_session, user=owner, week=week)
    db_session.add_all(
        [
            WeeklyResult(
                league_id=league.id,
                week_id=week.id,
                user_id=owner.id,
                total_points=17,
                correct_picks=2,
                incorrect_picks=0,
                weekly_rank=1,
            ),
            WeeklyResult(
                league_id=league.id,
                week_id=week.id,
                user_id=challenger.id,
                total_points=8,
                correct_picks=1,
                incorrect_picks=1,
                weekly_rank=2,
            ),
        ]
    )

    result = leaderboard_service.get_weekly_leaderboard(db_session, league=league, week_number=2)

    assert [member.member_name for member in result.standings] == ["Owner"]


def test_weekly_leaderboard_reports_points_remaining_on_unfinished_games(
    db_session: Session,
) -> None:
    owner = _user(db_session, "Owner")
    league = _league(db_session, owner)
    owner, challenger = _members(db_session, league)
    week = NflWeek(
        season=league.season,
        week_number=5,
        start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 10, 8, tzinfo=timezone.utc),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()
    decided_game = NflGame(
        week_id=week.id,
        espn_game_id=f"leaderboard-test-{uuid.uuid4().hex}",
        kickoff_time=week.start_date,
        away_team="BUF",
        home_team="KC",
        away_score=14,
        home_score=21,
        winning_team="KC",
        game_status=GameStatus.FINAL,
        is_tie=False,
    )
    live_game = NflGame(
        week_id=week.id,
        espn_game_id=f"leaderboard-test-{uuid.uuid4().hex}",
        kickoff_time=week.start_date + timedelta(hours=1),
        away_team="GB",
        home_team="CHI",
        game_status=GameStatus.LIVE,
    )
    voided_game = NflGame(
        week_id=week.id,
        espn_game_id=f"leaderboard-test-{uuid.uuid4().hex}",
        kickoff_time=week.start_date + timedelta(hours=2),
        away_team="DAL",
        home_team="NYG",
        game_status=GameStatus.SCHEDULED,
    )
    db_session.add_all([decided_game, live_game, voided_game])
    db_session.flush()
    _submit(db_session, user=owner, week=week)
    db_session.add_all(
        [
            WeeklyResult(
                league_id=league.id,
                week_id=week.id,
                user_id=owner.id,
                total_points=10,
                correct_picks=1,
                incorrect_picks=0,
                weekly_rank=1,
            ),
            Pick(
                user_id=owner.id,
                game_id=decided_game.id,
                picked_team="KC",
                confidence_value=10,
                locked_at=decided_game.kickoff_time,
                points_earned=10,
            ),
            Pick(
                user_id=owner.id,
                game_id=live_game.id,
                picked_team="GB",
                confidence_value=5,
                locked_at=live_game.kickoff_time,
            ),
            Pick(
                user_id=owner.id,
                game_id=voided_game.id,
                picked_team="DAL",
                confidence_value=7,
                locked_at=voided_game.kickoff_time,
                voided_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                voided_by_user_id=owner.id,
            ),
        ]
    )
    db_session.flush()

    result = leaderboard_service.get_weekly_leaderboard(db_session, league=league, week_number=5)

    owner_row = next(member for member in result.standings if member.member_name == "Owner")
    assert owner_row.points_remaining == 5


def test_season_standings_returns_aggregate_rows(db_session: Session) -> None:
    owner = _user(db_session, "Owner")
    league = _league(db_session, owner)
    owner, challenger = _members(db_session, league)
    db_session.add_all(
        [
            SeasonResult(
                league_id=league.id,
                user_id=owner.id,
                season=league.season,
                total_points=42,
                weekly_wins=2,
                first_place_finishes=2,
                second_place_finishes=0,
                third_place_finishes=0,
                current_rank=1,
            ),
            SeasonResult(
                league_id=league.id,
                user_id=challenger.id,
                season=league.season,
                total_points=31,
                weekly_wins=0,
                first_place_finishes=0,
                second_place_finishes=1,
                third_place_finishes=1,
                current_rank=2,
            ),
        ]
    )

    result = leaderboard_service.get_season_standings(db_session, league=league)

    assert result.season == league.season
    assert result.standings[0].weekly_wins == 2
    assert result.standings[1].third_place_finishes == 1


def _breakdown_fixture(db: Session) -> tuple[League, User, User, User]:
    owner = _user(db, "Owner")
    league = _league(db, owner)
    challenger = _user(db, "Challenger")
    outsider = _user(db, "Outsider")
    db.add_all(
        [
            LeagueMember(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER),
            LeagueMember(league_id=league.id, user_id=challenger.id, role=LeagueRole.MEMBER),
        ]
    )
    week, games = _week_and_games(db, league, 2)
    db.add_all(
        [
            Pick(
                user_id=owner.id,
                game_id=games[0].id,
                picked_team="KC",
                confidence_value=1,
                locked_at=games[0].kickoff_time,
                points_earned=12,
            ),
            Pick(
                user_id=owner.id,
                game_id=games[1].id,
                picked_team="GB",
                confidence_value=1,
                locked_at=games[1].kickoff_time,
                points_earned=0,
            ),
            Pick(
                user_id=challenger.id,
                game_id=games[0].id,
                picked_team="KC",
                confidence_value=2,
                locked_at=games[0].kickoff_time,
                points_earned=12,
            ),
            Pick(
                user_id=outsider.id,
                game_id=games[0].id,
                picked_team="KC",
                confidence_value=2,
                locked_at=games[0].kickoff_time,
                points_earned=12,
            ),
        ]
    )
    db.flush()
    return league, owner, challenger, outsider


def test_pick_breakdown_counts_distinct_members_and_excludes_outsiders(
    db_session: Session,
) -> None:
    league, owner, challenger, outsider = _breakdown_fixture(db_session)

    result = leaderboard_service.get_pick_breakdown(db_session, league=league, viewer_id=owner.id)

    assert len(result.weeks) == 1
    assert result.weeks[0].week_number == 2
    assert len(result.weeks[0].games) == 2
    first_game = result.weeks[0].games[0]
    assert (first_game.away_team, first_game.home_team) == ("BUF", "KC")
    assert first_game.median_confidence == 1.5
    assert [(count.team, count.user_count) for count in first_game.team_counts] == [
        ("BUF", 0),
        ("KC", 2),
    ]
    second_game = result.weeks[0].games[1]
    assert second_game.median_confidence == 1.0
    assert [(count.team, count.user_count) for count in second_game.team_counts] == [
        ("GB", 1),
        ("CHI", 0),
    ]
    assert outsider.id not in {owner.id, challenger.id}


def test_get_game_picks_returns_league_members_only_for_completed_weeks(
    db_session: Session,
) -> None:
    league, owner, challenger, outsider = _breakdown_fixture(db_session)
    game = (
        db_session.query(NflGame)
        .join(NflWeek, NflGame.week_id == NflWeek.id)
        .filter(NflWeek.season == league.season, NflWeek.week_number == 2)
        .order_by(NflGame.kickoff_time)
        .first()
    )
    assert game is not None

    result = leaderboard_service.get_game_picks(
        db_session, league=league, viewer_id=owner.id, game_id=game.id
    )

    assert result.away_team == "BUF"
    assert result.home_team == "KC"
    member_names = {p.member_name for p in result.picks}
    assert member_names == {"Owner", "Challenger"}
    assert outsider.display_name not in member_names
    owner_pick = next(p for p in result.picks if p.member_name == "Owner")
    assert owner_pick.team == "KC"
    assert owner_pick.confidence == 1
    assert owner_pick.is_correct is True


def test_get_game_picks_not_found_for_incomplete_week(db_session: Session) -> None:
    owner = _user(db_session, "Owner")
    league = _league(db_session, owner)
    db_session.add(LeagueMember(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER))
    week = NflWeek(
        season=league.season,
        week_number=9,
        start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 11, 8, tzinfo=timezone.utc),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()
    game = NflGame(
        week_id=week.id,
        espn_game_id=f"leaderboard-test-{uuid.uuid4().hex}",
        kickoff_time=week.start_date,
        away_team="BUF",
        home_team="KC",
        game_status=GameStatus.SCHEDULED,
    )
    db_session.add(game)
    db_session.flush()

    with pytest.raises(NotFoundError):
        leaderboard_service.get_game_picks(
            db_session, league=league, viewer_id=owner.id, game_id=game.id
        )


def test_pick_breakdown_includes_completed_weeks_without_picks(db_session: Session) -> None:
    league, owner, _, _ = _breakdown_fixture(db_session)
    empty_week = NflWeek(
        season=league.season,
        week_number=3,
        start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 9, 7, tzinfo=timezone.utc),
        status=WeekStatus.COMPLETE,
    )
    db_session.add(empty_week)
    db_session.flush()

    result = leaderboard_service.get_pick_breakdown(db_session, league=league, viewer_id=owner.id)

    assert [week.week_number for week in result.weeks] == [2, 3]
    assert result.weeks[1].games == []


def test_pick_breakdown_requires_active_league_membership(db_session: Session) -> None:
    league, _, _, outsider = _breakdown_fixture(db_session)

    with pytest.raises(NotFoundError, match="You are not a member of the active league"):
        leaderboard_service.get_pick_breakdown(db_session, league=league, viewer_id=outsider.id)
