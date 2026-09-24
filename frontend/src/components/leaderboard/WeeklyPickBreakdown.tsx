import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { fetchGamePicks } from '@/api/leaderboard'
import { Button } from '@/components/ui/Button'
import { TeamLogo } from '@/components/nfl/TeamLogo'
import { getTeamPalette } from '@/components/nfl/teamPalette'
import type { GamePickBreakdown, TeamPickCount } from '@/types/leaderboard'

function GamePicksModal({ game, onClose }: { game: GamePickBreakdown; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const { data, isPending, error } = useQuery({
    queryKey: ['leaderboard', 'game-picks', game.gameId],
    queryFn: () => fetchGamePicks(game.gameId),
  })

  useEffect(() => {
    closeRef.current?.focus()
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="game-picks-title"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-surface p-5 shadow-lg dark:border-slate-800 dev-dark:border-border dark:bg-slate-900 dev-dark:bg-surface-elevated"
      >
        <div className="flex items-center justify-between gap-3">
          <h2
            id="game-picks-title"
            className="text-lg font-black text-primary dark:text-white dev-dark:text-ink"
          >
            {game.awayTeam} at {game.homeTeam}
          </h2>
          <Button ref={closeRef} type="button" variant="quiet" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="mt-4 max-h-96 overflow-y-auto">
          {isPending && (
            <p className="text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
              Loading picks...
            </p>
          )}
          {error && (
            <p className="text-sm text-danger">
              {error instanceof ApiError ? error.message : 'Could not load picks for this game.'}
            </p>
          )}
          {data && data.picks.length === 0 && (
            <p className="text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
              No picks were submitted for this game.
            </p>
          )}
          {data && data.picks.length > 0 && (
            <ul className="divide-y divide-slate-200 dark:divide-slate-800 dev-dark:divide-border">
              {data.picks.map((pick) => (
                <li
                  key={pick.memberName}
                  className="flex items-center justify-between gap-3 py-2 text-sm"
                >
                  <span className="font-medium">{pick.memberName}</span>
                  <span
                    className={
                      pick.isCorrect === true
                        ? 'font-bold text-accent'
                        : pick.isCorrect === false
                          ? 'font-bold text-danger'
                          : 'font-bold text-ink-muted dark:text-slate-400 dev-dark:text-text-muted'
                    }
                  >
                    {pick.team} ({pick.confidence})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function formatMedian(value: number | null): string {
  if (value === null) return 'No confidence data'
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function countForTeam(counts: TeamPickCount[], team: string): number {
  return counts.find((count) => count.team === team)?.userCount ?? 0
}

function GameBreakdown({
  game,
  onViewPicks,
}: {
  game: GamePickBreakdown
  onViewPicks: () => void
}) {
  const awayCount = countForTeam(game.teamCounts, game.awayTeam)
  const homeCount = countForTeam(game.teamCounts, game.homeTeam)
  const total = awayCount + homeCount
  const awayPercentage = total === 0 ? 0 : Math.round((awayCount / total) * 100)
  const homePercentage = total === 0 ? 0 : 100 - awayPercentage
  const awayPalette = getTeamPalette(game.awayTeam)
  const homePalette = getTeamPalette(game.homeTeam)

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dev-dark:border-border dark:bg-slate-950 dev-dark:bg-background">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-bold">
          <TeamLogo code={game.awayTeam} size="sm" decorative />
          <span>
            {game.awayTeam}
            {game.awayRecord && (
              <span className="ml-1 font-semibold text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
                ({game.awayRecord})
              </span>
            )}
          </span>
          <span className="text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">at</span>
          <TeamLogo code={game.homeTeam} size="sm" decorative />
          <span>
            {game.homeTeam}
            {game.homeRecord && (
              <span className="ml-1 font-semibold text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
                ({game.homeRecord})
              </span>
            )}
          </span>
        </div>
        <p className="text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
          Median confidence:{' '}
          <span className="font-bold text-ink dark:text-slate-200 dev-dark:text-ink">
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
        className="mt-2 flex h-4 min-w-0 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800 dev-dark:bg-surface-hover"
        role="img"
        aria-label={`${game.awayTeam} ${awayPercentage} percent, ${game.homeTeam} ${homePercentage} percent`}
      >
        <span style={{ width: `${awayPercentage}%`, backgroundColor: awayPalette.background }} />
        <span style={{ width: `${homePercentage}%`, backgroundColor: homePalette.background }} />
      </div>
      {total === 0 && (
        <p className="mt-2 text-xs text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
          No picks were submitted for this game.
        </p>
      )}
      <div className="mt-3 text-right">
        <Button type="button" variant="quiet" onClick={onViewPicks}>
          View Picks
        </Button>
      </div>
    </article>
  )
}

export function WeeklyPickBreakdown({ games }: { games: GamePickBreakdown[] }) {
  const [openGame, setOpenGame] = useState<GamePickBreakdown | null>(null)

  if (games.length === 0) {
    return (
      <p className="text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
        No games are available for this week.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {games.map((game) => (
        <GameBreakdown key={game.gameId} game={game} onViewPicks={() => setOpenGame(game)} />
      ))}
      {openGame && <GamePicksModal game={openGame} onClose={() => setOpenGame(null)} />}
    </div>
  )
}
