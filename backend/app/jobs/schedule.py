"""Pure schedule logic: which job slots are due at a given moment.

The app no longer runs its own cron. An external trigger (a GitHub Actions
cron, see `.github/workflows/scheduled-tick.yml`) wakes the machine and calls
the tick endpoint; `due_slots` then decides, in the app's timezone, which jobs
are due. Nothing here touches the database or the clock, so every window edge
can be unit tested.

A slot is one hour bucket of one job (`sunday_score_sync:2026-10-04T10`). It is
due for the whole clock hour, so a tick that arrives late but inside the hour
still fires it, and the claim step makes a repeat call inside the same hour a
no-op.
"""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _weekday(name: str) -> int:
    try:
        return _WEEKDAYS[name.strip().lower()[:3]]
    except KeyError:
        raise ValueError(f"Unknown weekday name: {name!r}") from None


@dataclass(frozen=True)
class ScheduleConfig:
    """When each job is due. Hours are 0-23 in `timezone`; end hours are inclusive.

    Defaults reproduce the schedule prod already runs, expressed in Chicago time.
    """

    timezone: str = "America/Chicago"
    sunday_sync_start_hour: int = 10
    sunday_sync_end_hour: int = 23
    monthu_sync_start_hour: int = 19
    monthu_sync_end_hour: int = 22
    overnight_sync_hour: int = 2
    import_day: str = "tue"
    import_hour: int = 9
    reminder_day: str = "wed"
    reminder_hour: int = 17
    report_day: str = "tue"
    report_hour: int = 8

    def __post_init__(self) -> None:
        # Fail at construction, not at the first tick, on a mistyped day name.
        _weekday(self.import_day)
        _weekday(self.reminder_day)
        _weekday(self.report_day)

    @classmethod
    def from_settings(cls, settings) -> "ScheduleConfig":
        return cls(
            timezone=settings.scheduler_timezone,
            sunday_sync_start_hour=settings.sunday_sync_start_hour,
            sunday_sync_end_hour=settings.sunday_sync_end_hour,
            monthu_sync_start_hour=settings.monthu_sync_start_hour,
            monthu_sync_end_hour=settings.monthu_sync_end_hour,
            overnight_sync_hour=settings.overnight_sync_hour,
            import_day=settings.import_day,
            import_hour=settings.import_hour,
            reminder_day=settings.reminder_day,
            reminder_hour=settings.reminder_hour,
            report_day=settings.report_day,
            report_hour=settings.report_hour,
        )


@dataclass(frozen=True)
class Slot:
    job_name: str
    key: str  # unique per job per local clock hour


def due_slots(now: datetime, cfg: ScheduleConfig) -> list[Slot]:
    """Slots due at `now`, in run order (import -> syncs -> reminder/report -> pick lock)."""
    if now.tzinfo is None:
        raise ValueError("due_slots needs a timezone-aware datetime")

    local = now.astimezone(ZoneInfo(cfg.timezone))
    bucket = local.strftime("%Y-%m-%dT%H")
    weekday, hour = local.weekday(), local.hour

    due: list[str] = []
    if weekday == _weekday(cfg.import_day) and hour == cfg.import_hour:
        due.append("schedule_import")
    if weekday == 6 and cfg.sunday_sync_start_hour <= hour <= cfg.sunday_sync_end_hour:
        due.append("sunday_score_sync")
    if weekday in (0, 3) and cfg.monthu_sync_start_hour <= hour <= cfg.monthu_sync_end_hour:
        due.append("monday_thursday_score_sync")
    if hour == cfg.overnight_sync_hour:
        due.append("overnight_score_sync")
    if weekday == _weekday(cfg.reminder_day) and hour == cfg.reminder_hour:
        due.append("weekly_picks_reminder")
    if weekday == _weekday(cfg.report_day) and hour == cfg.report_hour:
        due.append("weekly_report")
    # Stamps locked_at once a kickoff has passed; cheap and idempotent. Bookkeeping only:
    # pick writes enforce the lock at kickoff themselves.
    due.append("lock_expired_picks")

    return [Slot(name, f"{name}:{bucket}") for name in due]
