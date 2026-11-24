"""Email delivery for league notifications.

Sends via Resend when RESEND_API_KEY is configured; otherwise logs the email so
local development and tests don't require real credentials (mirrors the dev-login
fallback pattern used for auth).
"""

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

import resend

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def _send_smtp(recipients: list[str], subject: str, html: str) -> None:
    msg = EmailMessage()
    msg["From"] = formataddr(("NFL Confidence Pool", settings.smtp_user))
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("This email needs an HTML-capable mail client.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def send_email(*, to: str | list[str], subject: str, html: str) -> None:
    recipients = [to] if isinstance(to, str) else to
    if settings.smtp_password:
        _send_smtp(recipients, subject, html)
        return
    if not settings.resend_api_key:
        logger.info(
            "Email suppressed (no SMTP_PASSWORD or RESEND_API_KEY configured): to=%s subject=%s",
            to,
            subject,
        )
        return

    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.email_from,
            "to": recipients,
            "subject": subject,
            "html": html,
        }
    )


def send_league_invitation(
    *, to: str, league_name: str, commissioner_name: str, invite_link: str, expires_at: str
) -> None:
    subject = f"You're invited to join {league_name}"
    html = (
        f"<p>{escape(commissioner_name)} invited you to join "
        f"<strong>{escape(league_name)}</strong> "
        "on NFL Confidence Pool.</p>"
        f'<p><a href="{escape(invite_link, quote=True)}">Accept your invitation</a></p>'
        f"<p>This invite expires on {escape(expires_at)}.</p>"
    )
    send_email(to=to, subject=subject, html=html)


def send_weekly_reminder(
    *, to: str, season: int, week_number: int, remaining_picks: int, deadline: str, picks_link: str
) -> None:
    subject = "Don't forget your NFL Confidence Picks"
    html = (
        f"<p>You have <strong>{remaining_picks}</strong> pick(s) remaining for "
        f"NFL season {season}, week {week_number}.</p>"
        f"<p>Picks lock at {escape(deadline)} when the first game kicks off.</p>"
        f'<p><a href="{escape(picks_link, quote=True)}">Submit your picks</a></p>'
    )
    send_email(to=to, subject=subject, html=html)
