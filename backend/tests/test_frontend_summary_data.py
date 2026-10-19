"""Local regressions for league metadata and season summary data."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.league import get_league
from app.api.session import bootstrap_session
from app.db.session import Base
from app.models import League, LeagueMember, NflWeek, SeasonResult, User, WeeklyResult
from app.models.enums import LeagueRole, WeekStatus
from app.services import leaderboard_service


def test_commissioner_names_and_completed_season_record() -> None:
    # These queries are portable; a disposable SQLite DB keeps this regression
    # independent of a developer's configured (potentially hosted) database.
    engine = create_engine("sqlite://")
    tables = [
        User.__table__,
        League.__table__,
        LeagueMember.__table__,
        NflWeek.__table__,
        WeeklyResult.__table__,
        SeasonResult.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    try:
        with Session(engine) as db:
            owner = User(google_id="owner", email="owner@example.com", display_name="Alex")
            co_owner = User(google_id="co-owner", email="co@example.com", display_name="Sam")
            member = User(google_id="member", email="member@example.com", display_name="Zoe")
            db.add_all([owner, co_owner, member])
            db.flush()
            league = League(name="Summary test", owner_id=owner.id, season=2026, invite_code="test")
            db.add(league)
            db.flush()
            memberships = [
                LeagueMember(league_id=league.id, user_id=user.id, role=role)
                for user, role in [
                    (owner, LeagueRole.OWNER),
                    (co_owner, LeagueRole.OWNER),
                    (member, LeagueRole.MEMBER),
                ]
            ]
            db.add_all(memberships)
            now = datetime.now(timezone.utc)
            weeks = [
                NflWeek(
                    season=2026,
                    week_number=number,
                    start_date=now - timedelta(days=14),
                    end_date=now - timedelta(days=7),
                    status=status,
                )
                for number, status in [
                    (1, WeekStatus.COMPLETE),
                    (2, WeekStatus.COMPLETE),
                    (3, WeekStatus.REGULAR),
                ]
            ]
            db.add_all(weeks)
            db.flush()
            for week, correct, incorrect in [
                (weeks[0], 10, 6),
                (weeks[1], 12, 4),
                (weeks[2], 3, 1),
            ]:
                db.add(
                    WeeklyResult(
                        league_id=league.id,
                        user_id=owner.id,
                        week_id=week.id,
                        correct_picks=correct,
                        incorrect_picks=incorrect,
                    )
                )
            db.add(
                SeasonResult(league_id=league.id, user_id=owner.id, season=2026, total_points=100)
            )
            db.flush()

            # Regular members receive commissioner names without access to the
            # owner-only members endpoint or other members' private emails.
            bootstrap = bootstrap_session(current_user=member, db=db)
            assert bootstrap["data"]["league"]["commissionerNames"] == ["Alex", "Sam"]
            league_response = get_league(league_member=(league, memberships[2]), db=db)
            assert league_response["data"]["commissionerNames"] == ["Alex", "Sam"]
            standings = leaderboard_service.get_season_standings(db, league=league)
            assert standings.standings[0].correct_picks == 22
            assert standings.standings[0].incorrect_picks == 10
    finally:
        engine.dispose()
