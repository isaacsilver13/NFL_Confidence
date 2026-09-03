import { TeamLogo, getTeamPalette } from '@/components/nfl/TeamLogo'
import type {
  GamePickBreakdown,
  TeamPickCount,
  WeeklyPickBreakdown as WeeklyPickBreakdownData,
} from '@/types/leaderboard'

function formatMedian(value: number | null): string {
  if (value === null) return 'No confidence data'
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function countForTeam(counts: TeamPickCount[], team: string): number {
  return counts.find((count) => count.team === team)?.userCount ?? 0
}

function GameBreakdown({ game }: { game: GamePickBreakdown }) {
  const awayCount = countForTeam(game.teamCounts, game.awayTeam)
  const homeCount = countForTeam(game.teamCounts, game.homeTeam)
  const total = awayCount + homeCount
  const awayPercentage = total === 0 ? 0 : Math.round((awayCount / total) * 100)
  const homePercentage = total === 0 ? 0 : 100 - awayPercentage
  const awayPalette = getTeamPalette(game.awayTeam)
  const homePalette = getTeamPalette(game.homeTeam)

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-bold">
          <TeamLogo code={game.awayTeam} size="sm" decorative />
          <span>{game.awayTeam}</span>
          <span className="text-ink-muted dark:text-slate-400">at</span>
          <TeamLogo code={game.homeTeam} size="sm" decorative />
          <span>{game.homeTeam}</span>
        </div>
        <p className="text-sm text-ink-muted dark:text-slate-400">
          Median confidence:{' '}
          <span className="font-bold text-ink dark:text-slate-200">
            {formatMedian(game.medianConfidence)}
          </span>
        </p>
      </div>
      <div className="mt-4 grid gap-2 text-xs font-bold sm:grid-cols-2">
        <div className="flex items-center justify-between gap-3">
          <span>
            {game.awayTeam}: {awayCount} {awayCount === 1 ? 'pick' : 'picks'}
          </span>
          <span>{awayPercentage}%</span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span>
            {game.homeTeam}: {homeCount} {homeCount === 1 ? 'pick' : 'picks'}
          </span>
          <span>{homePercentage}%</span>
        </div>
      </div>
      <div
        className="mt-2 flex h-4 min-w-0 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
        role="img"
        aria-label={`${game.awayTeam} ${awayPercentage} percent, ${game.homeTeam} ${homePercentage} percent`}
      >
        <span style={{ width: `${awayPercentage}%`, backgroundColor: awayPalette.background }} />
        <span style={{ width: `${homePercentage}%`, backgroundColor: homePalette.background }} />
      </div>
      {total === 0 && (
        <p className="mt-2 text-xs text-ink-muted dark:text-slate-400">
          No picks were submitted for this game.
        </p>
      )}
    </article>
  )
}

export function WeeklyPickBreakdown({ weeks }: { weeks: WeeklyPickBreakdownData[] }) {
  if (weeks.length === 0) {
    return (
      <p className="text-sm text-ink-muted dark:text-slate-400">
        No completed weeks are available.
      </p>
    )
  }

  return (
    <div className="space-y-5">
      {weeks.map((breakdown) => (
        <section
          key={breakdown.weekNumber}
          className="space-y-3"
          aria-labelledby={`week-breakdown-${breakdown.weekNumber}`}
        >
          <h3
            id={`week-breakdown-${breakdown.weekNumber}`}
            className="text-lg font-black text-primary dark:text-white"
          >
            Week {breakdown.weekNumber}
          </h3>
          {breakdown.games.length === 0 && (
            <p className="text-sm text-ink-muted dark:text-slate-400">
              No games are available for this week.
            </p>
          )}
          <div className="space-y-3">
            {breakdown.games.map((game) => (
              <GameBreakdown key={game.gameId} game={game} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
