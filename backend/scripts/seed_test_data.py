"""Seed deterministic NFL games and demo picks for local end-to-end verification."""

import argparse
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.models.league import League
from app.models.nfl_game import NflGame
from app.repositories import (
    league_member_repository,
    nfl_game_repository,
    nfl_week_repository,
    pick_repository,
)
from app.services import league_service, scoring_service
from app.services.auth_service import get_or_create_dev_user, get_or_create_google_user

TEST_LEAGUE_NAME = "2026 NFL Confidence League"
# Fixed passcode for local/dev seeding only -- never used for production league
# creation, which always goes through the normal random-code path.
DEV_LEAGUE_INVITE_CODE = "DevinTester23"

# Real team abbreviations with a fake final score per game, so the demo week reads
# as a fully-played slate (away, home, away_score, home_score). Every team appears
# exactly once so each matchup renders with its real logo/colors.
WEEK_GAMES = (
    ("BUF", "BAL", 21, 24),
    ("MIA", "NE", 17, 27),
    ("CIN", "CLE", 30, 20),
    ("PIT", "HOU", 18, 23),
    ("DEN", "KC", 20, 26),
    ("LAC", "LV", 24, 20),
    ("IND", "JAX", 27, 21),
    ("TB", "TEN", 22, 19),
    ("DAL", "PHI", 24, 28),
    ("WAS", "NYG", 20, 17),
    ("CHI", "DET", 21, 31),
    ("GB", "MIN", 17, 14),
    ("ARI", "LAR", 20, 27),
    ("SF", "SEA", 24, 21),
)

# Fake demo users for backfilled picks; never used for production auth.
FAKE_USERS = (
    {
        "google_id": "dev-fake-user-1",
        "email": "fake1@nflconfidence.test",
        "display_name": "Marcus Bearclaw",
    },
    {
        "google_id": "dev-fake-user-2",
        "email": "fake2@nflconfidence.test",
        "display_name": "Ditka's Ghost",
    },
    {
        "google_id": "dev-fake-user-3",
        "email": "fake3@nflconfidence.test",
        "display_name": "Soldier Field Sam",
    },
    {
        "google_id": "dev-fake-user-4",
        "email": "fake4@nflconfidence.test",
        "display_name": "Windy City Wendy",
    },
    {
        "google_id": "dev-fake-user-5",
        "email": "fake5@nflconfidence.test",
        "display_name": "Monsters of the Midway",
    },
)


def seed_test_data(
    *,
    season: int | None = None,
    week_number: int = 5,
    now: datetime | None = None,
) -> tuple[str, int, int]:
    seed_now = now or datetime.now(timezone.utc)
    if seed_now.tzinfo is None:
        seed_now = seed_now.replace(tzinfo=timezone.utc)

    with SessionLocal() as db:
        dev_user = get_or_create_dev_user(db)
        league = league_service.get_active_league(db) if _has_active_league(db) else None
        if league is None:
            league = league_service.create_league(
                db,
                owner=dev_user,
                name=TEST_LEAGUE_NAME,
                season=season or seed_now.year,
                invite_code=DEV_LEAGUE_INVITE_CODE,
            )
        else:
            # Self-healing: keep the dev passcode pinned even on a re-seed of an
            # already-existing local league, so it never drifts back to whatever
            # random code the league happened to be created with previously.
            league.invite_code = DEV_LEAGUE_INVITE_CODE
            if league_member_repository.get_by_league_and_user(db, league.id, dev_user.id) is None:
                league_member_repository.create(
                    db,
                    league_id=league.id,
                    user_id=dev_user.id,
                    role=LeagueRole.MEMBER,
                )

        fake_users = [
            get_or_create_google_user(
                db,
                google_id=entry["google_id"],
                email=entry["email"],
                display_name=entry["display_name"],
                avatar_url=None,
            )
            for entry in FAKE_USERS
        ]
        for fake_user in fake_users:
            if league_member_repository.get_by_league_and_user(db, league.id, fake_user.id) is None:
                league_member_repository.create(
                    db,
                    league_id=league.id,
                    user_id=fake_user.id,
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

        games: list[NflGame] = []
        for index, (away_team, home_team, away_score, home_score) in enumerate(WEEK_GAMES, start=1):
            espn_game_id = f"local-test-{target_season}-{week_number}-{index}"
            game = nfl_game_repository.get_by_espn_game_id(db, espn_game_id)
            # Kickoff stays in the future even though the game is FINAL, so the
            # demo week's picks never lock (locking is purely kickoff-time based)
            # while still showing a fully-played, scored slate.
            kickoff_time = seed_now + timedelta(days=index)
            if away_score == home_score:
                winning_team, is_tie = None, True
            else:
                winning_team = home_team if home_score > away_score else away_team
                is_tie = False
            values = {
                "week_id": week.id,
                "kickoff_time": kickoff_time,
                "away_team": away_team,
                "home_team": home_team,
                "venue_name": f"{home_team} Stadium",
                "venue_location": f"{home_team}, USA",
                "spread_team": home_team,
                "spread": float(index) - 0.5,
                "game_status": GameStatus.FINAL,
                "home_score": home_score,
                "away_score": away_score,
                "winning_team": winning_team,
                "is_tie": is_tie,
                "last_synced": seed_now,
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
            for key, value in values.items():
                setattr(game, key, value)
            games.append(game)

        db.flush()

        all_users = [dev_user, *fake_users]
        confidence_values = list(range(1, len(games) + 1))
        for user_index, user in enumerate(all_users):
            rng = random.Random(f"{week.id}:{user_index}")
            shuffled_confidences = confidence_values.copy()
            rng.shuffle(shuffled_confidences)
            for game, confidence_value in zip(games, shuffled_confidences, strict=True):
                picked_team = game.home_team if rng.random() < 0.5 else game.away_team
                pick = pick_repository.get_by_user_and_game(db, user_id=user.id, game_id=game.id)
                if pick is None:
                    pick_repository.create(
                        db,
                        user_id=user.id,
                        game_id=game.id,
                        picked_team=picked_team,
                        confidence_value=confidence_value,
                    )
                else:
                    pick.picked_team = picked_team
                    pick.confidence_value = confidence_value
                    pick.locked_at = None
                    pick.voided_at = None
                    pick.voided_by_user_id = None

        db.commit()
        scoring_service.score_week(db, league=league, week_id=week.id)

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
    parser.add_argument("--week", type=int, default=5)
    args = parser.parse_args()
    league_id, week_number, game_count = seed_test_data(
        season=args.season,
        week_number=args.week,
    )
    print(f"Seeded league {league_id}, week {week_number}, {game_count} NFL games.")


if __name__ == "__main__":
    main()
