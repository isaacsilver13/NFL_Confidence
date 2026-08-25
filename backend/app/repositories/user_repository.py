"""CRUD operations for the User model. No business logic here — see app.services."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_by_google_id(db: Session, google_id: str) -> User | None:
    return db.execute(select(User).where(User.google_id == google_id)).scalar_one_or_none()


def get_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def create(
    db: Session, *, google_id: str, email: str, display_name: str, avatar_url: str | None
) -> User:
    user = User(google_id=google_id, email=email, display_name=display_name, avatar_url=avatar_url)
    db.add(user)
    db.flush()
    return user
