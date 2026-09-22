"""Builds the weekly confidence report emailed to commissioners.

Renders a self-contained HTML email body (inline styles, system fonts, one
light theme -- email clients render <style> blocks and dark-mode media
queries inconsistently) from live data: scoreboard, standings, payment
status, and every member's full pick grid for the week.
"""

# ruff: noqa: E501 -- inline HTML/CSS template lines read better unwrapped.

from datetime import datetime
from html import escape

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import LeagueRole, WeekStatus
from app.models.league import League
from app.models.league_member import LeagueMember
from app.models.nfl_game import NflGame
from app.models.nfl_week import NflWeek
from app.repositories import (
    league_member_repository,
    nfl_game_repository,
    nfl_week_repository,
    pick_repository,
)
from app.schemas.leaderboard import WeekLabelRead, WeeklyLeaderboardRead
from app.services import leaderboard_service, member_payment_service


def get_most_recently_completed_week(db: Session, *, league: League) -> NflWeek:
    weeks = [
        week
        for week in nfl_week_repository.list_by_season(db, season=league.season)
        if week.status == WeekStatus.COMPLETE
    ]
    if not weeks:
        raise NotFoundError("No completed week is available for a report yet.")
    return max(weeks, key=lambda week: week.week_number)


def _game_card_html(game: NflGame) -> str:
    away_win = game.winning_team == game.away_team and not game.is_tie
    home_win = game.winning_team == game.home_team and not game.is_tie
    return f"""
    <table role="presentation" style="width:100%;border:1px solid #ddd4bf;border-radius:10px;
      background:#ffffff;margin-bottom:8px;">
      <tr>
        <td style="padding:10px 12px;font-size:13px;">
          <div style="display:flex;justify-content:space-between;font-weight:{'700' if away_win else '500'};
            color:{'#2f7d5b' if away_win else '#1c2230'};">
            <span>{escape(game.away_team)}</span><span>{game.away_score if game.away_score is not None else ''}</span>
          </div>
          <div style="display:flex;justify-content:space-between;font-weight:{'700' if home_win else '500'};
            color:{'#2f7d5b' if home_win else '#1c2230'};">
            <span>{escape(game.home_team)}</span><span>{game.home_score if game.home_score is not None else ''}</span>
          </div>
          <div style="margin-top:4px;font-size:11px;text-transform:uppercase;letter-spacing:0.04em;color:#8a8f9c;">
            {'Final &middot; Tie' if game.is_tie else 'Final'}
          </div>
        </td>
      </tr>
    </table>
    """


def render_weekly_report_html(db: Session, *, league: League, week_number: int) -> str:
    week = nfl_week_repository.get_by_season_and_week(
        db, season=league.season, week_number=week_number
    )
    if week is None:
        raise NotFoundError(f"Week {week_number} does not exist for this league's season.")

    games = nfl_game_repository.get_by_week_id(db, week.id)
    try:
        leaderboard = leaderboard_service.get_weekly_leaderboard(
            db, league=league, week_number=week_number
        )
    except NotFoundError:
        leaderboard = WeeklyLeaderboardRead(
            week=WeekLabelRead(week_number=week.week_number, season_number=week.season),
            standings=[],
            last_two_games=[],
        )
    _, payment_statuses = member_payment_service.list_payment_statuses(
        db, league=league, week_number=week_number
    )

    members = league_member_repository.list_by_league(db, league.id)
    all_picks = pick_repository.list_by_week_and_users(
        db, week_id=week.id, user_ids={member.user_id for member in members}
    )
    picks_by_user_game = {
        (pick.user_id, pick.game_id): pick for pick in all_picks if pick.voided_at is None
    }
    standings_by_user = {member.member_id: member for member in leaderboard.standings}
    # Report rows follow standings order when a member has scored results;
    # unscored/no-submission members are appended after, alphabetically.
    ordered_members = sorted(
        members,
        key=lambda member: (
            (
                standings_by_user[member.user_id].rank
                if member.user_id in standings_by_user
                else float("inf")
            ),
            member.user.display_name,
        ),
    )

    scoreboard_html = "".join(_game_card_html(game) for game in games)

    standings_rows = "".join(
        f"""<tr>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd4bf;font-weight:700;">{row.rank}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd4bf;">{escape(row.member_name)}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd4bf;text-align:right;font-weight:700;">{row.total_points}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd4bf;text-align:right;">{row.correct_picks}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd4bf;text-align:right;">{row.incorrect_picks}</td>
        </tr>"""
        for row in leaderboard.standings
    )

    payment_chips = ""
    for payment_member, payment, _voided_pick_count in payment_statuses:
        is_paid = payment.is_paid if payment else False
        color = "#2f7d5b" if is_paid else "#ad3d3d"
        payment_chips += (
            f'<span style="display:inline-block;padding:4px 10px;margin:2px;border-radius:999px;'
            f'font-size:12px;border:1px solid {color};color:{color};">'
            f"{escape(payment_member.user.display_name)}{'' if is_paid else ' &mdash; unpaid'}</span>"
        )

    game_headers = "".join(
        f"""<th style="padding:6px 8px;font-size:11px;text-transform:uppercase;color:#5f6577;
          border-bottom:1px solid #ddd4bf;white-space:nowrap;">{escape(game.away_team)}@{escape(game.home_team)}</th>"""
        for game in games
    )
    grid_rows = ""
    for member in ordered_members:
        cells = ""
        for game in games:
            pick = picks_by_user_game.get((member.user_id, game.id))
            if pick is None:
                cells += (
                    '<td style="padding:6px 8px;text-align:center;color:#8a8f9c;'
                    'border-bottom:1px solid #ddd4bf;">&mdash;</td>'
                )
                continue
            correct = pick.points_earned is not None and pick.points_earned > 0
            scored = pick.points_earned is not None
            color = "#2f7d5b" if (scored and correct) else "#ad3d3d" if scored else "#1c2230"
            cells += (
                f'<td style="padding:6px 8px;text-align:center;font-weight:700;color:{color};'
                f'border-bottom:1px solid #ddd4bf;">{escape(pick.picked_team)}<br>'
                f'<span style="font-weight:400;font-size:11px;">{pick.confidence_value}</span></td>'
            )
        grid_rows += (
            f'<tr><td style="padding:6px 8px;font-weight:700;white-space:nowrap;'
            f'border-bottom:1px solid #ddd4bf;">{escape(member.user.display_name)}</td>{cells}</tr>'
        )

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
      color:#1c2230;background:#f6f3ec;padding:20px;">
      <div style="max-width:900px;margin:0 auto;">
        <div style="border-bottom:2px solid #1c2230;padding-bottom:14px;margin-bottom:20px;">
          <p style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#6f4c14;margin:0 0 4px;">
            {escape(league.name)} &middot; {league.season} Season
          </p>
          <h1 style="margin:0;font-size:24px;">Week {week.week_number} Report</h1>
        </div>

        <h2 style="font-size:16px;">Scoreboard</h2>
        {scoreboard_html or '<p>No games this week.</p>'}

        <h2 style="font-size:16px;margin-top:24px;">Standings</h2>
        <table role="presentation" style="width:100%;border-collapse:collapse;background:#ffffff;
          border:1px solid #ddd4bf;border-radius:10px;overflow:hidden;">
          <tr style="background:#efe9dc;">
            <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;">Rank</th>
            <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;">Member</th>
            <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;">Pts</th>
            <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;">Correct</th>
            <th style="padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;">Incorrect</th>
          </tr>
          {standings_rows or '<tr><td style="padding:8px 12px;" colspan="5">No submitted picks yet.</td></tr>'}
        </table>

        <h2 style="font-size:16px;margin-top:24px;">Payments</h2>
        <div>{payment_chips or '<p>No payment records yet.</p>'}</div>

        <h2 style="font-size:16px;margin-top:24px;">Every pick</h2>
        <div style="overflow-x:auto;">
          <table role="presentation" style="border-collapse:collapse;background:#ffffff;
            border:1px solid #ddd4bf;border-radius:10px;">
            <tr style="background:#efe9dc;">
              <th style="padding:6px 8px;text-align:left;font-size:11px;text-transform:uppercase;
                border-bottom:1px solid #ddd4bf;">Member</th>
              {game_headers}
            </tr>
            {grid_rows}
          </table>
        </div>

        <p style="margin-top:24px;font-size:12px;color:#8a8f9c;">
          Generated {escape(datetime.now().strftime('%b %d, %Y'))} from live league data.
        </p>
      </div>
    </div>
    """


def commissioners(db: Session, *, league: League) -> list[LeagueMember]:
    members = league_member_repository.list_by_league(db, league.id)
    return [member for member in members if member.role == LeagueRole.OWNER]
