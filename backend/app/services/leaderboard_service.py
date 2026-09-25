"""Leaderboard queries and trend aggregation."""

import uuid
from collections import defaultdict

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import GameStatus, WeekStatus
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.models.weekly_result import WeeklyResult
from app.repositories import (
    league_member_repository,
    league_repository,
    nfl_game_repository,
    pick_repository,
    season_result_repository,
    week_submission_repository,
    weekly_result_repository,
)
from app.schemas.leaderboard import (
    GameLabelRead,
    GamePickBreakdownRead,
    GamePickDetailRead,
    GamePicksRead,
    LeaderboardMemberRead,
    MemberGamePickRead,
    PickBreakdownRead,
    SeasonStandingsRead,
    TeamPickCountRead,
    WeekLabelRead,
    WeeklyLeaderboardRead,
    WeeklyPickBreakdownRead,
)


def _weekly_payout_cents(*, rank: int, member_count: int) -> int:
    pool_cents = member_count * 1000
    if rank == 1:
        reserved = (200 if member_count >= 2 else 0) + (100 if member_count >= 3 else 0)
        return max(pool_cents - reserved, 0)
    if rank == 2 and member_count >= 2:
        return 200
    if rank == 3 and member_count >= 3:
        return 100
    return 0


def _points_remaining_by_user(db: Session, *, week_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """Sum confidence values on each user's not-yet-final, non-voided picks for a week."""
    unresolved_statuses = {GameStatus.SCHEDULED, GameStatus.LIVE, GameStatus.POSTPONED}
    rows = db.execute(
        select(Pick.user_id, func.sum(Pick.confidence_value))
        .join(NflGame, Pick.game_id == NflGame.id)
        .where(
            NflGame.week_id == week_id,
            NflGame.game_status.in_(unresolved_statuses),
            Pick.voided_at.is_(None),
        )
        .group_by(Pick.user_id)
    ).all()
    return {user_id: int(total) for user_id, total in rows}


def _ranked_members(
    results: list,
    *,
    season: bool = False,
    member_count: int = 0,
    points_remaining_by_user: dict[uuid.UUID, int] | None = None,
    last_two_game_picks_by_user: dict[uuid.UUID, list[MemberGamePickRead]] | None = None,
) -> list[LeaderboardMemberRead]:
    points_remaining_by_user = points_remaining_by_user or {}
    last_two_game_picks_by_user = last_two_game_picks_by_user or {}
    usable_results = [result for result in results if result.user is not None]
    ordered = sorted(
        usable_results,
        key=lambda result: (
            -(result.total_points or 0),
            (
                -(getattr(result, "weekly_wins", 0) or 0)
                if season
                else -(getattr(result, "correct_picks", 0) or 0)
            ),
            -(getattr(result, "highest_confidence_win", 0) or 0),
            result.user.display_name,
        ),
    )
    members: list[LeaderboardMemberRead] = []
    previous_key: tuple[int, int, int] | None = None
    previous_rank = 0
    for position, result in enumerate(ordered, start=1):
        current_key = (
            result.total_points or 0,
            (
                getattr(result, "weekly_wins", 0) or 0
                if season
                else getattr(result, "correct_picks", 0) or 0
            ),
            getattr(result, "highest_confidence_win", 0) or 0,
        )
        if current_key != previous_key:
            previous_rank = position
            previous_key = current_key
        members.append(
            LeaderboardMemberRead(
                rank=previous_rank,
                member_id=result.user_id,
                member_name=result.user.display_name,
                total_points=result.total_points or 0,
                correct_picks=getattr(result, "correct_picks", 0) or 0,
                incorrect_picks=getattr(result, "incorrect_picks", 0) or 0,
                weekly_wins=getattr(result, "weekly_wins", 0) or 0,
                first_place_finishes=getattr(result, "first_place_finishes", 0) or 0,
                second_place_finishes=getattr(result, "second_place_finishes", 0) or 0,
                third_place_finishes=getattr(result, "third_place_finishes", 0) or 0,
                payout_cents=(
                    _weekly_payout_cents(rank=previous_rank, member_count=member_count)
                    if not season
                    else 0
                ),
                points_remaining=points_remaining_by_user.get(result.user_id, 0),
                last_two_game_picks=last_two_game_picks_by_user.get(result.user_id, []),
            )
        )
    return members


def _get_week(db: Session, league: League, week_number: int | None) -> NflWeek:
    if week_number is not None:
        week = db.execute(
            select(NflWeek).where(
                NflWeek.season == league.season,
                NflWeek.week_number == week_number,
            )
        ).scalar_one_or_none()
    else:
        week = (
            db.execute(
                select(NflWeek)
                .join(WeeklyResult)
                .where(
                    NflWeek.season == league.season,
                    WeeklyResult.league_id == league.id,
                )
                .order_by(desc(NflWeek.week_number))
            )
            .scalars()
            .first()
        )
    if week is None:
        label = f"Week {week_number}" if week_number is not None else "A completed week"
        raise NotFoundError(f"{label} has no leaderboard data.")
    return week


def _last_two_games_picks(
    db: Session, *, week_id: uuid.UUID, user_ids: set[uuid.UUID]
) -> tuple[list, dict[uuid.UUID, list[MemberGamePickRead]]]:
    """The week's last two games by kickoff (e.g. SNF/MNF) and each member's pick for
    them. Safe to reveal alongside the leaderboard -- any week with leaderboard data
    has already locked (see get_weekly_leaderboard)."""
    games = nfl_game_repository.get_by_week_id(db, week_id)
    last_two_games = sorted(games, key=lambda game: game.kickoff_time)[-2:]
    last_two_game_ids = {game.id for game in last_two_games}
    if not last_two_game_ids:
        return last_two_games, {}

    picks = pick_repository.list_by_week_and_users(db, week_id=week_id, user_ids=user_ids)
    picks_by_user_game = {
        (pick.user_id, pick.game_id): pick
        for pick in picks
        if pick.voided_at is None and pick.game_id in last_two_game_ids
    }
    picks_by_user: dict[uuid.UUID, list[MemberGamePickRead]] = {}
    for user_id in user_ids:
        picks_by_user[user_id] = [
            (
                MemberGamePickRead(
                    game_id=game.id,
                    team=pick.picked_team,
                    confidence=pick.confidence_value,
                )
                if (pick := picks_by_user_game.get((user_id, game.id))) is not None
                else MemberGamePickRead(game_id=game.id)
            )
            for game in last_two_games
        ]
    return last_two_games, picks_by_user


def get_weekly_leaderboard(
    db: Session, *, league: League, week_number: int | None = None
) -> WeeklyLeaderboardRead:
    week = _get_week(db, league, week_number)
    results = weekly_result_repository.list_by_league_and_week(
        db, league_id=league.id, week_id=week.id
    )
    submitted_user_ids = week_submission_repository.list_user_ids_for_week(db, week_id=week.id)
    results = [result for result in results if result.user_id in submitted_user_ids]
    last_two_games, last_two_game_picks_by_user = _last_two_games_picks(
        db,
        week_id=week.id,
        user_ids={result.user_id for result in results if result.user_id is not None},
    )
    standings = _ranked_members(
        results,
        member_count=league_repository.count_members(db, league.id),
        points_remaining_by_user=_points_remaining_by_user(db, week_id=week.id),
        last_two_game_picks_by_user=last_two_game_picks_by_user,
    )
    if not standings:
        raise NotFoundError(f"Week {week.week_number} has no leaderboard data.")
    return WeeklyLeaderboardRead(
        week=WeekLabelRead(week_number=week.week_number, season_number=week.season),
        standings=standings,
        last_two_games=[
            GameLabelRead(game_id=game.id, away_team=game.away_team, home_team=game.home_team)
            for game in last_two_games
        ],
    )


def get_season_standings(
    db: Session, *, league: League, season: int | None = None
) -> SeasonStandingsRead:
    target_season = season if season is not None else league.season
    results = season_result_repository.list_by_league_and_season(
        db, league_id=league.id, season=target_season
    )
    standings = _ranked_members(results, season=True)
    if not standings:
        raise NotFoundError(f"Season {target_season} has no standings data.")
    return SeasonStandingsRead(season=target_season, standings=standings)


def get_pick_breakdown(db: Session, *, league: League, viewer_id: uuid.UUID) -> PickBreakdownRead:
    membership = league_member_repository.get_by_league_and_user(db, league.id, viewer_id)
    if membership is None:
        raise NotFoundError("You are not a member of the active league.")

    completed_weeks = list(
        db.execute(
            select(NflWeek)
            .where(NflWeek.season == league.season, NflWeek.status == WeekStatus.COMPLETE)
            .order_by(NflWeek.week_number)
        ).scalars()
    )
    game_rows = db.execute(
        select(
            NflWeek.week_number,
            NflGame.id,
            NflGame.away_team,
            NflGame.home_team,
            NflGame.away_record,
            NflGame.home_record,
        )
        .select_from(NflGame)
        .join(NflWeek, NflGame.week_id == NflWeek.id)
        .where(
            NflWeek.season == league.season,
            NflWeek.status == WeekStatus.COMPLETE,
        )
        .order_by(NflWeek.week_number, NflGame.kickoff_time)
    ).all()
    team_rows = db.execute(
        select(
            NflWeek.week_number,
            NflGame.id,
            Pick.picked_team,
            func.count(distinct(Pick.user_id)),
        )
        .select_from(Pick)
        .join(NflGame, Pick.game_id == NflGame.id)
        .join(NflWeek, NflGame.week_id == NflWeek.id)
        .join(LeagueMember, LeagueMember.user_id == Pick.user_id)
        .where(
            LeagueMember.league_id == league.id,
            NflWeek.season == league.season,
            NflWeek.status == WeekStatus.COMPLETE,
        )
        .group_by(NflWeek.week_number, NflGame.id, Pick.picked_team)
        .order_by(NflWeek.week_number, NflGame.id, Pick.picked_team)
    ).all()
    confidence_rows = db.execute(
        select(NflWeek.week_number, NflGame.id, Pick.confidence_value)
        .select_from(Pick)
        .join(NflGame, Pick.game_id == NflGame.id)
        .join(NflWeek, NflGame.week_id == NflWeek.id)
        .join(LeagueMember, LeagueMember.user_id == Pick.user_id)
        .where(
            LeagueMember.league_id == league.id,
            NflWeek.season == league.season,
            NflWeek.status == WeekStatus.COMPLETE,
        )
        .order_by(NflWeek.week_number, NflGame.id, Pick.confidence_value)
    ).all()

    team_counts_by_game: dict[uuid.UUID, dict[str, int]] = defaultdict(dict)
    for _, game_id, team, user_count in team_rows:
        team_counts_by_game[game_id][team] = user_count
    confidences_by_game: dict[uuid.UUID, list[int]] = defaultdict(list)
    for _, game_id, confidence in confidence_rows:
        confidences_by_game[game_id].append(confidence)

    games_by_week: dict[int, list[GamePickBreakdownRead]] = defaultdict(list)
    for week_number, game_id, away_team, home_team, away_record, home_record in game_rows:
        confidences = sorted(confidences_by_game[game_id])
        median_confidence: float | None = None
        if confidences:
            middle = len(confidences) // 2
            if len(confidences) % 2:
                median_confidence = float(confidences[middle])
            else:
                median_confidence = (confidences[middle - 1] + confidences[middle]) / 2
        counts = team_counts_by_game[game_id]
        games_by_week[week_number].append(
            GamePickBreakdownRead(
                game_id=game_id,
                away_team=away_team,
                home_team=home_team,
                away_record=away_record,
                home_record=home_record,
                median_confidence=median_confidence,
                team_counts=[
                    TeamPickCountRead(team=away_team, user_count=counts.get(away_team, 0)),
                    TeamPickCountRead(team=home_team, user_count=counts.get(home_team, 0)),
                ],
            )
        )

    return PickBreakdownRead(
        season=league.season,
        weeks=[
            WeeklyPickBreakdownRead(
                week_number=week.week_number,
                games=games_by_week[week.week_number],
            )
            for week in completed_weeks
        ],
    )


def get_game_picks(
    db: Session, *, league: League, viewer_id: uuid.UUID, game_id: uuid.UUID
) -> GamePicksRead:
    """Every league member's pick for one completed-week game, for the leaderboard's
    per-game "View Picks" modal."""
    membership = league_member_repository.get_by_league_and_user(db, league.id, viewer_id)
    if membership is None:
        raise NotFoundError("You are not a member of the active league.")

    game = db.execute(
        select(NflGame)
        .join(NflWeek, NflGame.week_id == NflWeek.id)
        .where(
            NflGame.id == game_id,
            NflWeek.season == league.season,
            NflWeek.status == WeekStatus.COMPLETE,
        )
    ).scalar_one_or_none()
    if game is None:
        raise NotFoundError("This game's picks aren't available yet.")

    rows = db.execute(
        select(Pick, LeagueMember)
        .join(LeagueMember, LeagueMember.user_id == Pick.user_id)
        .where(
            Pick.game_id == game.id,
            LeagueMember.league_id == league.id,
            Pick.voided_at.is_(None),
        )
        .order_by(Pick.confidence_value.desc())
    ).all()

    return GamePicksRead(
        game_id=game.id,
        away_team=game.away_team,
        home_team=game.home_team,
        picks=[
            GamePickDetailRead(
                member_name=member.user.display_name,
                team=pick.picked_team,
                confidence=pick.confidence_value,
                is_correct=(pick.points_earned > 0) if pick.points_earned is not None else None,
            )
            for pick, member in rows
        ],
    )
