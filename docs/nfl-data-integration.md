# NFL Data Integration

## Source

NFL schedule data comes from the ESPN scoreboard API:

```text
https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard
```

The backend client sends `dates`, `seasontype=2`, and `week` query parameters. No API key is required. The base URL and request timeout are configured through the backend settings (`NFL_API_BASE_URL` and `NFL_API_TIMEOUT_SECONDS`).

## Normalization

`app.integrations.espn.normalize_event()` converts an ESPN event into the internal `EspnGame` payload:

| ESPN data | Internal value |
| --- | --- |
| Event `id` | `espn_game_id` |
| Event `date` | `kickoff_time` |
| Home and away competitors | `home_team`, `away_team` |
| Competition status | `game_status` (`scheduled`, `live`, `final`, `postponed`, or `cancelled`) |
| Competitor scores | `home_score`, `away_score` |
| Winner flag or final scores | `winning_team` |
| Equal final scores | `is_tie` |
| Status `displayClock` | `clock` |
| Status `period` | `period` |
| Competition venue | `venue_name`, `venue_location` |
| Competition odds | `spread_team`, `spread` |

Events without both valid home and away teams are rejected. Missing scores, venue information, spread information, `clock`, or `period` remain nullable (e.g. for scheduled games, or whenever ESPN omits those fields).

## Import behavior

`app.services.nfl_schedule_service.import_games()` groups normalized games by season and week, creates a week when needed, and upserts games by `espn_game_id`. Existing records receive refreshed kickoff, teams, venue, odds, status, scores, winner, tie state, clock, period, and `last_synced` values. Re-running an import is therefore safe for the same schedule window.

The explicit local/import command is:

```powershell
cd backend
.venv\Scripts\python.exe -m scripts.import_nfl_schedule --season 2026 --week 1
```

The command requires the database configured by `DATABASE_URL` and prints the number of imported games. It is intended for a controlled schedule refresh and does not yet run on a timer.

## Local development

Seed the active league with real weeks and fake players (requires ESPN API access):

```powershell
cd backend
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m scripts.seed_test_data            # weeks 1-5 by default
.venv\Scripts\python.exe -m scripts.seed_test_data --weeks 8  # or more weeks
```

The seed imports weeks 1 through `--weeks` from ESPN through the same `import_games` path the scheduler uses, then gives five fake demo users a deterministic, fully-slotted set of picks for each week and scores it. It also removes games left by the old `local-test-*` fixture, which used to add extra confidence slots to real weeks. On the dev Fly app, run it with `fly ssh console --app nfl-confidence-api-dev -C "python -m scripts.seed_test_data"`. The leaderboard fixture can be added separately with:

```powershell
.venv\Scripts\python.exe -m scripts.seed_leaderboard_data --season 2026
```

## Boundaries and follow-up work

This integration provides normalization, persistence, read APIs, and an explicit import job. It does not provide automatic polling, score recalculation, result aggregation, or notifications. Those responsibilities belong to the background-job and scoring phases. Redis caching and retry/backoff should be added with the polling workflow rather than introduced into this initial import path.
