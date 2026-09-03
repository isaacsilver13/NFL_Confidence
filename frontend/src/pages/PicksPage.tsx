import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { savePicks } from '@/api/nfl'
import { fetchCurrentPicksCard } from '@/api/session'
import { TeamLogo } from '@/components/nfl/TeamLogo'
import { Button } from '@/components/ui/Button'
import type { NflGame, NflPick, NflWeek, PickInput } from '@/types/nfl'

interface PickDraft {
  team: string
  confidence: string
}

type PickDrafts = Record<string, PickDraft>

function formatKickoff(kickoff: string): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(kickoff))
}

function formatSpread(spread: number): string {
  return spread > 0 ? `+${spread}` : String(spread)
}

function formatDeadline(deadline: string): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(deadline))
}

function initialDrafts(games: NflGame[], picks: NflPick[]): PickDrafts {
  const picksByGame = new Map(picks.map((pick) => [pick.gameId, pick]))
  return Object.fromEntries(
    games.map((game) => {
      const pick = picksByGame.get(game.id)
      return [game.id, { team: pick?.team ?? '', confidence: pick ? String(pick.confidence) : '' }]
    }),
  )
}

function GamesForm({ week, games, picks }: { week: NflWeek; games: NflGame[]; picks: NflPick[] }) {
  const queryClient = useQueryClient()
  const [drafts, setDrafts] = useState<PickDrafts>(() => initialDrafts(games, picks))
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const locksAt = week.locksAt ? Date.parse(week.locksAt) : null
  const isLocked = Boolean(week.isLocked || (locksAt !== null && locksAt <= now))

  useEffect(() => {
    if (locksAt === null || isLocked) return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [isLocked, locksAt])

  const confidenceValues = Array.from({ length: games.length }, (_, index) => index + 1)
  // Maps a confidence value to the game it's currently assigned to, so each game card can check "used elsewhere" in O(1).
  const confidenceUsageByGame = useMemo(() => {
    const usage = new Map<number, string>()
    for (const game of games) {
      const confidence = Number(drafts[game.id]?.confidence)
      if (confidence) usage.set(confidence, game.id)
    }
    return usage
  }, [drafts, games])
  const saveMutation = useMutation({
    mutationFn: savePicks,
    onSuccess: async () => {
      setSaved(true)
      await queryClient.invalidateQueries({ queryKey: ['picks', 'card', 'current'] })
    },
  })

  function updateDraft(gameId: string, update: Partial<PickDraft>) {
    setSaved(false)
    setSubmitError(null)
    setDrafts((current) => ({ ...current, [gameId]: { ...current[gameId], ...update } }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitError(null)
    if (isLocked) {
      setSubmitError('Picks are locked after the first game kickoff.')
      return
    }
    const submissions: PickInput[] = games.map((game) => ({
      gameId: game.id,
      team: drafts[game.id]?.team ?? '',
      confidence: Number(drafts[game.id]?.confidence ?? 0),
    }))
    const hasMissingPick = submissions.some((pick) => !pick.team || pick.confidence < 1)
    const uniqueConfidenceValues = new Set(submissions.map((pick) => pick.confidence))
    if (hasMissingPick || uniqueConfidenceValues.size !== games.length) {
      setSubmitError('Choose a team and a unique confidence value for every game.')
      return
    }
    saveMutation.mutate({ week: week.weekNumber, picks: submissions })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 pb-5 dark:border-slate-800">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">
            {week.status} season {week.season}
          </p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            Week {week.weekNumber} picks
          </h1>
        </div>
        <div className="text-right text-sm text-slate-600 dark:text-slate-300">
          <p>Use each confidence value from 1 to {games.length} once.</p>
          {week.locksAt && (
            <p className={isLocked ? 'font-bold text-danger' : 'font-semibold text-accent'}>
              {isLocked ? 'Picks locked' : `Locks ${formatDeadline(week.locksAt)}`}
            </p>
          )}
        </div>
      </div>

      {isLocked && (
        <p className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm font-semibold text-danger">
          The first game has started. This week&apos;s picks are read-only.
        </p>
      )}

      {games.map((game) => {
        const draft = drafts[game.id] ?? { team: '', confidence: '' }
        const selectedConfidence = Number(draft.confidence)
        return (
          <fieldset
            key={game.id}
            className="animate-slide-up overflow-hidden rounded-2xl border border-slate-200 bg-surface shadow-sm transition-shadow hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
          >
            <legend className="sr-only">
              {game.awayTeam} at {game.homeTeam}
            </legend>
            <div className="border-b border-slate-200 bg-surface-muted/60 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/50">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
                {formatKickoff(game.kickoff)} · {game.status}
              </p>
              <p className="mt-2 text-sm text-ink-muted dark:text-slate-400">
                <span className="font-semibold text-ink dark:text-slate-200">
                  {game.venueName ?? 'Venue unavailable'}
                </span>
                {game.venueLocation && <span> · {game.venueLocation}</span>}
                <span>
                  {' '}
                  · Line:{' '}
                  {game.spreadTeam && game.spread !== null
                    ? `${game.spreadTeam} ${formatSpread(game.spread)}`
                    : 'Not available'}
                </span>
              </p>
            </div>
            <div className="flex flex-col gap-5 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                  Matchup
                </p>
                <div className="mt-3 flex items-center gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <TeamLogo code={game.awayTeam} decorative />
                    <span className="truncate text-base font-bold">{game.awayTeam}</span>
                  </div>
                  <span className="text-sm font-semibold text-ink-muted dark:text-slate-400">
                    at
                  </span>
                  <div className="flex min-w-0 items-center gap-2">
                    <TeamLogo code={game.homeTeam} decorative />
                    <span className="truncate text-base font-bold">{game.homeTeam}</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-4 sm:items-end">
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
                    Pick a winner
                  </p>
                  <div
                    className="flex flex-wrap gap-2"
                    role="group"
                    aria-label={`Winner for ${game.awayTeam} at ${game.homeTeam}`}
                  >
                    {[game.awayTeam, game.homeTeam].map((team) => {
                      const isSelected = draft.team === team
                      return (
                        <button
                          key={team}
                          type="button"
                          aria-pressed={isSelected}
                          disabled={isLocked}
                          onClick={() => updateDraft(game.id, { team })}
                          className={`flex min-h-11 items-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60 ${isSelected ? 'border-primary bg-primary text-white shadow-sm' : 'border-slate-300 bg-white text-ink hover:border-sky hover:bg-sky/10 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:hover:border-sky'}`}
                        >
                          <TeamLogo code={team} size="sm" decorative />
                          {team}
                        </button>
                      )
                    })}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
                    Confidence
                  </p>
                  <div
                    className="flex flex-wrap gap-2"
                    role="group"
                    aria-label={`Confidence for ${game.awayTeam} at ${game.homeTeam}`}
                  >
                    {confidenceValues.map((value) => {
                      const isSelected = selectedConfidence === value
                      const isUsedElsewhere =
                        confidenceUsageByGame.get(value) === game.id
                          ? false
                          : confidenceUsageByGame.has(value)
                      return (
                        <button
                          key={value}
                          type="button"
                          aria-pressed={isSelected}
                          disabled={isLocked}
                          aria-label={`${value}${isUsedElsewhere ? ' already used' : ''}`}
                          title={
                            isUsedElsewhere ? 'This confidence value is already used.' : undefined
                          }
                          onClick={() => updateDraft(game.id, { confidence: String(value) })}
                          className={`flex h-11 w-11 items-center justify-center rounded-xl border text-sm font-bold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60 ${isSelected ? 'border-gold bg-gold text-white shadow-sm' : isUsedElsewhere ? 'border-gold/60 bg-gold/10 text-gold hover:bg-gold/20' : 'border-slate-300 bg-white text-ink hover:border-gold hover:bg-gold/10 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'}`}
                        >
                          {value}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>
          </fieldset>
        )
      })}

      <div className="sticky bottom-3 z-10 -mx-1 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-surface/95 p-3 shadow-lg shadow-primary/10 backdrop-blur sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none sm:backdrop-blur-none dark:border-slate-800 dark:bg-slate-900/95 sm:dark:bg-transparent">
        <Button type="submit" disabled={saveMutation.isPending || isLocked}>
          {' '}
          {saveMutation.isPending ? 'Saving…' : 'Save picks'}{' '}
        </Button>
        {saved && <p className="text-sm font-semibold text-accent">Picks saved.</p>}
        {submitError && <p className="text-sm text-danger">{submitError}</p>}
      </div>
    </form>
  )
}

export function PicksPage() {
  const {
    data: picksCard,
    isPending,
    error,
  } = useQuery({
    queryKey: ['picks', 'card', 'current'],
    queryFn: fetchCurrentPicksCard,
  })

  if (isPending)
    return (
      <p className="animate-fade-in text-slate-600 dark:text-slate-300">
        Loading this week&apos;s games…
      </p>
    )

  if (error)
    return (
      <p className="animate-fade-in text-danger">
        {error instanceof ApiError ? error.message : 'Could not load this week&apos;s games.'}
      </p>
    )

  const week = picksCard?.week
  const games = picksCard?.games
  const picks = picksCard?.picks

  if (!week || !games || !picks)
    return (
      <p className="animate-fade-in text-slate-600 dark:text-slate-300">
        No current week is available.
      </p>
    )

  if (games.length === 0)
    return (
      <div className="animate-fade-in space-y-2">
        <h1 className="text-3xl font-black text-primary dark:text-white">Week {week.weekNumber}</h1>
        <p className="text-slate-600 dark:text-slate-300">No games are scheduled for this week.</p>
      </div>
    )

  const picksKey = picks.map((pick) => `${pick.gameId}:${pick.team}:${pick.confidence}`).join('|')
  return <GamesForm key={`${week.id}:${picksKey}`} week={week} games={games} picks={picks} />
}
