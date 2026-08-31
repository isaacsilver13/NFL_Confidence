"""Import normalized ESPN schedule data into NFL game records."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.espn import EspnGame
from app.models.enums import GameStatus, WeekStatus
from app.repositories import nfl_game_repository, nfl_week_repository

_STATUS_MAP = {status.value: status for status in GameStatus}


def import_games(db: Session, games: list[EspnGame]) -> int:
    if not games:
        return 0
    grouped: dict[tuple[int, int], list[EspnGame]] = {}
    for game in games:
        grouped.setdefault((game.season, game.week_number), []).append(game)

    imported = 0
    for (season, week_number), week_games in grouped.items():
        start_date = min(game.kickoff_time for game in week_games)
        end_date = max(game.kickoff_time for game in week_games)
        week = nfl_week_repository.get_by_season_and_week(
            db, season=season, week_number=week_number
        )
        if week is None:
            week = nfl_week_repository.create(
                db,
                season=season,
                week_number=week_number,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            week.start_date = min(week.start_date, start_date)
            week.end_date = max(week.end_date, end_date)
            if week.status == WeekStatus.PRESEASON:
                week.status = WeekStatus.REGULAR

        for imported_game in week_games:
            db_game = nfl_game_repository.get_by_espn_game_id(db, imported_game.espn_game_id)
            if db_game is None:
                db_game = nfl_game_repository.create(
                    db,
                    espn_game_id=imported_game.espn_game_id,
                    week_id=week.id,
                    kickoff_time=imported_game.kickoff_time,
                    home_team=imported_game.home_team,
                    away_team=imported_game.away_team,
                )
            db_game.week_id = week.id
            db_game.kickoff_time = imported_game.kickoff_time
            db_game.home_team = imported_game.home_team
            db_game.away_team = imported_game.away_team
            db_game.venue_name = imported_game.venue_name
            db_game.venue_location = imported_game.venue_location
            db_game.spread_team = imported_game.spread_team
            db_game.spread = imported_game.spread
            db_game.game_status = _STATUS_MAP[imported_game.game_status]
            db_game.home_score = imported_game.home_score
            db_game.away_score = imported_game.away_score
            db_game.winning_team = imported_game.winning_team
            db_game.is_tie = imported_game.is_tie
            db_game.last_synced = datetime.now(timezone.utc)
            imported += 1
    db.commit()
    return imported


def import_schedule(
    db: Session,
    *,
    season: int,
    week_number: int,
    games: list[EspnGame],
) -> int:
    selected_games = [
        game for game in games if game.season == season and game.week_number == week_number
    ]
    return import_games(db, selected_games)
