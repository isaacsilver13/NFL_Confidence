"""Tests for Phase 1B: Email binding and HTML escaping for invitations."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.user import User
from app.services import league_service


class TestInviteEmailBinding:
    """Verify that invitations are bound to recipient email and cannot be accepted
    by users with different emails."""

    def test_user_with_matching_email_can_accept_invite(
        self, db_session: Session, owner_user: User, another_user: User
    ):
        """User with matching email successfully accepts invite."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )
        another_user_email = another_user.email

        # Create invite for another_user's email
        invite = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=another_user_email
        )

        # another_user can accept because their email matches
        membership = league_service.join_league(db_session, user=another_user, token=invite.token)
        assert membership.user_id == another_user.id
        assert membership.league_id == league.id

        # Verify invite is marked as accepted
        db_session.refresh(invite)
        assert invite.accepted_at is not None

    def test_user_with_different_email_cannot_accept_invite(
        self, db_session: Session, owner_user: User, another_user: User
    ):
        """User with different email than invite recipient gets ValidationError."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        # Create invite for owner_user's email
        invite = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=owner_user.email
        )

        # another_user tries to accept but has different email
        with pytest.raises(ValidationError) as exc_info:
            league_service.join_league(db_session, user=another_user, token=invite.token)

        assert "different email address" in str(exc_info.value).lower()

        # Verify invite is NOT marked as accepted
        db_session.refresh(invite)
        assert invite.accepted_at is None

    def test_invite_email_matching_is_case_insensitive(self, db_session: Session, owner_user: User):
        """Email matching handles uppercase/lowercase variations."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        # Create user with email in different case
        invited_email = "NewUser@example.com"
        invited_user = User(
            google_id="new-user-123",
            email=invited_email.lower(),
            display_name="New User",
        )
        db_session.add(invited_user)
        db_session.commit()

        # Create invite with different case
        invite = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=invited_email.upper()
        )

        # User can accept despite case differences
        membership = league_service.join_league(db_session, user=invited_user, token=invite.token)
        assert membership.user_id == invited_user.id

        # Verify invite was accepted
        db_session.refresh(invite)
        assert invite.accepted_at is not None

    def test_invite_email_matching_trims_whitespace(self, db_session: Session, owner_user: User):
        """Email matching strips leading/trailing whitespace."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        # Create user with email
        invited_email = "trimmed@example.com"
        invited_user = User(
            google_id="trim-user-123",
            email=invited_email,
            display_name="Trim User",
        )
        db_session.add(invited_user)
        db_session.commit()

        # Create invite with extra whitespace
        invite = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=f"  {invited_email}  "
        )

        # User can accept despite whitespace
        membership = league_service.join_league(db_session, user=invited_user, token=invite.token)
        assert membership.user_id == invited_user.id

        # Verify invite was accepted
        db_session.refresh(invite)
        assert invite.accepted_at is not None

    def test_email_mismatch_preserves_invite_for_correct_user(
        self, db_session: Session, owner_user: User, another_user: User
    ):
        """When wrong user tries to accept, invite remains valid for correct user."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        correct_email = "correct@example.com"
        correct_user = User(
            google_id="correct-user-123",
            email=correct_email,
            display_name="Correct User",
        )
        db_session.add(correct_user)
        db_session.commit()

        # Create invite for correct_user
        invite = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=correct_email
        )

        # Wrong user tries to accept
        with pytest.raises(ValidationError):
            league_service.join_league(db_session, user=another_user, token=invite.token)

        # Invite is still unused
        db_session.refresh(invite)
        assert invite.accepted_at is None

        # Correct user can still accept the same invite
        membership = league_service.join_league(db_session, user=correct_user, token=invite.token)
        assert membership.user_id == correct_user.id
        db_session.refresh(invite)
        assert invite.accepted_at is not None

    def test_invite_email_normalized_in_database(self, db_session: Session, owner_user: User):
        """Invite email is normalized (lowercased, trimmed) in database."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        # Create invite with mixed case and whitespace
        raw_email = "  MixedCase@EXAMPLE.COM  "
        invite = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=raw_email
        )

        # Verify stored email is normalized
        db_session.refresh(invite)
        assert invite.email == raw_email.lower().strip()
        assert invite.email == "mixedcase@example.com"

    def test_email_mismatch_includes_helpful_error_message(
        self, db_session: Session, owner_user: User, another_user: User
    ):
        """Error message when email doesn't match is helpful."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        invite = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=owner_user.email
        )

        with pytest.raises(ValidationError) as exc_info:
            league_service.join_league(db_session, user=another_user, token=invite.token)

        error_message = str(exc_info.value).lower()
        assert "different email" in error_message
        assert "must log in" in error_message or "sent to" in error_message

    def test_multiple_invites_to_different_emails_work_independently(
        self, db_session: Session, owner_user: User
    ):
        """Multiple invites to different emails are independent."""
        league = league_service.create_league(
            db_session, owner=owner_user, name="Test League", season=2026
        )

        # Create two users
        user1 = User(
            google_id="user1-123",
            email="user1@example.com",
            display_name="User 1",
        )
        user2 = User(
            google_id="user2-123",
            email="user2@example.com",
            display_name="User 2",
        )
        db_session.add_all([user1, user2])
        db_session.commit()

        # Create invites for each
        invite1 = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=user1.email
        )
        invite2 = league_service.create_invite(
            db_session, league=league, inviter=owner_user, email=user2.email
        )

        # user1 accepts invite1
        membership1 = league_service.join_league(db_session, user=user1, token=invite1.token)
        assert membership1.user_id == user1.id

        # user2 cannot accept invite1 (wrong email)
        with pytest.raises(ValidationError):
            league_service.join_league(db_session, user=user2, token=invite1.token)

        # user2 can accept invite2 (correct email)
        membership2 = league_service.join_league(db_session, user=user2, token=invite2.token)
        assert membership2.user_id == user2.id
