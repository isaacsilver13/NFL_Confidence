"""Business logic for validating and saving weekly confidence picks."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.league import League
from app.models.pick import Pick
from app.models.user import User
from app.repositories import nfl_game_repository, pick_repository
from app.schemas.nfl import HistoricalPickRead, HistoricalWeekRead, PickHistoryRead
from app.services import weeks_service


@dataclass(frozen=True)
class PickSubmission:
    game_id: uuid.UUID
    team: str
    confidence: int


def get_user_picks(db: Session, *, user: User) -> list[Pick]:
    week = weeks_service.get_current_week(db)
    return pick_repository.list_by_user_and_week(db, user_id=user.id, week_id=week.id)


def get_user_pick_history(db: Session, *, user: User, league: League) -> PickHistoryRead:
    picks = pick_repository.list_by_user_and_completed_season(
        db, user_id=user.id, league_id=league.id, season=league.season
    )
    picks_by_week: dict[int, list[HistoricalPickRead]] = {}
    for pick in picks:
        game = pick.game
        if pick.points_earned is None:
            outcome = "unscored"
        elif pick.points_earned > 0:
            outcome = "correct"
        else:
            outcome = "incorrect"
        picks_by_week.setdefault(game.week.week_number, []).append(
            HistoricalPickRead(
                id=pick.id,
                game_id=pick.game_id,
                away_team=game.away_team,
                home_team=game.home_team,
                kickoff=game.kickoff_time,
                status=game.game_status.value,
                team=pick.picked_team,
                confidence=pick.confidence_value,
                submitted_at=pick.submitted_at,
                winning_team=game.winning_team,
                is_tie=game.is_tie,
                points_earned=pick.points_earned,
                outcome=outcome,
            )
        )
    return PickHistoryRead(
        season=league.season,
        weeks=[
            HistoricalWeekRead(week_number=week_number, picks=week_picks)
            for week_number, week_picks in picks_by_week.items()
        ],
    )


def create_picks(
    db: Session,
    *,
    user: User,
    week_number: int,
    submissions: list[PickSubmission],
) -> list[Pick]:
    """Create or update confidence picks for the current week.

    Per-game validation: each game in the submission must have kickoff_time > now.
    Confidence values must be unique across all picks (locked + submitted editable).
    Allows partial card submission (subset of week's games).

    Args:
        db: Database session
        user: Current user
        week_number: NFL week number (must match current week)
        submissions: List of game picks to create/update

    Returns:
        List of saved Pick records

    Raises:
        ValidationError: If week doesn't match, game already kicked off, or confidence conflict
    """
    # Serialize a user's submission while allowing different users to proceed.
    pick_repository.lock_user(db, user_id=user.id)

    week = weeks_service.get_current_week(db)
    if week.week_number != week_number:
        raise ValidationError("Picks must be submitted for the current NFL week.")

    games = nfl_game_repository.get_by_week_id(db, week.id)
    game_by_id = {game.id: game for game in games}

    # Validate submission format
    submitted_game_ids = [submission.game_id for submission in submissions]
    submitted_confidences = [submission.confidence for submission in submissions]

    if len(submitted_game_ids) != len(set(submitted_game_ids)):
        raise ValidationError("Each game may only be picked once per submission.")

    if not all(1 <= c <= len(games) for c in submitted_confidences):
        raise ValidationError(f"Confidence values must be between 1 and {len(games)}.")

    # Check week-level lock: ALL picks lock when earliest game (first kickoff) occurs
    now = datetime.now(timezone.utc)
    earliest_kickoff = min((g.kickoff_time for g in games), default=None)

    if earliest_kickoff and earliest_kickoff <= now:
        raise ValidationError("Picks are locked after the earliest game has already kicked off.")

    # Validate all submission games exist in current week
    for submission in submissions:
        game = game_by_id.get(submission.game_id)
        if game is None:
            raise ValidationError(f"Game {submission.game_id} is not in the current week.")

    # Get all existing picks for this user/week
    existing_picks = pick_repository.list_by_user_and_week(db, user_id=user.id, week_id=week.id)
    existing_pick_by_game = {pick.game_id: pick for pick in existing_picks}

    # Validate uniqueness on the final card so updating an existing pick does not
    # treat its previous value as a second pick.
    final_confidences_by_game = {pick.game_id: pick.confidence_value for pick in existing_picks}
    final_confidences_by_game.update(
        {submission.game_id: submission.confidence for submission in submissions}
    )
    all_confidences = list(final_confidences_by_game.values())

    # Check for confidence value conflicts
    if len(all_confidences) != len(set(all_confidences)):
        raise ValidationError(
            "Confidence values must be unique across all your picks (locked and submitted)."
        )

    # Validate team choices
    for submission in submissions:
        game = game_by_id.get(submission.game_id)
        if game is None:
            raise ValidationError("Every pick must reference a current-week game.")
        if submission.team not in {game.home_team, game.away_team}:
            raise ValidationError(f"{submission.team} is not a team in game {game.id}.")

    # Create or update picks
    saved_picks: list[Pick] = []
    for submission in submissions:
        pick = existing_pick_by_game.get(submission.game_id)
        if pick is None:
            pick = pick_repository.create(
                db,
                user_id=user.id,
                game_id=submission.game_id,
                picked_team=submission.team,
                confidence_value=submission.confidence,
            )
        else:
            pick.picked_team = submission.team
            pick.confidence_value = submission.confidence
        saved_picks.append(pick)

    db.commit()
    for pick in saved_picks:
        db.refresh(pick)
    return saved_picks
