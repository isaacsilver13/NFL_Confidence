"""Weekly usage report job: email the last 7 days of member activity to USAGE_REPORT_TO.

Due on the same day and hour as the commissioner report (see `app.jobs.schedule`). With
USAGE_REPORT_TO empty the job does nothing, so the report goes only where it is configured.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services import usage_report_service
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

WINDOW_DAYS = 7


def send_weekly_usage_report() -> int:
    """Send the report to each address in USAGE_REPORT_TO; returns how many were sent."""
    settings = get_settings()
    recipients = [a.strip() for a in settings.usage_report_to.split(",") if a.strip()]
    if not recipients:
        return 0

    tz = ZoneInfo(settings.scheduler_timezone)
    until = datetime.now(tz).date()
    since = until - timedelta(days=WINDOW_DAYS)
    with SessionLocal() as db:
        data = usage_report_service.collect(db, since, settings.scheduler_timezone)
    html = usage_report_service.render_email_html(data, since, until)
    subject = f"NFL Confidence usage: {since:%b} {since.day} to {until:%b} {until.day}"
    send_email(to=recipients, subject=subject, html=html)
    logger.info("Usage report sent", extra={"recipients": len(recipients)})
    return len(recipients)
