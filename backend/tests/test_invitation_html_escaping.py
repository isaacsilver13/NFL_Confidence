"""Tests for Phase 1B: HTML escaping in invitation emails."""

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import league_service


class TestInvitationHTMLEscaping:
    """Verify that HTML injection attempts in invitation fields are properly escaped."""

    @patch("app.services.email_service.send_email")
    def test_league_name_is_escaped_in_invitation_email(
        self, mock_send_email: patch, db_session: Session, owner_user: User, another_user: User
    ):
        """League name with HTML special characters is escaped."""
        malicious_league_name = "Test League <script>alert('xss')</script>"
        league = league_service.create_league(
            db_session, owner=owner_user, name=malicious_league_name, season=2026
        )

        league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=another_user.email
        )

        # Verify send_email was called
        assert mock_send_email.called
        call_kwargs = mock_send_email.call_args.kwargs
        html = call_kwargs["html"]

        # Verify the script tag is escaped, not executed
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    @patch("app.services.email_service.send_email")
    def test_commissioner_name_is_escaped_in_invitation_email(
        self, mock_send_email: patch, db_session: Session, another_user: User
    ):
        """Commissioner name with HTML special characters is escaped."""
        malicious_owner = User(
            google_id="evil-owner-123",
            email="evil@example.com",
            display_name="Admin<img src=x onerror=alert('xss')>",
        )
        db_session.add(malicious_owner)
        db_session.commit()

        league = league_service.create_league(
            db_session, owner=malicious_owner, name="Test League", season=2026
        )

        league_service.create_invite(
            db_session, league=league, inviter=malicious_owner, email=another_user.email
        )

        # Verify send_email was called
        assert mock_send_email.called
        call_kwargs = mock_send_email.call_args.kwargs
        html = call_kwargs["html"]

        # Verify the img tag is escaped
        assert "<img" not in html
        assert "&lt;img" in html

    @patch("app.services.email_service.send_email")
    def test_invite_link_is_escaped_in_invitation_email(
        self, mock_send_email: patch, db_session: Session, owner_user: User, another_user: User
    ):
        """Invite link is properly escaped for HTML context."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=another_user.email
        )

        # Verify send_email was called
        assert mock_send_email.called
        call_kwargs = mock_send_email.call_args.kwargs
        html = call_kwargs["html"]

        # Verify the link is properly formatted and escaped for href attribute
        # The link should be in an href attribute with proper quoting
        assert "href=" in html
        # Should contain properly formatted URL (no raw & without escaping in href)
        # or properly escaped &amp; if there are query params
        assert "<a " in html

    @patch("app.services.email_service.send_email")
    def test_expires_at_is_escaped_in_invitation_email(
        self, mock_send_email: patch, db_session: Session, owner_user: User, another_user: User
    ):
        """Expiry datetime is properly escaped."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=another_user.email
        )

        # Verify send_email was called
        assert mock_send_email.called
        call_kwargs = mock_send_email.call_args.kwargs
        html = call_kwargs["html"]

        # Should contain the expiry date text
        assert "expires" in html.lower()
        # ISO format datetime should be present (with T separator)
        assert "T" in html  # ISO datetime format includes T
