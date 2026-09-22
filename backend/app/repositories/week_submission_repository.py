"""CRUD and queries for weekly pick submissions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.week_submission import WeekSubmission


def get_by_user_and_week(
    db: Session, *, user_id: uuid.UUID, week_id: uuid.UUID
) -> WeekSubmission | None:
    return db.execute(
        select(WeekSubmission).where(
            WeekSubmission.user_id == user_id, WeekSubmission.week_id == week_id
        )
    ).scalar_one_or_none()


def list_user_ids_for_week(db: Session, *, week_id: uuid.UUID) -> set[uuid.UUID]:
    rows = db.execute(
        select(WeekSubmission.user_id).where(WeekSubmission.week_id == week_id)
    ).scalars()
    return set(rows)


def list_by_week(db: Session, *, week_id: uuid.UUID) -> list[WeekSubmission]:
    return list(
        db.execute(select(WeekSubmission).where(WeekSubmission.week_id == week_id)).scalars()
    )


def upsert(db: Session, *, user_id: uuid.UUID, week_id: uuid.UUID) -> WeekSubmission:
    submission = get_by_user_and_week(db, user_id=user_id, week_id=week_id)
    if submission is None:
        submission = WeekSubmission(user_id=user_id, week_id=week_id)
        db.add(submission)
    else:
        submission.submitted_at = datetime.now(timezone.utc)
    db.flush()
    return submission
