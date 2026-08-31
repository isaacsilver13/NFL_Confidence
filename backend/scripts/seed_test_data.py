"""Seed deterministic NFL games for local end-to-end verification."""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.models.league import League
from app.models.nfl_game import NflGame
from app.repositories import league_member_repository, nfl_game_repository, nfl_week_repository
from app.services import league_service
from app.services.auth_service import get_or_create_dev_user

TEST_LEAGUE_NAME = "Local NFL Confidence Test League"
TEST_TEAMS = (
    ("BUF", "KC"),
    ("GB", "CHI"),
    ("DAL", "PHI"),
    ("SF", "SEA"),
    ("BAL", "CIN"),
)


def seed_test_data(
    *,
    season: int | None = None,
    week_number: int = 1,
    now: datetime | None = None,
) -> tuple[str, int, int]:
    seed_now = now or datetime.now(timezone.utc)
    if seed_now.tzinfo is None:
        seed_now = seed_now.replace(tzinfo=timezone.utc)

    with SessionLocal() as db:
        user = get_or_create_dev_user(db)
        league = league_service.get_active_league(db) if _has_active_league(db) else None
        if league is None:
            league = league_service.create_league(
                db,
                owner=user,
                name=TEST_LEAGUE_NAME,
                season=season or seed_now.year,
            )
        elif league_member_repository.get_by_league_and_user(db, league.id, user.id) is None:
            league_member_repository.create(
                db,
                league_id=league.id,
                user_id=user.id,
                role=LeagueRole.MEMBER,
            )
        target_season = league.season
        week = nfl_week_repository.get_by_season_and_week(
            db, season=target_season, week_number=week_number
        )
        start_date = seed_now - timedelta(days=1)
        end_date = seed_now + timedelta(days=7)
        if week is None:
            week = nfl_week_repository.create(
                db,
                season=target_season,
                week_number=week_number,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            week.start_date = start_date
            week.end_date = end_date
            week.status = WeekStatus.REGULAR

        for index, (away_team, home_team) in enumerate(TEST_TEAMS, start=1):
            espn_game_id = f"local-test-{target_season}-{week_number}-{index}"
            game = nfl_game_repository.get_by_espn_game_id(db, espn_game_id)
            kickoff_time = seed_now + timedelta(days=index)
            values = {
                "week_id": week.id,
                "kickoff_time": kickoff_time,
                "away_team": away_team,
                "home_team": home_team,
                "venue_name": f"{home_team} Stadium",
                "venue_location": f"{home_team}, USA",
                "spread_team": home_team,
                "spread": float(index) - 0.5,
                "game_status": GameStatus.SCHEDULED,
                "home_score": None,
                "away_score": None,
                "winning_team": None,
                "is_tie": False,
                "last_synced": None,
            }
            if game is None:
                game = nfl_game_repository.create(
                    db,
                    espn_game_id=espn_game_id,
                    week_id=week.id,
                    kickoff_time=kickoff_time,
                    home_team=home_team,
                    away_team=away_team,
                )
                for key in ("venue_name", "venue_location", "spread_team", "spread"):
                    setattr(game, key, values[key])
            else:
                for key, value in values.items():
                    setattr(game, key, value)

        db.commit()
        game_count = db.execute(select(NflGame).where(NflGame.week_id == week.id)).scalars().all()
        return str(league.id), week.week_number, len(game_count)


def _has_active_league(db) -> bool:
    return (
        db.execute(select(League).where(League.is_active.is_(True))).scalar_one_or_none()
        is not None
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int)
    parser.add_argument("--week", type=int, default=1)
    args = parser.parse_args()
    league_id, week_number, game_count = seed_test_data(
        season=args.season,
        week_number=args.week,
    )
    print(f"Seeded league {league_id}, week {week_number}, {game_count} NFL games.")


if __name__ == "__main__":
    main()
