"""Email delivery for league notifications.

Sends via Resend when RESEND_API_KEY is configured; otherwise logs the email so
local development and tests don't require real credentials (mirrors the dev-login
fallback pattern used for auth).
"""

import logging

import resend

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def send_email(*, to: str, subject: str, html: str) -> None:
    if not settings.resend_api_key:
        logger.info(
            "Email suppressed (no RESEND_API_KEY configured): to=%s subject=%s", to, subject
        )
        return

    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )


def send_league_invitation(
    *, to: str, league_name: str, commissioner_name: str, invite_link: str, expires_at: str
) -> None:
    subject = f"You're invited to join {league_name}"
    html = (
        f"<p>{commissioner_name} invited you to join <strong>{league_name}</strong> "
        "on NFL Confidence Pool.</p>"
        f'<p><a href="{invite_link}">Accept your invitation</a></p>'
        f"<p>This invite expires on {expires_at}.</p>"
    )
    send_email(to=to, subject=subject, html=html)
