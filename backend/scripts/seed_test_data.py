"""Seed real ESPN weeks plus fake demo users' picks for dev/local verification.

Games come from the same ESPN import path the live scheduler uses, so the
seed and the scheduler converge on identical rows instead of mixing fake and
real games in one week (which inflated the week's confidence-point slots).
"""

import argparse
import random
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.integrations.espn import fetch_schedule
from app.models.enums import LeagueRole
from app.models.league import League
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.repositories import (
    league_member_repository,
    nfl_game_repository,
    nfl_week_repository,
    pick_repository,
)
from app.services import league_service, scoring_service
from app.services.auth_service import get_or_create_dev_user, get_or_create_google_user
from app.services.nfl_schedule_service import _END_OF_WEEK_BUFFER, import_games

TEST_LEAGUE_NAME = "2026 NFL Confidence League"
# Fixed passcode for local/dev seeding only -- never used for production league
# creation, which always goes through the normal random-code path.
DEV_LEAGUE_INVITE_CODE = "DevinTester23"
DEFAULT_WEEK_COUNT = 5
# Earlier versions of this script seeded fake games with this ESPN id prefix.
# They get purged so they stop padding real weeks with extra slots.
LEGACY_FIXTURE_PREFIX = "local-test-"

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


def choose_pick(game: NflGame, rng: random.Random, persona_index: int) -> str:
    """Return the team abbreviation a fake user picks to win `game`.

    `persona_index` is the user's position in FAKE_USERS (0-4), so each fake
    user can have a distinct picking style. Must always return either
    `game.home_team` or `game.away_team`, and should only draw randomness from
    `rng` so re-seeding stays deterministic.
    """
    # Coin flip: keeps the demo standings unpredictable week to week.
    return game.home_team if rng.random() < 0.5 else game.away_team


def seed_test_data(
    *,
    season: int | None = None,
    week_count: int = DEFAULT_WEEK_COUNT,
    now: datetime | None = None,
) -> tuple[str, dict[int, int]]:
    """Seed weeks 1..week_count and return (league id, {week number: game count})."""

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
            # already-existing league, so it never drifts back to whatever
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
        _purge_legacy_fixture_games(db, season=target_season)
        db.commit()

        game_counts: dict[int, int] = {}
        for week_number in range(1, week_count + 1):
            import_games(db, fetch_schedule(target_season, week_number))
            week = nfl_week_repository.get_by_season_and_week(
                db, season=target_season, week_number=week_number
            )
            if week is None:
                # ESPN has no games for this week (yet); nothing to pick on.
                game_counts[week_number] = 0
                continue

            games = sorted(
                nfl_game_repository.get_by_week_id(db, week.id),
                key=lambda game: (game.kickoff_time, game.espn_game_id),
            )
            if games:
                # import_games only ever widens a week's window, so a week the
                # legacy fixture stretched into the future would stay "current"
                # forever. Re-derive the end from the real games.
                week.end_date = games[-1].kickoff_time + _END_OF_WEEK_BUFFER
            for persona_index, fake_user in enumerate(fake_users):
                rng = random.Random(f"{target_season}:{week_number}:{persona_index}")
                confidences = list(range(1, len(games) + 1))
                rng.shuffle(confidences)
                for game, confidence_value in zip(games, confidences, strict=True):
                    picked_team = choose_pick(game, rng, persona_index)
                    pick = pick_repository.get_by_user_and_game(
                        db, user_id=fake_user.id, game_id=game.id
                    )
                    if pick is None:
                        pick = pick_repository.create(
                            db,
                            user_id=fake_user.id,
                            game_id=game.id,
                            picked_team=picked_team,
                            confidence_value=confidence_value,
                        )
                    else:
                        pick.picked_team = picked_team
                        pick.confidence_value = confidence_value
                        pick.voided_at = None
                        pick.voided_by_user_id = None
                    pick.locked_at = game.kickoff_time if game.kickoff_time <= seed_now else None

            db.commit()
            scoring_service.score_week(db, league=league, week_id=week.id)
            game_counts[week_number] = len(games)

        return str(league.id), game_counts


def _purge_legacy_fixture_games(db, *, season: int) -> None:
    legacy_game_ids = select(NflGame.id).where(
        NflGame.espn_game_id.like(f"{LEGACY_FIXTURE_PREFIX}%"),
        NflGame.week_id.in_(select(NflWeek.id).where(NflWeek.season == season)),
    )
    # Explicit pick delete rather than relying on ON DELETE CASCADE, which
    # SQLite only honors when foreign keys are switched on.
    db.execute(delete(Pick).where(Pick.game_id.in_(legacy_game_ids)))
    db.execute(delete(NflGame).where(NflGame.id.in_(legacy_game_ids)))


def _has_active_league(db) -> bool:
    return (
        db.execute(select(League).where(League.is_active.is_(True))).scalar_one_or_none()
        is not None
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int)
    parser.add_argument("--weeks", type=int, default=DEFAULT_WEEK_COUNT)
    args = parser.parse_args()
    league_id, game_counts = seed_test_data(season=args.season, week_count=args.weeks)
    print(f"Seeded league {league_id}:")
    for week_number, game_count in game_counts.items():
        print(f"  week {week_number}: {game_count} games, {len(FAKE_USERS)} fake users picked")


if __name__ == "__main__":
    main()
