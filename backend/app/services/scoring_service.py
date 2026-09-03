"""Recompute confidence-pool scores from the imported NFL game outcomes."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.models.enums import GameStatus, WeekStatus
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.models.season_result import SeasonResult
from app.models.weekly_result import WeeklyResult


def _pick_points(pick: Pick) -> int:
    game = pick.game
    if game.game_status != GameStatus.FINAL or game.is_tie or game.winning_team is None:
        return 0
    return pick.confidence_value if pick.picked_team == game.winning_team else 0


def _rank_key(result: WeeklyResult) -> tuple[int, int, int, str]:
    return (
        -result.total_points,
        -result.correct_picks,
        -result.highest_confidence_win,
        str(result.user_id),
    )


def _assign_weekly_ranks(results: list[WeeklyResult]) -> None:
    ordered = sorted(results, key=_rank_key)
    previous_key: tuple[int, int, int] | None = None
    previous_rank = 0
    for position, result in enumerate(ordered, start=1):
        current_key = (
            result.total_points,
            result.correct_picks,
            result.highest_confidence_win,
        )
        if current_key != previous_key:
            previous_rank = position
            previous_key = current_key
        result.weekly_rank = previous_rank


def _get_or_create_weekly_result(
    db: Session, *, league_id: uuid.UUID, week_id: uuid.UUID, user_id: uuid.UUID
) -> WeeklyResult:
    """Get or create a weekly result using UPSERT pattern for concurrent safety.

    Uses PostgreSQL ON CONFLICT DO NOTHING to safely handle concurrent calls:
    - First call creates the record
    - Concurrent calls silently ignore the conflict
    - Both return the same record
    """
    # Use PostgreSQL UPSERT: insert with on_conflict_do_nothing()
    stmt = (
        pg_insert(WeeklyResult)
        .values(
            league_id=league_id,
            week_id=week_id,
            user_id=user_id,
        )
        .on_conflict_do_nothing()
    )

    db.execute(stmt)

    # Now fetch the record (either just created or already existed)
    result = db.execute(
        select(WeeklyResult).where(
            WeeklyResult.league_id == league_id,
            WeeklyResult.week_id == week_id,
            WeeklyResult.user_id == user_id,
        )
    ).scalar_one_or_none()

    if result is None:
        # This should not happen if UPSERT worked, but fallback for safety
        result = WeeklyResult(league_id=league_id, week_id=week_id, user_id=user_id)
        db.add(result)
        db.flush()

    return result


def _get_or_create_season_result(
    db: Session, *, league_id: uuid.UUID, season: int, user_id: uuid.UUID
) -> SeasonResult:
    result = db.execute(
        select(SeasonResult).where(
            SeasonResult.league_id == league_id,
            SeasonResult.season == season,
            SeasonResult.user_id == user_id,
        )
    ).scalar_one_or_none()
    if result is None:
        result = SeasonResult(
            league_id=league_id,
            season=season,
            user_id=user_id,
        )
        db.add(result)
    return result


def score_week(db: Session, *, league: League, week_id: uuid.UUID) -> int:
    """Recompute one league's scores and return the number of finalized games.

    The calculation is a full rebuild of derived result rows, so repeated ESPN
    syncs or job retries do not double-count points or wins.
    """

    week = db.get(NflWeek, week_id)
    if week is None or week.season != league.season:
        raise NotFoundError("The requested NFL week does not exist.")

    games = list(db.execute(select(NflGame).where(NflGame.week_id == week.id)).scalars().all())
    members = list(
        db.execute(
            select(LeagueMember)
            .where(LeagueMember.league_id == league.id)
            .options(joinedload(LeagueMember.user))
        )
        .scalars()
        .all()
    )
    picks = list(
        db.execute(
            select(Pick)
            .join(NflGame, Pick.game_id == NflGame.id)
            .where(NflGame.week_id == week.id)
            .options(joinedload(Pick.game))
        )
        .scalars()
        .all()
    )

    picks_by_user: dict[uuid.UUID, list[Pick]] = {}
    for pick in picks:
        if pick.game.game_status == GameStatus.FINAL:
            pick.points_earned = _pick_points(pick)
        picks_by_user.setdefault(pick.user_id, []).append(pick)

    weekly_results: list[WeeklyResult] = []
    for member in members:
        member_picks = picks_by_user.get(member.user_id, [])
        scored_picks = [pick for pick in member_picks if pick.points_earned is not None]
        result = _get_or_create_weekly_result(
            db,
            league_id=league.id,
            week_id=week.id,
            user_id=member.user_id,
        )
        result.total_points = sum(pick.points_earned or 0 for pick in scored_picks)
        result.correct_picks = sum((pick.points_earned or 0) > 0 for pick in scored_picks)
        result.incorrect_picks = sum((pick.points_earned or 0) == 0 for pick in scored_picks)
        result.highest_confidence_win = max(
            (pick.confidence_value for pick in scored_picks if (pick.points_earned or 0) > 0),
            default=0,
        )
        weekly_results.append(result)

    db.flush()
    _assign_weekly_ranks(weekly_results)

    terminal_statuses = {GameStatus.FINAL, GameStatus.CANCELLED}
    if games and all(game.game_status in terminal_statuses for game in games):
        week.status = WeekStatus.COMPLETE

    completed_results = list(
        db.execute(
            select(WeeklyResult)
            .join(NflWeek, WeeklyResult.week_id == NflWeek.id)
            .where(
                WeeklyResult.league_id == league.id,
                NflWeek.season == league.season,
                NflWeek.status == WeekStatus.COMPLETE,
            )
        )
        .scalars()
        .all()
    )
    results_by_user: dict[uuid.UUID, list[WeeklyResult]] = {}
    for weekly_result in completed_results:
        if weekly_result.user_id is not None:
            results_by_user.setdefault(weekly_result.user_id, []).append(weekly_result)

    season_results: list[SeasonResult] = []
    for member in members:
        member_results = results_by_user.get(member.user_id, [])
        season_result = _get_or_create_season_result(
            db,
            league_id=league.id,
            season=league.season,
            user_id=member.user_id,
        )
        season_result.total_points = sum(result.total_points for result in member_results)
        season_result.weekly_wins = sum(result.weekly_rank == 1 for result in member_results)
        season_result.highest_confidence_win = max(
            (result.highest_confidence_win for result in member_results),
            default=0,
        )
        season_result.first_place_finishes = sum(
            result.weekly_rank == 1 for result in member_results
        )
        season_result.second_place_finishes = sum(
            result.weekly_rank == 2 for result in member_results
        )
        season_result.third_place_finishes = sum(
            result.weekly_rank == 3 for result in member_results
        )
        season_results.append(season_result)

    db.flush()
    ordered_season_results = sorted(
        season_results,
        key=lambda result: (
            -result.total_points,
            -result.weekly_wins,
            -result.highest_confidence_win,
            str(result.user_id),
        ),
    )
    for rank, season_result in enumerate(ordered_season_results, start=1):
        season_result.current_rank = rank

    db.commit()
    return sum(game.game_status == GameStatus.FINAL for game in games)
