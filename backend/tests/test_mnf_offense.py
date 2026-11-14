"""Monday Night total offense (ESPN) and the guesses-as-a-pick completeness rule."""

import httpx
from sqlalchemy.orm import Session

from app.integrations.espn import fetch_total_offense
from app.models.enums import GameStatus
from app.services import nfl_schedule_service, picks_service
from tests.test_nfl import (
    _auth_header,
    _ensure_current_fixture,
    _make_last_game_monday_night,
    _make_user,
)


def _summary(yards: list[str]) -> httpx.Client:
    body = {
        "boxscore": {
            "teams": [{"statistics": [{"name": "totalYards", "displayValue": y}]} for y in yards]
        }
    }
    return httpx.Client(
        base_url="https://espn.test",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)),
    )


def test_fetch_total_offense_sums_both_teams() -> None:
    assert fetch_total_offense("1", client=_summary(["339", "178"])) == 517


def test_fetch_total_offense_is_none_when_not_reported() -> None:
    assert fetch_total_offense("1", client=_summary(["339"])) is None
    assert fetch_total_offense("1", client=_summary(["--", "178"])) is None


def test_sync_stores_total_offense_on_a_final_monday_game(db_session: Session, monkeypatch) -> None:
    user = _make_user(db_session)
    week, games = _ensure_current_fixture(db_session, user)
    _make_last_game_monday_night(db_session, games)
    monday = games[-1]
    monday.game_status = GameStatus.FINAL
    db_session.commit()
    monkeypatch.setattr(nfl_schedule_service, "fetch_total_offense", lambda _id: 517)

    nfl_schedule_service.sync_monday_night_offense(db_session, week_id=week.id)

    assert monday.total_offense_yards == 517


def test_complete_autosaved_card_needs_monday_night_guesses(client, db_session: Session) -> None:
    user = _make_user(db_session)
    week, games = _ensure_current_fixture(db_session, user)
    _make_last_game_monday_night(db_session, games)
    picks = [
        {"gameId": str(g.id), "team": g.home_team, "confidence": i}
        for i, g in enumerate(games, start=1)
    ]

    client.post(
        "/api/v1/picks", json={"week": week.week_number, "picks": picks}, headers=_auth_header(user)
    )
    assert user.id not in picks_service.list_complete_card_user_ids(db_session, week_id=week.id)

    client.post(
        "/api/v1/picks",
        json={"week": week.week_number, "picks": picks, "mnfGuessPoints": 44, "mnfGuessYards": 700},
        headers=_auth_header(user),
    )
    assert user.id in picks_service.list_complete_card_user_ids(db_session, week_id=week.id)
