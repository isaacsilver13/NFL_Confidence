"""Seed deterministic historical data for local leaderboard and trends verification."""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.models.league import League
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.models.season_result import SeasonResult
from app.models.seed_run import SeedRun
from app.models.user import User
from app.models.weekly_result import WeeklyResult
from app.repositories import league_member_repository, league_repository, user_repository
from app.services.auth_service import get_or_create_dev_user

DEMO_LEAGUE_NAME = "Local NFL Confidence Demo League"
DEMO_USER_SPECS = (
    ("leaderboard-demo-ava", "ava@leaderboard.local", "Ava Chen"),
    ("leaderboard-demo-ben", "ben@leaderboard.local", "Ben Morgan"),
    ("leaderboard-demo-carmen", "carmen@leaderboard.local", "Carmen Ruiz"),
    ("leaderboard-demo-drew", "drew@leaderboard.local", "Drew Patel"),
)
DEMO_GAMES = (
    ("BUF", "KC"),
    ("GB", "CHI"),
    ("DAL", "PHI"),
    ("SF", "SEA"),
    ("BAL", "CIN"),
    ("MIA", "NYJ"),
    ("DET", "MIN"),
    ("PIT", "CLE"),
)
# Week 1 remains available for the separate current-week test fixture.
DEFAULT_WEEKS = tuple(range(2, 12))
FIXTURE_KEY = "nfl-confidence-historical-v1"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _get_or_create_user(db: Session, *, google_id: str, email: str, display_name: str) -> User:
    user = user_repository.get_by_google_id(db, google_id)
    if user is None:
        user = user_repository.create(
            db,
            google_id=google_id,
            email=email,
            display_name=display_name,
            avatar_url=None,
        )
    else:
        user.email = email
        user.display_name = display_name
    return user


def _get_or_create_week(
    db: Session,
    *,
    season: int,
    week_number: int,
    start_date: datetime,
    end_date: datetime,
) -> NflWeek:
    week = db.execute(
        select(NflWeek).where(
            NflWeek.season == season,
            NflWeek.week_number == week_number,
        )
    ).scalar_one_or_none()
    if week is None:
        week = NflWeek(
            season=season,
            week_number=week_number,
            start_date=start_date,
            end_date=end_date,
            status=WeekStatus.COMPLETE,
        )
        db.add(week)
        db.flush()
    else:
        week.start_date = start_date
        week.end_date = end_date
        week.status = WeekStatus.COMPLETE
    return week


def _get_or_create_game(
    db: Session,
    *,
    season: int,
    week_number: int,
    game_number: int,
    week_id,
    kickoff_time: datetime,
    away_team: str,
    home_team: str,
) -> NflGame:
    game_id = f"leaderboard-demo-{season}-{week_number}-{game_number}"
    game = db.execute(select(NflGame).where(NflGame.espn_game_id == game_id)).scalar_one_or_none()
    is_tie = week_number == 4 and game_number == 17
    home_score = 24 + ((week_number + game_number) % 13)
    away_score = 17 + ((week_number * 2 + game_number) % 10)
    if is_tie:
        home_score = away_score = 24
    winning_team = None if is_tie else (home_team if home_score > away_score else away_team)
    values = {
        "week_id": week_id,
        "kickoff_time": kickoff_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "winning_team": winning_team,
        "game_status": GameStatus.FINAL,
        "is_tie": is_tie,
        "last_synced": kickoff_time,
    }
    if game is None:
        game = NflGame(espn_game_id=game_id, **values)
        db.add(game)
        db.flush()
    else:
        for key, value in values.items():
            setattr(game, key, value)
    return game


def _get_or_create_pick(
    db: Session,
    *,
    user_id,
    game: NflGame,
    picked_team: str,
    confidence_value: int,
) -> Pick:
    pick = db.execute(
        select(Pick).where(Pick.user_id == user_id, Pick.game_id == game.id)
    ).scalar_one_or_none()
    is_correct = game.winning_team is not None and picked_team == game.winning_team
    values = {
        "picked_team": picked_team,
        "confidence_value": confidence_value,
        "locked_at": game.kickoff_time,
        "points_earned": confidence_value if is_correct else 0,
    }
    if pick is None:
        pick = Pick(user_id=user_id, game_id=game.id, **values)
        db.add(pick)
    else:
        for key, value in values.items():
            setattr(pick, key, value)
    return pick


def _validate_target_weeks(db: Session, *, season: int, weeks: tuple[int, ...]) -> None:
    """Reject unrelated games so a partial or conflicting fixture is never overwritten."""
    existing_weeks = db.execute(
        select(NflWeek).where(
            NflWeek.season == season,
            NflWeek.week_number.in_(weeks),
        )
    ).scalars()
    for week in existing_weeks:
        existing_games = db.execute(select(NflGame).where(NflGame.week_id == week.id)).scalars()
        expected_ids = {
            f"leaderboard-demo-{season}-{week.week_number}-{game_number}"
            for game_number in range(1, len(DEMO_GAMES) + 1)
        }
        conflicting_ids = sorted(
            game.espn_game_id for game in existing_games if game.espn_game_id not in expected_ids
        )
        if conflicting_ids:
            raise ValueError(
                f"Season {season} week {week.week_number} already contains unrelated games "
                f"({', '.join(conflicting_ids)}); refusing to overwrite them."
            )


def _upsert_weekly_result(
    db: Session,
    *,
    league_id,
    week_id,
    user_id,
    total_points: int,
    correct_picks: int,
    incorrect_picks: int,
    weekly_rank: int,
) -> WeeklyResult:
    results = list(
        db.execute(
            select(WeeklyResult).where(
                WeeklyResult.league_id == league_id,
                WeeklyResult.week_id == week_id,
                WeeklyResult.user_id == user_id,
            )
        ).scalars()
    )
    result = (
        results[0]
        if results
        else WeeklyResult(
            league_id=league_id,
            week_id=week_id,
            user_id=user_id,
        )
    )
    result.total_points = total_points
    result.correct_picks = correct_picks
    result.incorrect_picks = incorrect_picks
    result.weekly_rank = weekly_rank
    if not results:
        db.add(result)
    for duplicate in results[1:]:
        db.delete(duplicate)
    return result


def _upsert_season_result(
    db: Session,
    *,
    league_id,
    user_id,
    season: int,
    total_points: int,
    weekly_wins: int,
    first_place_finishes: int,
    second_place_finishes: int,
    third_place_finishes: int,
    current_rank: int,
) -> SeasonResult:
    result = db.execute(
        select(SeasonResult).where(
            SeasonResult.league_id == league_id,
            SeasonResult.user_id == user_id,
            SeasonResult.season == season,
        )
    ).scalar_one_or_none()
    if result is None:
        result = SeasonResult(league_id=league_id, user_id=user_id, season=season)
        db.add(result)
    result.total_points = total_points
    result.weekly_wins = weekly_wins
    result.first_place_finishes = first_place_finishes
    result.second_place_finishes = second_place_finishes
    result.third_place_finishes = third_place_finishes
    result.current_rank = current_rank
    return result


def seed_leaderboard_data(
    *,
    season: int | None = None,
    weeks: tuple[int, ...] = DEFAULT_WEEKS,
    now: datetime | None = None,
) -> tuple[str, int, int, int]:
    """Create the deterministic historical fixture once for local leaderboard views."""
    seed_now = _utc(now or datetime.now(timezone.utc))
    selected_weeks = tuple(dict.fromkeys(weeks))
    if not selected_weeks or any(week < 1 or week > 18 for week in selected_weeks):
        raise ValueError("weeks must contain NFL week numbers from 1 through 18")

    with SessionLocal() as db:
        completed_run = db.get(SeedRun, FIXTURE_KEY)
        if completed_run is not None:
            return (
                str(completed_run.league_id),
                completed_run.week_count,
                5,
                completed_run.pick_count,
            )

        active_league = league_repository.get_active(db)
        if active_league is not None and season is not None and active_league.season != season:
            raise ValueError(
                f"Active league uses season {active_league.season}; "
                f"cannot seed season {season}."
            )
        target_season = (
            active_league.season if active_league is not None else season or seed_now.year
        )
        _validate_target_weeks(db, season=target_season, weeks=selected_weeks)

        dev_user = get_or_create_dev_user(db)
        league = active_league
        if league is None:
            league = League(
                name=DEMO_LEAGUE_NAME,
                owner_id=dev_user.id,
                season=season or seed_now.year,
                invite_code="local-leaderboard-demo",
                is_active=True,
            )
            db.add(league)
            db.flush()
            league_member_repository.create(
                db,
                league_id=league.id,
                user_id=dev_user.id,
                role=LeagueRole.OWNER,
            )
        elif league_member_repository.get_by_league_and_user(db, league.id, dev_user.id) is None:
            league_member_repository.create(
                db,
                league_id=league.id,
                user_id=dev_user.id,
                role=LeagueRole.MEMBER,
            )

        target_season = league.season
        users = [dev_user]
        for google_id, email, display_name in DEMO_USER_SPECS:
            user = _get_or_create_user(
                db,
                google_id=google_id,
                email=email,
                display_name=display_name,
            )
            users.append(user)
            if league_member_repository.get_by_league_and_user(db, league.id, user.id) is None:
                league_member_repository.create(
                    db,
                    league_id=league.id,
                    user_id=user.id,
                    role=LeagueRole.MEMBER,
                )

        weekly_scores: dict[int, dict] = {}
        pick_count = 0
        ordered_weeks = sorted(selected_weeks)
        for week_index, week_number in enumerate(ordered_weeks):
            start_date = seed_now - timedelta(days=(len(ordered_weeks) - week_index) * 7)
            week = _get_or_create_week(
                db,
                season=target_season,
                week_number=week_number,
                start_date=start_date,
                end_date=start_date + timedelta(days=6, hours=23),
            )
            games = []
            for game_number, (away_team, home_team) in enumerate(DEMO_GAMES, start=1):
                game = _get_or_create_game(
                    db,
                    season=target_season,
                    week_number=week_number,
                    game_number=game_number,
                    week_id=week.id,
                    kickoff_time=start_date + timedelta(hours=12 + game_number * 2),
                    away_team=away_team,
                    home_team=home_team,
                )
                games.append(game)

            weekly_scores[week_number] = {}
            for member_index, user in enumerate(users):
                total_points = 0
                correct_picks = 0
                for game_index, game in enumerate(games):
                    confidence = ((game_index + member_index * 3 + week_index * 5) % len(games)) + 1
                    is_correct = (
                        game.winning_team is not None
                        and (game_index + member_index + week_index) % 4 != 0
                    )
                    if is_correct:
                        assert game.winning_team is not None
                        picked_team = game.winning_team
                    elif game.winning_team == game.home_team:
                        picked_team = game.away_team
                    else:
                        picked_team = game.home_team
                    pick = _get_or_create_pick(
                        db,
                        user_id=user.id,
                        game=game,
                        picked_team=picked_team,
                        confidence_value=confidence,
                    )
                    total_points += pick.points_earned or 0
                    correct_picks += int((pick.points_earned or 0) > 0)
                    pick_count += 1
                weekly_scores[week_number][user.id] = (total_points, correct_picks)

            ranked_users = sorted(
                users,
                key=lambda user: (
                    -weekly_scores[week_number][user.id][0],
                    -weekly_scores[week_number][user.id][1],
                    user.display_name,
                ),
            )
            for rank, user in enumerate(ranked_users, start=1):
                total_points, correct_picks = weekly_scores[week_number][user.id]
                _upsert_weekly_result(
                    db,
                    league_id=league.id,
                    week_id=week.id,
                    user_id=user.id,
                    total_points=total_points,
                    correct_picks=correct_picks,
                    incorrect_picks=len(games) - correct_picks,
                    weekly_rank=rank,
                )

        season_totals = {
            user.id: {
                "total_points": sum(weekly_scores[week][user.id][0] for week in ordered_weeks),
                "weekly_wins": 0,
                "first_place_finishes": 0,
                "second_place_finishes": 0,
                "third_place_finishes": 0,
            }
            for user in users
        }
        for week_number in ordered_weeks:
            results = db.execute(
                select(WeeklyResult).where(
                    WeeklyResult.league_id == league.id,
                    WeeklyResult.week_id
                    == select(NflWeek.id)
                    .where(
                        NflWeek.season == target_season,
                        NflWeek.week_number == week_number,
                    )
                    .scalar_subquery(),
                )
            ).scalars()
            for result in results:
                if result.user_id not in season_totals:
                    continue
                if result.weekly_rank == 1:
                    season_totals[result.user_id]["weekly_wins"] += 1
                    season_totals[result.user_id]["first_place_finishes"] += 1
                elif result.weekly_rank == 2:
                    season_totals[result.user_id]["second_place_finishes"] += 1
                elif result.weekly_rank == 3:
                    season_totals[result.user_id]["third_place_finishes"] += 1

        ranked_season_users = sorted(
            users,
            key=lambda user: (
                -season_totals[user.id]["total_points"],
                -season_totals[user.id]["weekly_wins"],
                user.display_name,
            ),
        )
        for rank, user in enumerate(ranked_season_users, start=1):
            _upsert_season_result(
                db,
                league_id=league.id,
                user_id=user.id,
                season=target_season,
                current_rank=rank,
                **season_totals[user.id],
            )

        db.add(
            SeedRun(
                fixture_key=FIXTURE_KEY,
                season=target_season,
                league_id=league.id,
                week_count=len(ordered_weeks),
                game_count=len(ordered_weeks) * len(DEMO_GAMES),
                pick_count=pick_count,
                completed_at=seed_now,
            )
        )
        db.commit()
        return str(league.id), len(ordered_weeks), len(users), pick_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int)
    parser.add_argument("--weeks", type=int, nargs="+", default=list(DEFAULT_WEEKS))
    args = parser.parse_args()
    try:
        completed_before_run = False
        with SessionLocal() as db:
            completed_before_run = db.get(SeedRun, FIXTURE_KEY) is not None
        league_id, week_count, member_count, pick_count = seed_leaderboard_data(
            season=args.season,
            weeks=tuple(args.weeks),
        )
    except ValueError as error:
        parser.error(str(error))
        return
    if completed_before_run:
        print("Historical fixture already seeded; exiting.")
        return
    print(
        f"Seeded league {league_id}: {week_count} historical weeks, "
        f"{member_count} members, {pick_count} picks."
    )


if __name__ == "__main__":
    main()
