"""Tests for current NFL weeks, games, and confidence picks."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.models import League, LeagueMember, NflGame, NflWeek, Pick, User
from app.models.enums import GameStatus, LeagueRole, WeekStatus
from app.repositories import league_repository, nfl_game_repository, nfl_week_repository
from app.services import league_service, picks_service


def _make_user(db_session: Session) -> User:
    suffix = uuid.uuid4().hex
    user = User(
        google_id=f"nfl-test-{suffix}",
        email=f"nfl-test-{suffix}@example.com",
        display_name="NFL Test User",
    )
    db_session.add(user)
    db_session.flush()
    return user


def _auth_header(user: User) -> dict[str, str]:
    access_token, _ = create_access_token(user.id)
    return {"Authorization": f"Bearer {access_token}"}


def _ensure_current_fixture(db_session: Session, user: User) -> tuple[NflWeek, list[NflGame]]:
    league = league_repository.get_active(db_session)
    if league is None:
        league = league_service.create_league(
            db_session, owner=user, name="NFL API Test League", season=2026
        )

    now = datetime.now(timezone.utc)
    week = nfl_week_repository.get_current(db_session, season=league.season, at=now)
    if week is None:
        week = nfl_week_repository.get_by_season_and_week(
            db_session, season=league.season, week_number=1
        )
        if week is None:
            week = nfl_week_repository.create(
                db_session,
                season=league.season,
                week_number=1,
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=7),
            )
        else:
            week.start_date = now - timedelta(days=1)
            week.end_date = now + timedelta(days=7)
            week.status = WeekStatus.REGULAR

    games = nfl_game_repository.get_by_week_id(db_session, week.id)
    if not games:
        games = [
            nfl_game_repository.create(
                db_session,
                week_id=week.id,
                espn_game_id=f"nfl-api-test-{uuid.uuid4().hex}-{index}",
                kickoff_time=now + timedelta(days=index),
                home_team=home_team,
                away_team=away_team,
            )
            for index, (away_team, home_team) in enumerate((("BUF", "KC"), ("GB", "CHI")), start=1)
        ]
    db_session.commit()
    return week, games


def test_current_nfl_endpoints_and_pick_update(client, db_session: Session) -> None:
    user = _make_user(db_session)
    week, games = _ensure_current_fixture(db_session, user)
    headers = _auth_header(user)

    week_response = client.get("/api/v1/weeks/current", headers=headers)
    games_response = client.get("/api/v1/games/current", headers=headers)

    assert week_response.status_code == 200
    assert week_response.json()["data"]["weekNumber"] == week.week_number
    assert games_response.status_code == 200
    returned_games = games_response.json()["data"]
    assert [game["id"] for game in returned_games] == [str(game.id) for game in games]
    assert returned_games[0]["venueName"] is None
    assert returned_games[0]["spreadTeam"] is None
    assert returned_games[0]["spread"] is None
    assert returned_games[0]["kickoff"] <= returned_games[-1]["kickoff"]

    pick_payloads = [
        {"gameId": str(game.id), "team": game.home_team, "confidence": index}
        for index, game in enumerate(games, start=1)
    ]
    payload = {"week": week.week_number, "picks": pick_payloads}
    save_response = client.post("/api/v1/picks", json=payload, headers=headers)
    assert save_response.status_code == 200
    assert len(save_response.json()["data"]) == len(games)

    pick_payloads[0]["team"] = games[0].away_team
    update_response = client.post("/api/v1/picks", json=payload, headers=headers)
    assert update_response.status_code == 200
    assert db_session.query(Pick).filter_by(user_id=user.id).count() == len(games)


def test_picks_reject_duplicate_confidence_values(client, db_session: Session) -> None:
    user = _make_user(db_session)
    _, games = _ensure_current_fixture(db_session, user)
    headers = _auth_header(user)
    response = client.post(
        "/api/v1/picks",
        json={
            "week": 1,
            "picks": [
                {"gameId": str(game.id), "team": game.home_team, "confidence": 1} for game in games
            ],
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_pick_history_is_private_and_contains_outcomes(db_session: Session) -> None:
    suffix = uuid.uuid4().hex
    owner = _make_user(db_session)
    other_user = _make_user(db_session)
    league = League(
        name=f"History {suffix[:8]}",
        owner_id=owner.id,
        season=2000 + int(suffix[:4], 16) % 100,
        invite_code=f"history-{suffix[:24]}",
        is_active=False,
    )
    db_session.add(league)
    db_session.flush()
    db_session.add_all(
        [
            LeagueMember(league_id=league.id, user_id=owner.id, role=LeagueRole.OWNER),
            LeagueMember(league_id=league.id, user_id=other_user.id, role=LeagueRole.MEMBER),
        ]
    )
    complete_week = NflWeek(
        season=league.season,
        week_number=2,
        start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 9, 7, tzinfo=timezone.utc),
        status=WeekStatus.COMPLETE,
    )
    open_week = NflWeek(
        season=league.season,
        week_number=3,
        start_date=datetime(2026, 9, 8, tzinfo=timezone.utc),
        end_date=datetime(2026, 9, 14, tzinfo=timezone.utc),
        status=WeekStatus.REGULAR,
    )
    db_session.add_all([complete_week, open_week])
    db_session.flush()
    games = [
        NflGame(
            week_id=complete_week.id,
            espn_game_id=f"history-{suffix}-{index}",
            kickoff_time=datetime(2026, 9, 2 + index, tzinfo=timezone.utc),
            away_team=away,
            home_team=home,
            winning_team=home if index == 0 else None,
            game_status=GameStatus.FINAL if index == 0 else GameStatus.SCHEDULED,
            is_tie=index == 1,
        )
        for index, (away, home) in enumerate((("BUF", "KC"), ("GB", "CHI")))
    ]
    open_game = NflGame(
        week_id=open_week.id,
        espn_game_id=f"history-open-{suffix}",
        kickoff_time=datetime(2026, 9, 10, tzinfo=timezone.utc),
        away_team="DAL",
        home_team="NYG",
        game_status=GameStatus.FINAL,
    )
    db_session.add_all([*games, open_game])
    db_session.flush()
    db_session.add_all(
        [
            Pick(
                user_id=owner.id,
                game_id=games[0].id,
                picked_team="KC",
                confidence_value=2,
                points_earned=2,
            ),
            Pick(
                user_id=owner.id,
                game_id=games[1].id,
                picked_team="GB",
                confidence_value=1,
                points_earned=None,
            ),
            Pick(
                user_id=owner.id,
                game_id=open_game.id,
                picked_team="DAL",
                confidence_value=1,
                points_earned=None,
            ),
            Pick(
                user_id=other_user.id,
                game_id=games[0].id,
                picked_team="BUF",
                confidence_value=2,
                points_earned=0,
            ),
        ]
    )
    db_session.flush()

    result = picks_service.get_user_pick_history(db_session, user=owner, league=league)

    assert [week.week_number for week in result.weeks] == [2]
    assert [(pick.team, pick.outcome) for pick in result.weeks[0].picks] == [
        ("KC", "correct"),
        ("GB", "unscored"),
    ]
