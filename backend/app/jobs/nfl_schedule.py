"""Callable Tuesday schedule import job."""

import argparse
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.espn import fetch_schedule
from app.models.nfl_game import NflGame
from app.models.notification_delivery import NotificationDelivery
from app.models.reminder_preference import ReminderPreference
from app.repositories import (
    league_member_repository,
    league_repository,
    nfl_game_repository,
    nfl_week_repository,
    pick_repository,
)
from app.services import scoring_service, weeks_service
from app.services.email_service import send_weekly_reminder
from app.services.nfl_schedule_service import import_games

logger = logging.getLogger(__name__)


def run_schedule_import(*, season: int, week_number: int) -> int:
    games = fetch_schedule(season, week_number)
    with SessionLocal() as db:
        return import_games(db, games)


def run_current_week_sync() -> int:
    """Import the active league week and recompute any finalized outcomes."""

    with SessionLocal() as db:
        league = league_repository.get_active(db)
        if league is None:
            logger.info("Skipping NFL sync because no active league exists")
            return 0
        week = weeks_service.get_current_week(db)
        imported_games = import_games(db, fetch_schedule(league.season, week.week_number))
        finalized_games = scoring_service.score_week(db, league=league, week_id=week.id)
        logger.info(
            "NFL sync complete season=%s week=%s imported_games=%s finalized_games=%s",
            league.season,
            week.week_number,
            imported_games,
            finalized_games,
        )
        return imported_games


def run_next_week_import() -> int:
    """Import the next unimported week for the active league."""

    with SessionLocal() as db:
        league = league_repository.get_active(db)
        if league is None:
            logger.info("Skipping NFL schedule import because no active league exists")
            return 0
        weeks = nfl_week_repository.list_by_season(db, season=league.season)
        week_number = max((week.week_number for week in weeks), default=0) + 1
        imported_games = import_games(db, fetch_schedule(league.season, week_number))
        logger.info(
            "NFL schedule import complete season=%s week=%s imported_games=%s",
            league.season,
            week_number,
            imported_games,
        )
        return imported_games


def lock_expired_picks() -> int:
    """Stamp all picks once the active week's earliest kickoff has passed."""

    with SessionLocal() as db:
        league = league_repository.get_active(db)
        if league is None:
            return 0
        week = weeks_service.get_current_week(db)

        # Eager load picks to avoid N+1 queries
        games = list(
            db.execute(
                select(NflGame)
                .where(NflGame.week_id == week.id)
                .options(selectinload(NflGame.picks))
            ).scalars()
        )
        if not games:
            return 0
        deadline = min(game.kickoff_time for game in games)
        now = datetime.now(timezone.utc)
        if deadline > now:
            return 0
        locked = 0
        for game in games:
            for pick in game.picks:
                if pick.locked_at is None:
                    pick.locked_at = deadline
                    locked += 1
        db.commit()
        if locked:
            logger.info(
                "NFL picks locked season=%s week=%s count=%s",
                league.season,
                week.week_number,
                locked,
            )
        return locked


def _send_weekly_reminders(db: Session) -> int:
    league = league_repository.get_active(db)
    if league is None:
        return 0
    week = weeks_service.get_current_week(db)
    games = nfl_game_repository.get_by_week_id(db, week.id)
    if not games:
        return 0
    deadline = min(game.kickoff_time for game in games)
    members = league_member_repository.list_by_league(db, league.id)
    user_ids = [member.user_id for member in members]
    preferences = {
        preference.user_id: preference
        for preference in db.execute(
            select(ReminderPreference).where(ReminderPreference.user_id.in_(user_ids))
        ).scalars()
    }
    delivered = {
        user_id
        for user_id in db.execute(
            select(NotificationDelivery.user_id).where(
                NotificationDelivery.week_id == week.id,
                NotificationDelivery.notification_type == "weekly_picks_reminder",
            )
        ).scalars()
    }
    sent = 0
    for member in members:
        preference = preferences.get(member.user_id)
        if preference is not None and (
            not preference.email_enabled or not preference.weekly_reminder
        ):
            continue
        if member.user_id in delivered:
            continue
        picks = pick_repository.list_by_user_and_week(db, user_id=member.user_id, week_id=week.id)
        remaining = len(games) - len(picks)
        if remaining <= 0:
            continue
        send_weekly_reminder(
            to=member.user.email,
            season=league.season,
            week_number=week.week_number,
            remaining_picks=remaining,
            deadline=deadline.isoformat(),
            picks_link=f"{get_settings().app_url.rstrip('/')}/picks",
        )
        db.add(
            NotificationDelivery(
                user_id=member.user_id,
                week_id=week.id,
                notification_type="weekly_picks_reminder",
            )
        )
        sent += 1
    db.commit()
    logger.info(
        "Weekly reminder run season=%s week=%s sent=%s",
        league.season,
        week.week_number,
        sent,
    )
    return sent


def send_weekly_reminders(db: Session | None = None) -> int:
    if db is not None:
        return _send_weekly_reminders(db)
    with SessionLocal() as session:
        return _send_weekly_reminders(session)


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
