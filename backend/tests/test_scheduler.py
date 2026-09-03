"""Tests for scheduled job registration."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.jobs import nfl_schedule
from app.jobs.scheduler import create_scheduler
from app.models import LeagueMember, NflGame, NflWeek, Pick, ReminderPreference, User
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.services import league_service


def test_scheduler_registers_single_instance_of_each_launch_job() -> None:
    scheduler = create_scheduler()
    try:
        job_ids = {job.id for job in scheduler.get_jobs()}
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)

    assert job_ids == {
        "schedule_import",
        "lock_expired_picks",
        "sunday_score_sync",
        "monday_thursday_score_sync",
        "weekly_picks_reminder",
    }


def _make_user(db_session: Session, label: str) -> User:
    suffix = uuid.uuid4().hex
    user = User(
        google_id=f"reminder-{label}-{suffix}",
        email=f"reminder-{label}-{suffix}@example.com",
        display_name=f"Reminder {label}",
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_weekly_reminders_target_incomplete_members_and_are_idempotent(
    db_session: Session, monkeypatch
) -> None:
    owner = _make_user(db_session, "owner")
    incomplete = _make_user(db_session, "incomplete")
    disabled = _make_user(db_session, "disabled")
    complete = _make_user(db_session, "complete")
    league = league_service.create_league(
        db_session, owner=owner, name="Reminder Test League", season=2026
    )
    db_session.add_all(
        [
            LeagueMember(league_id=league.id, user_id=incomplete.id, role=LeagueRole.MEMBER),
            LeagueMember(league_id=league.id, user_id=disabled.id, role=LeagueRole.MEMBER),
            LeagueMember(league_id=league.id, user_id=complete.id, role=LeagueRole.MEMBER),
        ]
    )
    now = datetime.now(timezone.utc)
    week = NflWeek(
        season=league.season,
        week_number=1,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=7),
        status=WeekStatus.REGULAR,
    )
    db_session.add(week)
    db_session.flush()
    games = [
        NflGame(
            week_id=week.id,
            espn_game_id=f"reminder-game-{uuid.uuid4().hex}-{index}",
            kickoff_time=now + timedelta(days=index),
            away_team=f"AW{index}",
            home_team=f"HM{index}",
            game_status=GameStatus.SCHEDULED,
        )
        for index in (1, 2)
    ]
    db_session.add_all(games)
    db_session.flush()
    db_session.add(
        ReminderPreference(user_id=disabled.id, email_enabled=False, weekly_reminder=True)
    )
    db_session.add_all(
        [
            Pick(
                user_id=user.id,
                game_id=game.id,
                picked_team=game.home_team,
                confidence_value=index,
            )
            for user in (owner, complete)
            for index, game in enumerate(games, start=1)
        ]
    )
    sent: list[dict[str, object]] = []
    monkeypatch.setattr(
        nfl_schedule,
        "send_weekly_reminder",
        lambda **kwargs: sent.append(kwargs),
    )

    assert nfl_schedule.send_weekly_reminders(db_session) == 1
    assert nfl_schedule.send_weekly_reminders(db_session) == 0
    assert [message["to"] for message in sent] == [incomplete.email]
