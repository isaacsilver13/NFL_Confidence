"""Which job slots are due at a given moment (pure schedule logic, no DB)."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.jobs.schedule import ScheduleConfig, due_slots

CHICAGO = ZoneInfo("America/Chicago")
CFG = ScheduleConfig()


def at(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=CHICAGO)


def names(now: datetime, cfg: ScheduleConfig = CFG) -> list[str]:
    return [slot.job_name for slot in due_slots(now, cfg)]


# 2026-10-04 is a Sunday (CDT).
@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (9, 59, False),
        (10, 0, True),
        (22, 59, True),
        (23, 0, True),
        (23, 1, True),  # still inside the 23:00 hour bucket: a late tick fires it
    ],
)
def test_sunday_window_boundaries(hour: int, minute: int, expected: bool) -> None:
    assert ("sunday_score_sync" in names(at(2026, 10, 4, hour, minute))) is expected


def test_sunday_window_ends_at_midnight() -> None:
    # Monday 00:00 is outside the Sunday window (and Mon/Thu sync starts at 19:00).
    assert "sunday_score_sync" not in names(at(2026, 10, 5, 0, 0))


def test_sunday_slot_covers_every_hour_10_through_23() -> None:
    hours = [h for h in range(24) if "sunday_score_sync" in names(at(2026, 10, 4, h, 5))]
    assert hours == list(range(10, 24))


def test_sunday_window_is_configurable() -> None:
    cfg = ScheduleConfig(sunday_sync_start_hour=7, sunday_sync_end_hour=20)
    assert "sunday_score_sync" in names(at(2026, 10, 4, 7), cfg)
    assert "sunday_score_sync" not in names(at(2026, 10, 4, 21), cfg)


def test_slot_key_is_stable_within_an_hour_and_differs_across_hours() -> None:
    first = due_slots(at(2026, 10, 4, 10, 5), CFG)[0]
    later = due_slots(at(2026, 10, 4, 10, 55), CFG)[0]
    next_hour = due_slots(at(2026, 10, 4, 11, 5), CFG)[0]
    assert first.key == later.key
    assert first.key != next_hour.key


def test_utc_input_is_converted_to_chicago() -> None:
    # 15:05 UTC on a CDT Sunday is 10:05 Chicago; 15:05 UTC in CST (Nov) is 09:05.
    assert "sunday_score_sync" in names(datetime(2026, 10, 4, 15, 5, tzinfo=timezone.utc))
    assert "sunday_score_sync" not in names(datetime(2026, 11, 8, 15, 5, tzinfo=timezone.utc))
    assert "sunday_score_sync" in names(datetime(2026, 11, 8, 16, 5, tzinfo=timezone.utc))


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError):
        due_slots(datetime(2026, 10, 4, 10, 0), CFG)


# Mon 2026-10-05 and Thu 2026-10-08.
@pytest.mark.parametrize("day", [5, 8])
def test_monday_thursday_sync_window(day: int) -> None:
    assert "monday_thursday_score_sync" not in names(at(2026, 10, day, 18, 59))
    assert "monday_thursday_score_sync" in names(at(2026, 10, day, 19, 0))
    assert "monday_thursday_score_sync" in names(at(2026, 10, day, 22, 59))
    assert "monday_thursday_score_sync" not in names(at(2026, 10, day, 23, 0))


def test_monday_thursday_sync_does_not_run_on_other_days() -> None:
    assert "monday_thursday_score_sync" not in names(at(2026, 10, 6, 20))  # Tuesday
    assert "monday_thursday_score_sync" not in names(at(2026, 10, 4, 20))  # Sunday


def test_overnight_sync_runs_daily_at_2am() -> None:
    for day in range(4, 11):
        assert "overnight_score_sync" in names(at(2026, 10, day, 2, 30))
        assert "overnight_score_sync" not in names(at(2026, 10, day, 3, 0))


def test_default_import_is_tuesday_9am() -> None:
    assert "schedule_import" in names(at(2026, 10, 6, 9, 10))  # Tuesday
    assert "schedule_import" not in names(at(2026, 10, 6, 10, 0))
    assert "schedule_import" not in names(at(2026, 10, 5, 9, 10))  # Monday


def test_import_day_and_hour_are_configurable() -> None:
    cfg = ScheduleConfig(import_day="mon", import_hour=10)
    assert "schedule_import" in names(at(2026, 10, 5, 10, 0), cfg)
    assert "schedule_import" not in names(at(2026, 10, 6, 9, 0), cfg)


def test_default_reminder_is_wednesday_5pm() -> None:
    assert "weekly_picks_reminder" in names(at(2026, 10, 7, 17, 0))
    assert "weekly_picks_reminder" not in names(at(2026, 10, 7, 18, 0))
    assert "weekly_picks_reminder" not in names(at(2026, 10, 8, 17, 0))


def test_default_weekly_report_is_tuesday_8am() -> None:
    assert "weekly_report" in names(at(2026, 10, 6, 8, 0))
    assert "weekly_report" not in names(at(2026, 10, 6, 9, 0))
    assert "weekly_report" not in names(at(2026, 10, 7, 8, 0))


def test_lock_slot_is_due_every_hour() -> None:
    assert all("lock_expired_picks" in names(at(2026, 10, 6, h, 5)) for h in range(24))


def test_quiet_hour_only_has_lock() -> None:
    # Tuesday 14:00 Chicago: no sync window, no import, no reminder.
    assert names(at(2026, 10, 6, 14, 5)) == ["lock_expired_picks"]


def test_import_runs_before_sync_and_lock_is_last() -> None:
    cfg = ScheduleConfig(import_day="sun", import_hour=10)
    assert names(at(2026, 10, 4, 10, 5), cfg) == [
        "schedule_import",
        "sunday_score_sync",
        "lock_expired_picks",
    ]


def test_spring_forward_sunday_has_no_2am_overnight_slot() -> None:
    # 2027-03-14: clocks jump 02:00 CST -> 03:00 CDT, so local 02:xx does not exist.
    # The Sunday-window slots still fire on time after the change.
    assert "overnight_score_sync" not in names(at(2027, 3, 14, 3, 0))
    assert "sunday_score_sync" in names(at(2027, 3, 14, 10, 5))


def test_fall_back_sunday_window_is_unchanged() -> None:
    # 2026-11-01: clocks fall back 02:00 CDT -> 01:00 CST.
    hours = [h for h in range(24) if "sunday_score_sync" in names(at(2026, 11, 1, h, 5))]
    assert hours == list(range(10, 24))


def test_unknown_weekday_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        ScheduleConfig(import_day="funday")
