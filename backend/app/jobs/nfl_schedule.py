"""Callable Tuesday schedule import job."""

import argparse

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.espn import fetch_schedule
from app.services.nfl_schedule_service import import_games


def run_schedule_import(*, season: int, week_number: int) -> int:
    games = fetch_schedule(season, week_number)
    with SessionLocal() as db:
        return import_games(db, games)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    args = parser.parse_args()
    imported = run_schedule_import(season=args.season, week_number=args.week)
    print(f"Imported {imported} games for {args.season} week {args.week}.")


if __name__ == "__main__":
    get_settings()
    main()
