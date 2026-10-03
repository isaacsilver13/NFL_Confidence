"""Pure schedule logic: which job slots are due at a given moment.

The app has no cron of its own. An external scheduler (cron-job.org) wakes the
machine hourly and calls the tick endpoint; `due_slots` then decides, in the
app's timezone, which jobs are due. Nothing here touches the database or the
clock, so every window edge can be unit tested.

A slot is one bucket of one job. The score syncs and the pick lock are hourly:
due for their local clock hour, keyed by hour (`sunday_score_sync:2026-10-04T10`).
The single-shot jobs (import, reminder, report, overnight sync) are due from their
hour until the end of that local day and keyed by date, so a tick that arrives hours
late still runs them once. The claim step makes any repeat call a no-op.
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
    key: str  # unique per job per local hour (or day for single-shot jobs)


def due_slots(now: datetime, cfg: ScheduleConfig) -> list[Slot]:
    """Slots due at `now`, in run order (import -> syncs -> reminder/report -> pick lock)."""
    if now.tzinfo is None:
        raise ValueError("due_slots needs a timezone-aware datetime")

    local = now.astimezone(ZoneInfo(cfg.timezone))
    bucket = local.strftime("%Y-%m-%dT%H")
    day = local.strftime("%Y-%m-%d")
    weekday, hour = local.weekday(), local.hour

    hourly: list[str] = []
    if weekday == 6 and cfg.sunday_sync_start_hour <= hour <= cfg.sunday_sync_end_hour:
        hourly.append("sunday_score_sync")
    if weekday in (0, 3) and cfg.monthu_sync_start_hour <= hour <= cfg.monthu_sync_end_hour:
        hourly.append("monday_thursday_score_sync")

    # Due from their hour to the end of the local day (catch-up for a late tick).
    daily: list[str] = []
    if weekday == _weekday(cfg.import_day) and hour >= cfg.import_hour:
        daily.append("schedule_import")
    if hour >= cfg.overnight_sync_hour:
        daily.append("overnight_score_sync")
    if weekday == _weekday(cfg.reminder_day) and hour >= cfg.reminder_hour:
        daily.append("weekly_picks_reminder")
    if weekday == _weekday(cfg.report_day) and hour >= cfg.report_hour:
        daily.append("weekly_report")

    slots = [Slot(name, f"{name}:{day}") for name in daily]
    slots += [Slot(name, f"{name}:{bucket}") for name in hourly]
    # Run order: import -> syncs -> reminder/report -> pick lock.
    order = [
        "schedule_import",
        "sunday_score_sync",
        "monday_thursday_score_sync",
        "overnight_score_sync",
        "weekly_picks_reminder",
        "weekly_report",
    ]
    slots.sort(key=lambda slot: order.index(slot.job_name))
    # Stamps locked_at once a kickoff has passed; cheap and idempotent. Bookkeeping only:
    # pick writes enforce the lock at kickoff themselves.
    slots.append(Slot("lock_expired_picks", f"lock_expired_picks:{bucket}"))
    return slots
