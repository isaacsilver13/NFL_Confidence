"""ESPN scoreboard client and normalized NFL game payloads."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from app.core.config import get_settings

_SPREAD_DETAILS = re.compile(r"(?P<team>[A-Za-z0-9]{2,4})\s+(?P<spread>[+-]?\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class EspnGame:
    espn_game_id: str
    season: int
    week_number: int
    kickoff_time: datetime
    away_team: str
    home_team: str
    game_status: str
    away_score: int | None
    home_score: int | None
    winning_team: str | None
    is_tie: bool
    venue_name: str | None
    venue_location: str | None
    spread_team: str | None
    spread: float | None


def _team_code(competitor: dict[str, Any]) -> str | None:
    team = competitor.get("team", {})
    return team.get("abbreviation") or team.get("shortDisplayName")


def _score(competitor: dict[str, Any]) -> int | None:
    value = competitor.get("score")
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _status(event: dict[str, Any], competition: dict[str, Any]) -> str:
    status = competition.get("status") or event.get("status") or {}
    status_type = status.get("type") or {}
    state = status_type.get("state")
    name = status_type.get("name", "").lower()
    if state == "post" or status_type.get("completed") or name in {"status_final", "final"}:
        return "final"
    if state == "in" or name in {"status_in_progress", "in_progress"}:
        return "live"
    if "postpon" in name:
        return "postponed"
    if "cancel" in name:
        return "cancelled"
    return "scheduled"


def _venue(competition: dict[str, Any]) -> tuple[str | None, str | None]:
    venue = competition.get("venue") or {}
    name = venue.get("fullName")
    address = venue.get("address") or {}
    city = address.get("city")
    state = address.get("state")
    location = ", ".join(part for part in (city, state) if part)
    return name, location or None


def _spread(
    competition: dict[str, Any], away_team: str, home_team: str
) -> tuple[str | None, float | None]:
    for odds in competition.get("odds") or []:
        details = odds.get("details")
        if isinstance(details, str):
            match = _SPREAD_DETAILS.search(details)
            if match and match.group("team") in {away_team, home_team}:
                return match.group("team"), float(match.group("spread"))

        for key, team in (("awayTeamOdds", away_team), ("homeTeamOdds", home_team)):
            team_odds = odds.get(key) or {}
            if team_odds.get("favorite") and team_odds.get("spread") is not None:
                try:
                    return team, float(team_odds["spread"])
                except (TypeError, ValueError):
                    continue
    return None, None


def normalize_event(event: dict[str, Any], *, season: int, week_number: int) -> EspnGame:
    competition = (event.get("competitions") or [{}])[0]
    competitors = competition.get("competitors") or []
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    if away is None or home is None:
        raise ValueError(f"ESPN event {event.get('id', '<unknown>')} is missing home or away team")

    away_team = _team_code(away)
    home_team = _team_code(home)
    if away_team is None or home_team is None:
        raise ValueError(f"ESPN event {event.get('id', '<unknown>')} has an invalid team")
    away_score = _score(away)
    home_score = _score(home)
    is_tie = away_score is not None and home_score is not None and away_score == home_score
    winning_team = None
    if not is_tie:
        winner = next((item for item in competitors if item.get("winner")), None)
        winning_team = _team_code(winner) if winner else None
        if winning_team is None and away_score is not None and home_score is not None:
            winning_team = away_team if away_score > home_score else home_team
    spread_team, spread = _spread(competition, away_team, home_team)
    venue_name, venue_location = _venue(competition)
    return EspnGame(
        espn_game_id=str(event["id"]),
        season=season,
        week_number=week_number,
        kickoff_time=datetime.fromisoformat(event["date"].replace("Z", "+00:00")),
        away_team=away_team,
        home_team=home_team,
        game_status=_status(event, competition),
        away_score=away_score,
        home_score=home_score,
        winning_team=winning_team,
        is_tie=is_tie,
        venue_name=venue_name,
        venue_location=venue_location,
        spread_team=spread_team,
        spread=spread,
    )


def fetch_schedule(
    season: int,
    week_number: int,
    *,
    client: httpx.Client | None = None,
) -> list[EspnGame]:
    settings = get_settings()
    params = {"dates": str(season), "seasontype": "2", "week": str(week_number)}
    owns_client = client is None
    request_client = client or httpx.Client(
        base_url=settings.nfl_api_base_url,
        timeout=settings.nfl_api_timeout_seconds,
    )
    try:
        response = request_client.get("/scoreboard", params=params)
        response.raise_for_status()
        payload = response.json()
        return [
            normalize_event(event, season=season, week_number=week_number)
            for event in payload.get("events", [])
        ]
    finally:
        if owns_client:
            request_client.close()
