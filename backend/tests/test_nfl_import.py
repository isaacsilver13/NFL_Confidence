"""Tests for normalized ESPN NFL schedule imports."""

from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.espn import EspnGame, fetch_schedule
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.services.nfl_schedule_service import import_games


def _espn_game(*, venue_name: str | None = "Arrowhead Stadium") -> EspnGame:
    return EspnGame(
        espn_game_id="espn-import-test-1",
        season=2026,
        week_number=1,
        kickoff_time=datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc),
        away_team="BUF",
        home_team="KC",
        game_status="scheduled",
        away_score=None,
        home_score=None,
        winning_team=None,
        is_tie=False,
        venue_name=venue_name,
        venue_location="Kansas City, MO" if venue_name else None,
        spread_team="KC" if venue_name else None,
        spread=-3.5 if venue_name else None,
    )


def test_import_games_upserts_metadata_and_allows_missing_feed_values(
    db_session: Session,
) -> None:
    assert import_games(db_session, [_espn_game()]) == 1
    assert import_games(db_session, [_espn_game(venue_name=None)]) == 1

    week = db_session.scalar(select(NflWeek).where(NflWeek.season == 2026))
    game = db_session.scalar(select(NflGame).where(NflGame.espn_game_id == "espn-import-test-1"))

    assert week is not None
    assert game is not None
    assert game.week_id == week.id
    assert game.venue_name is None
    assert game.venue_location is None
    assert game.spread_team is None
    assert game.spread is None


def test_fetch_schedule_normalizes_espn_venue_and_favorite_spread() -> None:
    payload = {
        "events": [
            {
                "id": "espn-event-1",
                "date": "2026-09-10T00:00:00Z",
                "competitions": [
                    {
                        "competitors": [
                            {"homeAway": "away", "team": {"abbreviation": "BUF"}},
                            {"homeAway": "home", "team": {"abbreviation": "KC"}},
                        ],
                        "venue": {
                            "fullName": "GEHA Field at Arrowhead Stadium",
                            "address": {"city": "Kansas City", "state": "MO"},
                        },
                        "odds": [{"details": "KC -3.5"}],
                    }
                ],
            }
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    with httpx.Client(transport=transport, base_url="https://example.test") as client:
        games = fetch_schedule(2026, 1, client=client)

    assert len(games) == 1
    assert games[0].venue_name == "GEHA Field at Arrowhead Stadium"
    assert games[0].venue_location == "Kansas City, MO"
    assert games[0].spread_team == "KC"
    assert games[0].spread == -3.5
