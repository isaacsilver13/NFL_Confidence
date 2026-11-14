"""Recompute confidence-pool scores from the imported NFL game outcomes."""

import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.enums import GameStatus, WeekStatus
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.mnf_guess import MnfGuess
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


# Sorts after every real guess distance, so members without a guess rank last in the tie-break.
NO_GUESS_DISTANCE = (10**9, 10**9)


def monday_night_game(games: list[NflGame]) -> NflGame | None:
    """The week's last Monday game (the late one in a doubleheader), if there is one."""
    tz = ZoneInfo(get_settings().scheduler_timezone)
    mondays = [g for g in games if g.kickoff_time.astimezone(tz).weekday() == 0]
    return max(mondays, key=lambda g: g.kickoff_time) if mondays else None


def mnf_distances(
    db: Session, *, week_id: uuid.UUID, games: list[NflGame] | None = None
) -> dict[uuid.UUID, tuple[int, int]]:
    """Each member's (points, yards) distance from their Monday Night guesses to the real totals.

    Empty until that game is final. Until total offense is fetched, yards distance is 0 for
    everyone who guessed, so only the points distance separates them.
    """
    if games is None:
        games = list(db.execute(select(NflGame).where(NflGame.week_id == week_id)).scalars())
    game = monday_night_game(games)
    if (
        game is None
        or game.game_status != GameStatus.FINAL
        or game.home_score is None
        or game.away_score is None
    ):
        return {}
    actual_points = game.home_score + game.away_score
    guesses = db.execute(select(MnfGuess).where(MnfGuess.week_id == week_id)).scalars()
    return {
        guess.user_id: (
            abs(guess.points - actual_points),
            abs(guess.yards - game.total_offense_yards) if game.total_offense_yards else 0,
        )
        for guess in guesses
    }


def _rank_key(result: WeeklyResult) -> tuple[int, int, int, str]:
    return (
        -result.total_points,
        -result.correct_picks,
        result.highest_confidence_loss,
        str(result.user_id),
    )


def _assign_weekly_ranks(
    results: list[WeeklyResult], distances: dict[uuid.UUID, tuple[int, int]] | None = None
) -> None:
    """Rank by points, correct picks, lowest missed confidence, then Monday Night guess distance
    (points, then yards)."""
    distances = distances or {}

    def key(result: WeeklyResult) -> tuple[int, int, int, tuple[int, int]]:
        points, correct, loss, _ = _rank_key(result)
        return (
            points,
            correct,
            loss,
            (
                distances.get(result.user_id, NO_GUESS_DISTANCE)
                if result.user_id
                else NO_GUESS_DISTANCE
            ),
        )

    ordered = sorted(results, key=lambda r: (key(r), str(r.user_id)))
    previous_key: tuple[int, int, int, tuple[int, int]] | None = None
    previous_rank = 0
    for position, result in enumerate(ordered, start=1):
        if key(result) != previous_key:
            previous_rank = position
            previous_key = key(result)
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
        if pick.voided_at is not None:
            pick.points_earned = None
        elif pick.game.game_status == GameStatus.FINAL:
            pick.points_earned = _pick_points(pick)
        picks_by_user.setdefault(pick.user_id, []).append(pick)

    weekly_results: list[WeeklyResult] = []
    for member in members:
        member_picks = picks_by_user.get(member.user_id, [])
        scored_picks = [
            pick
            for pick in member_picks
            if pick.points_earned is not None and pick.voided_at is None
        ]
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
        result.highest_confidence_loss = max(
            (pick.confidence_value for pick in scored_picks if (pick.points_earned or 0) == 0),
            default=0,
        )
        weekly_results.append(result)

    db.flush()
    _assign_weekly_ranks(weekly_results, mnf_distances(db, week_id=week.id, games=games))

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
        # Both metrics currently count rank-one weeks; they remain separate for reporting,
        # and could diverge if weekly-win and placement tie policies change independently.
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
