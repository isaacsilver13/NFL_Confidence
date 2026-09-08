"""CRUD queries for weekly member payment records."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.member_weekly_payment import MemberWeeklyPayment


def list_by_league_and_week(
    db: Session, *, league_id: uuid.UUID, week_id: uuid.UUID
) -> list[MemberWeeklyPayment]:
    return list(
        db.execute(
            select(MemberWeeklyPayment).where(
                MemberWeeklyPayment.league_id == league_id,
                MemberWeeklyPayment.week_id == week_id,
            )
        ).scalars()
    )


def get_by_league_week_user(
    db: Session, *, league_id: uuid.UUID, week_id: uuid.UUID, user_id: uuid.UUID
) -> MemberWeeklyPayment | None:
    return db.execute(
        select(MemberWeeklyPayment).where(
            MemberWeeklyPayment.league_id == league_id,
            MemberWeeklyPayment.week_id == week_id,
            MemberWeeklyPayment.user_id == user_id,
        )
    ).scalar_one_or_none()


def create(
    db: Session,
    *,
    league_id: uuid.UUID,
    week_id: uuid.UUID,
    user_id: uuid.UUID,
    is_paid: bool,
    marked_at: datetime,
    marked_by_user_id: uuid.UUID,
) -> MemberWeeklyPayment:
    payment = MemberWeeklyPayment(
        league_id=league_id,
        week_id=week_id,
        user_id=user_id,
        is_paid=is_paid,
        marked_at=marked_at,
        marked_by_user_id=marked_by_user_id,
    )
    db.add(payment)
    db.flush()
    return payment
