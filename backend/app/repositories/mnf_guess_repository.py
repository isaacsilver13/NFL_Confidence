"""Queries for Monday Night guesses."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mnf_guess import MnfGuess


def get(db: Session, *, user_id: uuid.UUID, week_id: uuid.UUID) -> MnfGuess | None:
    return db.execute(
        select(MnfGuess).where(MnfGuess.user_id == user_id, MnfGuess.week_id == week_id)
    ).scalar_one_or_none()


def upsert(
    db: Session, *, user_id: uuid.UUID, week_id: uuid.UUID, points: int, yards: int
) -> MnfGuess:
    guess = get(db, user_id=user_id, week_id=week_id)
    if guess is None:
        guess = MnfGuess(user_id=user_id, week_id=week_id, points=points, yards=yards)
        db.add(guess)
    else:
        guess.points, guess.yards = points, yards
    db.flush()
    return guess


def list_by_week(db: Session, *, week_id: uuid.UUID) -> list[MnfGuess]:
    return list(db.execute(select(MnfGuess).where(MnfGuess.week_id == week_id)).scalars())
