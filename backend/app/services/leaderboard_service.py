"""Leaderboard queries and trend aggregation."""

import uuid
from collections import defaultdict

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import WeekStatus
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.models.pick import Pick
from app.models.weekly_result import WeeklyResult
from app.repositories import (
    league_member_repository,
    season_result_repository,
    weekly_result_repository,
)
from app.schemas.leaderboard import (
    GamePickBreakdownRead,
    LeaderboardMemberRead,
    PickBreakdownRead,
    SeasonStandingsRead,
    TeamPickCountRead,
    WeekLabelRead,
    WeeklyLeaderboardRead,
    WeeklyPickBreakdownRead,
)


def _ranked_members(results: list, *, season: bool = False) -> list[LeaderboardMemberRead]:
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
            result.user.display_name,
        ),
    )
    return [
        LeaderboardMemberRead(
            rank=rank,
            member_id=result.user_id,
            member_name=result.user.display_name,
            total_points=result.total_points or 0,
            correct_picks=getattr(result, "correct_picks", 0) or 0,
            incorrect_picks=getattr(result, "incorrect_picks", 0) or 0,
            weekly_wins=getattr(result, "weekly_wins", 0) or 0,
            first_place_finishes=getattr(result, "first_place_finishes", 0) or 0,
            second_place_finishes=getattr(result, "second_place_finishes", 0) or 0,
            third_place_finishes=getattr(result, "third_place_finishes", 0) or 0,
        )
        for rank, result in enumerate(ordered, start=1)
    ]


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


def get_weekly_leaderboard(
    db: Session, *, league: League, week_number: int | None = None
) -> WeeklyLeaderboardRead:
    week = _get_week(db, league, week_number)
    results = weekly_result_repository.list_by_league_and_week(
        db, league_id=league.id, week_id=week.id
    )
    standings = _ranked_members(results)
    if not standings:
        raise NotFoundError(f"Week {week.week_number} has no leaderboard data.")
    return WeeklyLeaderboardRead(
        week=WeekLabelRead(week_number=week.week_number, season_number=week.season),
        standings=standings,
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
    for week_number, game_id, away_team, home_team in game_rows:
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
