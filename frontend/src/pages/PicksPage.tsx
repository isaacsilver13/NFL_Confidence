import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { AlertTriangle, Check } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { fetchAllPicksCurrentWeek, savePicks, submitPicks } from '@/api/nfl'
import { fetchCurrentPicksCard } from '@/api/session'
import { TeamLogo } from '@/components/nfl/TeamLogo'
import { getPicksCardRefetchInterval } from '@/features/nfl/picksPolling'
import type { NflGame, NflPick, NflWeek, PickInput, WeekSubmission } from '@/types/nfl'

const AUTO_SAVE_DEBOUNCE_MS = 400

interface PickDraft {
  team: string
  confidence: string
}

type PickDrafts = Record<string, PickDraft>

interface PendingSave {
  drafts: PickDrafts
  version: number
}

interface DraftSavePayload {
  submissions: PickInput[]
  voidedGameIds: string[]
}

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
      const activePick = pick?.isVoided ? undefined : pick
      return [
        game.id,
        {
          team: activePick?.team ?? '',
          confidence: activePick ? String(activePick.confidence) : '',
        },
      ]
    }),
  )
}

function isCompleteDraft(game: NflGame, draft: PickDraft | undefined, gameCount: number): boolean {
  const confidence = Number(draft?.confidence ?? 0)
  return (
    Boolean(draft?.team) &&
    (draft?.team === game.awayTeam || draft?.team === game.homeTeam) &&
    Number.isInteger(confidence) &&
    confidence >= 1 &&
    confidence <= gameCount
  )
}

function draftSavePayload(games: NflGame[], drafts: PickDrafts): DraftSavePayload {
  const candidates = games.map((game) => {
    const draft = drafts[game.id]
    const confidence = Number(draft?.confidence ?? 0)
    const isComplete = isCompleteDraft(game, draft, games.length)
    return { game, team: draft?.team ?? '', confidence, isComplete }
  })
  const confidenceCounts = new Map<number, number>()
  for (const candidate of candidates) {
    if (candidate.isComplete) {
      confidenceCounts.set(
        candidate.confidence,
        (confidenceCounts.get(candidate.confidence) ?? 0) + 1,
      )
    }
  }

  const submissions: PickInput[] = []
  const voidedGameIds: string[] = []
  for (const candidate of candidates) {
    if (candidate.isComplete && confidenceCounts.get(candidate.confidence) === 1) {
      submissions.push({
        gameId: candidate.game.id,
        team: candidate.team,
        confidence: candidate.confidence,
      })
    } else {
      voidedGameIds.push(candidate.game.id)
    }
  }
  return { submissions, voidedGameIds }
}

function formatSubmittedAt(submittedAt: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(submittedAt))
}

function AllPicksTable() {
  const { data, isPending, error } = useQuery({
    queryKey: ['picks', 'all', 'current'],
    queryFn: fetchAllPicksCurrentWeek,
    staleTime: 60_000,
  })

  if (isPending) {
    return <p className="text-sm text-ink-muted dark:text-slate-400">Loading everyone's picks…</p>
  }
  if (error) {
    return (
      <p className="text-sm text-danger">
        {error instanceof ApiError ? error.message : "Could not load everyone's picks."}
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="bg-surface-muted dark:bg-slate-900">
            <th className="sticky left-0 z-10 bg-surface-muted px-3 py-2 text-left font-bold dark:bg-slate-900">
              Member
            </th>
            {data.games.map((game) => (
              <th key={game.id} className="px-3 py-2 text-center font-bold whitespace-nowrap">
                {game.awayTeam} @ {game.homeTeam}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.members.map((member) => {
            const picksByGame = new Map(member.picks.map((pick) => [pick.gameId, pick]))
            return (
              <tr key={member.userId} className="border-t border-slate-200 dark:border-slate-800">
                <td className="sticky left-0 z-10 bg-surface px-3 py-2 font-semibold whitespace-nowrap dark:bg-slate-950">
                  {member.displayName}
                </td>
                {data.games.map((game) => {
                  const pick = picksByGame.get(game.id)
                  return (
                    <td key={game.id} className="px-3 py-2 text-center whitespace-nowrap">
                      {pick ? `${pick.team} (${pick.confidence})` : '—'}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function GamesForm({
  week,
  games,
  picks,
  submission,
}: {
  week: NflWeek
  games: NflGame[]
  picks: NflPick[]
  submission: WeekSubmission
}) {
  const queryClient = useQueryClient()
  const [drafts, setDrafts] = useState<PickDrafts>(() => initialDrafts(games, picks))
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [voided, setVoided] = useState(false)
  const [submitPicksError, setSubmitPicksError] = useState<string | null>(null)
  const [showAllPicks, setShowAllPicks] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const gameKickoffs = games
    .map((game) => Date.parse(game.kickoff))
    .filter((kickoff) => Number.isFinite(kickoff))
  const earliestKickoff = gameKickoffs.length > 0 ? Math.min(...gameKickoffs) : null
  const locksAt = week.locksAt ? Date.parse(week.locksAt) : earliestKickoff
  const isLocked = Boolean(week.isLocked || (locksAt !== null && locksAt <= now))
  const draftsRef = useRef(drafts)
  const draftVersionRef = useRef(0)
  const isLockedRef = useRef(isLocked)
  const saveTimerRef = useRef<number | null>(null)
  const pendingSaveRef = useRef<PendingSave | null>(null)
  const savingRef = useRef(false)

  useEffect(() => {
    if (locksAt === null || isLocked) return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [isLocked, locksAt])

  useEffect(() => {
    isLockedRef.current = isLocked
  }, [isLocked])

  useEffect(() => {
    return () => {
      if (saveTimerRef.current !== null) window.clearTimeout(saveTimerRef.current)
    }
  }, [])

  const confidenceValues = Array.from({ length: games.length }, (_, index) => index + 1)
  const confidenceUsageByValue = useMemo(() => {
    const usage = new Map<number, string[]>()
    for (const game of games) {
      if (!isCompleteDraft(game, drafts[game.id], games.length)) continue
      const confidence = Number(drafts[game.id]?.confidence)
      const gameIds = usage.get(confidence) ?? []
      gameIds.push(game.id)
      usage.set(confidence, gameIds)
    }
    return usage
  }, [drafts, games])
  const confidenceConflicts = useMemo(
    () => Array.from(confidenceUsageByValue.entries()).filter(([, gameIds]) => gameIds.length > 1),
    [confidenceUsageByValue],
  )
  const conflictingGameIds = useMemo(
    () => new Set(confidenceConflicts.flatMap(([, gameIds]) => gameIds)),
    [confidenceConflicts],
  )
  const pickedCount = useMemo(
    () => games.filter((game) => isCompleteDraft(game, drafts[game.id], games.length)).length,
    [drafts, games],
  )
  const hasConflicts = confidenceConflicts.length > 0
  const saveMutation = useMutation({
    mutationFn: savePicks,
  })
  const submitMutation = useMutation({
    mutationFn: submitPicks,
    onSuccess: async () => {
      setSubmitPicksError(null)
      await queryClient.invalidateQueries({ queryKey: ['picks', 'card', 'current'] })
    },
    onError: (error: unknown) => {
      setSubmitPicksError(
        error instanceof ApiError ? error.message : "Could not submit this week's picks.",
      )
    },
  })
  const isComplete = pickedCount === games.length && games.length > 0
  const canSubmit = isComplete && !hasConflicts && !isLocked && !submitMutation.isPending

  function handleSubmitPicks() {
    submitMutation.mutate(week.weekNumber)
  }

  async function saveDraft(pendingSave: PendingSave) {
    if (savingRef.current) {
      pendingSaveRef.current = pendingSave
      return
    }

    if (isLockedRef.current) {
      if (pendingSave.version === draftVersionRef.current) {
        setSaved(false)
        setVoided(false)
        setSubmitError('Picks are locked after the earliest game kickoff.')
      }
      return
    }

    const { submissions, voidedGameIds } = draftSavePayload(games, pendingSave.drafts)

    savingRef.current = true
    try {
      await saveMutation.mutateAsync({
        week: week.weekNumber,
        picks: submissions,
        voidedGameIds,
      })
      if (pendingSave.version === draftVersionRef.current) {
        await queryClient.invalidateQueries({ queryKey: ['picks', 'card', 'current'] })
        if (pendingSave.version === draftVersionRef.current) {
          setSaved(true)
          setVoided(voidedGameIds.length > 0)
          setSubmitError(null)
        }
      }
    } catch (error) {
      if (pendingSave.version === draftVersionRef.current) {
        setSaved(false)
        setSubmitError(
          error instanceof ApiError ? error.message : "Could not save this week's picks.",
        )
      }
      setVoided(false)
    } finally {
      savingRef.current = false
      const queuedSave = pendingSaveRef.current
      if (queuedSave && queuedSave.version > pendingSave.version) {
        pendingSaveRef.current = null
        scheduleSave(queuedSave, 0)
      } else if (draftVersionRef.current > pendingSave.version) {
        scheduleSave({ drafts: draftsRef.current, version: draftVersionRef.current }, 0)
      }
    }
  }

  function scheduleSave(pendingSave: PendingSave, delay = AUTO_SAVE_DEBOUNCE_MS) {
    pendingSaveRef.current = pendingSave
    if (saveTimerRef.current !== null) window.clearTimeout(saveTimerRef.current)
    saveTimerRef.current = window.setTimeout(() => {
      saveTimerRef.current = null
      const nextSave = pendingSaveRef.current
      pendingSaveRef.current = null
      if (nextSave) void saveDraft(nextSave)
    }, delay)
  }

  function updateDraft(gameId: string, update: Partial<PickDraft>) {
    const currentDraft = draftsRef.current[gameId]
    const nextDraft = { ...currentDraft, ...update }
    if (
      nextDraft.team === currentDraft?.team &&
      nextDraft.confidence === currentDraft?.confidence
    ) {
      return
    }
    const nextDrafts = {
      ...draftsRef.current,
      [gameId]: nextDraft,
    }
    const nextVersion = draftVersionRef.current + 1
    draftsRef.current = nextDrafts
    draftVersionRef.current = nextVersion
    setSaved(false)
    setSubmitError(null)
    setDrafts(nextDrafts)
    scheduleSave({ drafts: nextDrafts, version: nextVersion })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    scheduleSave({ drafts: draftsRef.current, version: draftVersionRef.current }, 0)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="sticky top-[70px] z-10 -mx-1 space-y-3 rounded-2xl border border-slate-200 bg-surface/95 px-4 py-3 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-900/95 sm:mx-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
              Pick progress
            </p>
            <p className="mt-1 text-lg font-black text-primary dark:text-white">
              {pickedCount} of {games.length} games picked
            </p>
          </div>
          {hasConflicts ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-danger/10 px-3 py-1.5 text-xs font-black uppercase tracking-[0.12em] text-danger">
              <AlertTriangle size={14} aria-hidden="true" /> Resolve conflicts
            </span>
          ) : pickedCount === games.length ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-3 py-1.5 text-xs font-black uppercase tracking-[0.12em] text-accent">
              <Check size={14} aria-hidden="true" /> Complete
            </span>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3 dark:border-slate-800">
          <p
            role="status"
            className={`text-sm font-semibold ${submission.submittedAt ? 'text-accent' : 'text-ink-muted dark:text-slate-400'}`}
          >
            {submission.submittedAt
              ? `Submitted ${formatSubmittedAt(submission.submittedAt)}`
              : 'Not yet submitted'}
          </p>
          {!isLocked && (
            <button
              type="button"
              onClick={handleSubmitPicks}
              disabled={!canSubmit}
              className="rounded-xl bg-primary px-4 py-2 text-sm font-black text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40 dark:bg-sky dark:text-primary"
            >
              {submitMutation.isPending
                ? 'Submitting…'
                : submission.submittedAt
                  ? 'Resubmit picks'
                  : 'Submit picks'}
            </button>
          )}
        </div>
        <div
          role="progressbar"
          aria-label="Games picked"
          aria-valuemin={0}
          aria-valuemax={games.length}
          aria-valuenow={pickedCount}
          className="h-2 overflow-hidden rounded-full bg-surface-muted dark:bg-slate-800"
        >
          <div
            className={`h-full rounded-full transition-[width] ${hasConflicts ? 'bg-danger' : 'bg-accent'}`}
            style={{ width: `${games.length ? (pickedCount / games.length) * 100 : 0}%` }}
          />
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted dark:text-slate-400">
            Confidence values
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5" role="list" aria-label="Confidence values">
            {confidenceValues.map((value) => {
              const usedBy = confidenceUsageByValue.get(value) ?? []
              const isConflict = usedBy.length > 1
              return (
                <span
                  key={value}
                  role="listitem"
                  aria-label={`Confidence ${value}${usedBy.length ? ' used' : ' available'}${isConflict ? ', conflict' : ''}`}
                  className={`inline-flex h-7 min-w-7 items-center justify-center gap-0.5 rounded-md border px-1.5 text-xs font-bold ${isConflict ? 'border-danger bg-danger/10 text-danger' : usedBy.length ? 'border-slate-300 bg-surface-muted text-ink-muted line-through dark:border-slate-700 dark:bg-slate-950 dark:text-slate-500' : 'border-accent/40 bg-accent/5 text-accent'}`}
                >
                  {usedBy.length > 0 && <Check size={11} aria-hidden="true" />}
                  {value}
                </span>
              )
            })}
          </div>
        </div>
      </div>
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
          {(week.locksAt || isLocked) && (
            <p className={isLocked ? 'font-bold text-danger' : 'font-semibold text-accent'}>
              {isLocked
                ? 'Picks locked'
                : week.locksAt
                  ? `Locks ${formatDeadline(week.locksAt)}`
                  : null}
            </p>
          )}
        </div>
      </div>

      {isLocked && (
        <div className="space-y-3 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-semibold text-danger">
              The earliest game has started. This week&apos;s picks are read-only.
            </p>
            <button
              type="button"
              onClick={() => setShowAllPicks((current) => !current)}
              className="rounded-xl border border-danger/40 px-3 py-1.5 text-sm font-black text-danger"
            >
              {showAllPicks ? 'Hide all picks' : "See everyone's picks"}
            </button>
          </div>
          {showAllPicks && <AllPicksTable />}
        </div>
      )}

      {confidenceConflicts.length > 0 && (
        <div
          role="alert"
          className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
        >
          <p className="font-bold">Conflicting picks</p>
          <p className="mt-1">
            These picks will be voided unless fixed. They remain invalid until fixed because each
            confidence value can be used only once.
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {confidenceConflicts.map(([confidence, gameIds]) => (
              <li key={confidence}>
                <button
                  type="button"
                  className="text-left font-semibold underline decoration-danger/40 underline-offset-2 hover:decoration-danger"
                  onClick={() => {
                    const firstGame = document.getElementById(`game-${gameIds[0]}`)
                    if (firstGame && 'scrollIntoView' in firstGame) {
                      firstGame.scrollIntoView({ behavior: 'smooth', block: 'center' })
                    }
                  }}
                >
                  {confidence} point{confidence === 1 ? '' : 's'}:{' '}
                  {gameIds
                    .map((gameId) => {
                      const game = games.find((candidate) => candidate.id === gameId)
                      return game ? `${game.awayTeam} at ${game.homeTeam}` : gameId
                    })
                    .join(', ')}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {games.map((game) => {
        const draft = drafts[game.id] ?? { team: '', confidence: '' }
        const selectedConfidence = Number(draft.confidence)
        const isPicked = isCompleteDraft(game, draft, games.length)
        const isConflicting = conflictingGameIds.has(game.id)
        return (
          <fieldset
            key={game.id}
            id={`game-${game.id}`}
            data-testid={`pick-card-${game.id}`}
            className={`animate-slide-up overflow-hidden rounded-2xl border bg-surface shadow-sm transition-shadow hover:shadow-md dark:bg-slate-900 ${isConflicting ? 'border-danger bg-danger/5 dark:border-danger' : isPicked ? 'border-accent/70 bg-accent/5 dark:border-accent/70' : 'border-slate-200 dark:border-slate-800'}`}
          >
            <legend className="sr-only">
              {game.awayTeam} at {game.homeTeam}
            </legend>
            <div className="border-b border-slate-200 bg-surface-muted/60 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/50">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
                  {formatKickoff(game.kickoff)} · {game.status}
                </p>
                <span
                  className={`inline-flex items-center gap-1 text-xs font-black uppercase tracking-[0.12em] ${isConflicting ? 'text-danger' : isPicked ? 'text-accent' : 'text-ink-muted dark:text-slate-400'}`}
                >
                  {isConflicting ? (
                    <AlertTriangle size={13} aria-hidden="true" />
                  ) : isPicked ? (
                    <Check size={13} aria-hidden="true" />
                  ) : null}
                  {isConflicting ? 'Conflict' : isPicked ? 'Picked' : 'Not picked'}
                </span>
              </div>
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
                    <span
                      data-testid={`team-name-${game.id}-away`}
                      className={`truncate text-base font-bold ${game.status === 'final' && !game.isTie && game.winningTeam === game.awayTeam ? 'text-accent' : ''}`}
                    >
                      {game.awayTeam}
                    </span>
                  </div>
                  {game.status === 'final' ? (
                    <div className="flex flex-col items-center">
                      <span className="text-sm font-black text-primary dark:text-white">
                        {game.awayScore ?? 0}–{game.homeScore ?? 0}
                      </span>
                      <span className="text-xs font-bold uppercase tracking-[0.08em] text-ink-muted dark:text-slate-400">
                        {game.isTie ? 'Final · Tie' : 'Final'}
                      </span>
                    </div>
                  ) : (
                    <span className="text-sm font-semibold text-ink-muted dark:text-slate-400">
                      at
                    </span>
                  )}
                  <div className="flex min-w-0 items-center gap-2">
                    <TeamLogo code={game.homeTeam} decorative />
                    <span
                      data-testid={`team-name-${game.id}-home`}
                      className={`truncate text-base font-bold ${game.status === 'final' && !game.isTie && game.winningTeam === game.homeTeam ? 'text-accent' : ''}`}
                    >
                      {game.homeTeam}
                    </span>
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
                          onClick={() => updateDraft(game.id, { team: isSelected ? '' : team })}
                          className={`flex min-h-11 items-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60 ${isSelected ? 'border-primary bg-primary text-white shadow-sm dark:border-sky dark:bg-sky/20 dark:text-sky' : 'border-slate-300 bg-white text-ink hover:border-sky hover:bg-sky/10 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:hover:border-sky'}`}
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
                    className="grid grid-cols-4 gap-2"
                    role="group"
                    aria-label={`Confidence for ${game.awayTeam} at ${game.homeTeam}`}
                  >
                    {confidenceValues.map((value) => {
                      const isSelected = selectedConfidence === value
                      const isUsedElsewhere =
                        confidenceUsageByValue.get(value)?.some((gameId) => gameId !== game.id) ??
                        false
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
                          onClick={() =>
                            updateDraft(game.id, {
                              confidence: isSelected ? '' : String(value),
                            })
                          }
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

      {(saveMutation.isPending || saved || submitError) && (
        <div className="sticky bottom-3 z-10 -mx-1 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-surface/95 p-3 shadow-lg shadow-primary/10 backdrop-blur sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none sm:backdrop-blur-none dark:border-slate-800 dark:bg-slate-900/95 sm:dark:bg-transparent">
          {saveMutation.isPending && (
            <p role="status" className="text-sm font-semibold text-ink-muted dark:text-slate-400">
              Saving…
            </p>
          )}
          {saved && (
            <p role="status" className="text-sm font-semibold text-accent">
              {hasConflicts
                ? 'Picks saved, but conflicts must be resolved before this week is complete.'
                : voided
                  ? 'Picks saved. Incomplete or conflicting picks were voided.'
                  : 'Picks saved.'}
            </p>
          )}
          {submitError && (
            <p role="alert" className="text-sm text-danger">
              {submitError}
            </p>
          )}
        </div>
      )}

      {submitPicksError && (
        <p role="alert" className="text-sm text-danger">
          {submitPicksError}
        </p>
      )}
    </form>
  )
}

function PicksScrollPane({ children }: { children: ReactNode }) {
  return (
    <div
      data-testid="picks-scroll-pane"
      className="h-[calc(100dvh-8rem)] overflow-y-auto overscroll-contain px-1 pb-4 sm:h-auto sm:overflow-visible sm:px-0 sm:pb-0"
    >
      {children}
    </div>
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
    staleTime: 10_000,
    refetchInterval: (query) => getPicksCardRefetchInterval(query.state.data),
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
  const submission = picksCard?.submission

  if (!week || !games || !picks || !submission)
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
  return (
    <PicksScrollPane>
      <GamesForm
        key={`${week.id}:${picksKey}`}
        week={week}
        games={games}
        picks={picks}
        submission={submission}
      />
    </PicksScrollPane>
  )
}
