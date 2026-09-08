"""Commissioner workflows for weekly payment status and unpaid picks."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.member_weekly_payment import MemberWeeklyPayment
from app.repositories import (
    league_member_repository,
    member_weekly_payment_repository,
    nfl_week_repository,
    pick_repository,
)
from app.services import scoring_service


def _get_week(db: Session, *, league: League, week_number: int):
    week = nfl_week_repository.get_by_season_and_week(
        db, season=league.season, week_number=week_number
    )
    if week is None:
        raise NotFoundError(f"Week {week_number} does not exist for this league's season.")
    return week


def _member_or_404(db: Session, *, league: League, user_id: uuid.UUID) -> LeagueMember:
    member = league_member_repository.get_by_league_and_user(db, league.id, user_id)
    if member is None:
        raise NotFoundError("League member not found.")
    return member


def list_payment_statuses(
    db: Session, *, league: League, week_number: int
) -> tuple[int, list[tuple[LeagueMember, MemberWeeklyPayment | None, int]]]:
    week = _get_week(db, league=league, week_number=week_number)
    members = league_member_repository.list_by_league(db, league.id)
    payments = {
        payment.user_id: payment
        for payment in member_weekly_payment_repository.list_by_league_and_week(
            db, league_id=league.id, week_id=week.id
        )
    }
    return week_number, [
        (
            member,
            payments.get(member.user_id),
            pick_repository.count_voided_by_user_and_week(
                db, user_id=member.user_id, week_id=week.id
            ),
        )
        for member in members
    ]


def mark_payment(
    db: Session,
    *,
    league: League,
    marked_by: uuid.UUID,
    user_id: uuid.UUID,
    week_number: int,
    is_paid: bool,
) -> None:
    _member_or_404(db, league=league, user_id=user_id)
    week = _get_week(db, league=league, week_number=week_number)
    payment = member_weekly_payment_repository.get_by_league_week_user(
        db, league_id=league.id, week_id=week.id, user_id=user_id
    )
    marked_at = datetime.now(timezone.utc)
    if payment is None:
        member_weekly_payment_repository.create(
            db,
            league_id=league.id,
            week_id=week.id,
            user_id=user_id,
            is_paid=is_paid,
            marked_at=marked_at,
            marked_by_user_id=marked_by,
        )
    else:
        payment.is_paid = is_paid
        payment.marked_at = marked_at
        payment.marked_by_user_id = marked_by
    db.commit()


def void_unpaid_picks(
    db: Session, *, league: League, week_number: int, voided_by: uuid.UUID
) -> tuple[int, int]:
    week = _get_week(db, league=league, week_number=week_number)
    members = league_member_repository.list_by_league(db, league.id)
    payments = {
        payment.user_id: payment
        for payment in member_weekly_payment_repository.list_by_league_and_week(
            db, league_id=league.id, week_id=week.id
        )
    }
    unpaid_user_ids = {
        member.user_id
        for member in members
        if not payments.get(member.user_id, None) or not payments[member.user_id].is_paid
    }
    picks = pick_repository.list_by_week_and_users(db, week_id=week.id, user_ids=unpaid_user_ids)
    now = datetime.now(timezone.utc)
    for pick in picks:
        if pick.voided_at is None:
            pick.voided_at = now
            pick.voided_by_user_id = voided_by
            pick.points_earned = None
    affected_user_ids: set[uuid.UUID] = set()
    voided_pick_count = 0
    for pick in picks:
        if pick.voided_at == now:
            affected_user_ids.add(pick.user_id)
            voided_pick_count += 1
    db.flush()
    scoring_service.score_week(db, league=league, week_id=week.id)
    return voided_pick_count, len(affected_user_ids)
