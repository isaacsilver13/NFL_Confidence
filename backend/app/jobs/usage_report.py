"""Weekly usage report job: email the last 7 days of member activity to the commissioners.

Due on the same day and hour as the commissioner report (see `app.jobs.schedule`). Recipients
are the active league's owners (their Google sign-in emails), in one email. No league or no
owners: nothing is sent.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories import league_repository
from app.services import report_service, usage_report_service
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

WINDOW_DAYS = 7


def send_weekly_usage_report() -> int:
    """Send the report to every commissioner in one email; returns how many addresses."""
    settings = get_settings()
    tz = ZoneInfo(settings.scheduler_timezone)
    until = datetime.now(tz).date()
    since = until - timedelta(days=WINDOW_DAYS)
    with SessionLocal() as db:
        league = league_repository.get_active(db)
        recipients = (
            [m.user.email for m in report_service.commissioners(db, league=league)]
            if league
            else []
        )
        if not recipients:
            return 0
        data = usage_report_service.collect(db, since, settings.scheduler_timezone)
    html = usage_report_service.render_email_html(data, since, until)
    subject = f"NFL Confidence usage: {since:%b} {since.day} to {until:%b} {until.day}"
    send_email(to=recipients, subject=subject, html=html)
    logger.info("Usage report sent", extra={"recipients": len(recipients)})
    return len(recipients)
