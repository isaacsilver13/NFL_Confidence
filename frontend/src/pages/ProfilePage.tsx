import { useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, UserRound } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ApiError } from '@/api/client'
import { fetchPickHistory } from '@/api/nfl'
import type { HistoricalPick, HistoricalWeek, PickOutcome } from '@/types/nfl'

const OUTCOME_LABELS: Record<PickOutcome, string> = {
  correct: 'Correct',
  incorrect: 'Incorrect',
  unscored: 'Not scored',
  voided: 'Voided',
}

type SortKey = 'game' | 'team' | 'confidence' | 'outcome' | 'points'
type SortDirection = 'ascending' | 'descending'

const OUTCOME_ORDER: Record<PickOutcome, number> = {
  voided: 0,
  unscored: 1,
  incorrect: 2,
  correct: 3,
}

function formatKickoff(kickoff: string): string {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(
    new Date(kickoff),
  )
}

function Outcome({ pick }: { pick: HistoricalPick }) {
  const color =
    pick.outcome === 'correct'
      ? 'text-success'
      : pick.outcome === 'incorrect'
        ? 'text-danger'
        : pick.outcome === 'voided'
          ? 'text-gold'
          : 'text-ink-muted dark:text-slate-400 dev-dark:text-text-muted'
  return <span className={`font-bold ${color}`}>{OUTCOME_LABELS[pick.outcome]}</span>
}

function HistoryTable({ picks }: { picks: HistoricalPick[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('game')
  const [direction, setDirection] = useState<SortDirection>('ascending')
  const sortedPicks = [...picks].sort((left, right) => {
    const leftValue = sortValue(left, sortKey)
    const rightValue = sortValue(right, sortKey)
    const comparison = compareValues(leftValue, rightValue)
    if (comparison !== 0) return comparison * (direction === 'ascending' ? 1 : -1)
    return left.kickoff.localeCompare(right.kickoff) || left.id.localeCompare(right.id)
  })

  function handleSort(nextKey: SortKey) {
    if (nextKey === sortKey) {
      setDirection((current) => (current === 'ascending' ? 'descending' : 'ascending'))
      return
    }
    setSortKey(nextKey)
    setDirection('ascending')
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 dev-dark:border-border">
      <table className="w-full min-w-[760px] text-left text-sm">
        <caption className="sr-only">Your picks</caption>
        <thead className="bg-surface-muted text-xs uppercase tracking-[0.14em] text-ink-muted dark:bg-slate-950 dev-dark:bg-background dark:text-slate-400 dev-dark:text-text-muted">
          <tr>
            <SortableHeader
              label="Game"
              sortKey="game"
              activeKey={sortKey}
              direction={direction}
              onSort={handleSort}
            />
            <SortableHeader
              label="Picked team"
              sortKey="team"
              activeKey={sortKey}
              direction={direction}
              onSort={handleSort}
            />
            <SortableHeader
              label="Confidence"
              sortKey="confidence"
              activeKey={sortKey}
              direction={direction}
              onSort={handleSort}
              align="right"
            />
            <SortableHeader
              label="Outcome"
              sortKey="outcome"
              activeKey={sortKey}
              direction={direction}
              onSort={handleSort}
            />
            <SortableHeader
              label="Points"
              sortKey="points"
              activeKey={sortKey}
              direction={direction}
              onSort={handleSort}
              align="right"
            />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800 dev-dark:divide-border">
          {sortedPicks.map((pick) => (
            <tr key={pick.id}>
              <th scope="row" className="px-4 py-3 font-semibold">
                {pick.awayTeam} at {pick.homeTeam}
                <span className="block text-xs font-normal text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
                  {formatKickoff(pick.kickoff)}
                </span>
              </th>
              <td className="px-4 py-3 font-bold">{pick.team}</td>
              <td className="px-4 py-3 text-right">{pick.confidence}</td>
              <td className="px-4 py-3">
                <Outcome pick={pick} />
              </td>
              <td className="px-4 py-3 text-right">{pick.pointsEarned ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function sortValue(pick: HistoricalPick, sortKey: SortKey): string | number | null {
  if (sortKey === 'game') return `${pick.awayTeam} at ${pick.homeTeam}`
  if (sortKey === 'team') return pick.team
  if (sortKey === 'confidence') return pick.confidence
  if (sortKey === 'outcome') return OUTCOME_ORDER[pick.outcome]
  return pick.pointsEarned
}

function compareValues(left: string | number | null, right: string | number | null): number {
  if (left === null && right === null) return 0
  if (left === null) return 1
  if (right === null) return -1
  if (typeof left === 'number' && typeof right === 'number') return left - right
  return String(left).localeCompare(String(right))
}

function SortableHeader({
  label,
  sortKey,
  activeKey,
  direction,
  onSort,
  align = 'left',
}: {
  label: string
  sortKey: SortKey
  activeKey: SortKey
  direction: SortDirection
  onSort: (key: SortKey) => void
  align?: 'left' | 'right'
}) {
  const isActive = activeKey === sortKey
  const Icon = isActive ? (direction === 'ascending' ? ArrowUp : ArrowDown) : ArrowUpDown
  return (
    <th
      className={`px-4 py-3 ${align === 'right' ? 'text-right' : ''}`}
      aria-sort={isActive ? direction : 'none'}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        aria-label={`Sort by ${label}`}
        className="inline-flex items-center gap-1 font-bold hover:text-primary dark:hover:text-white dev-dark:hover:text-ink"
      >
        <span>{label}</span>
        <Icon size={14} aria-hidden="true" />
      </button>
    </th>
  )
}

interface WeekStat {
  weekNumber: number
  correct: number
  incorrect: number
  scoredPicks: number
  winRate: number | null
  totalPoints: number
}

interface ConfidenceStat {
  confidence: number
  correct: number
}

function computeWeekStats(weeks: HistoricalWeek[]): WeekStat[] {
  return [...weeks]
    .sort((left, right) => left.weekNumber - right.weekNumber)
    .map((week) => {
      const scored = week.picks.filter(
        (pick) => pick.outcome === 'correct' || pick.outcome === 'incorrect',
      )
      const correct = scored.filter((pick) => pick.outcome === 'correct').length
      const incorrect = scored.length - correct
      const totalPoints = week.picks.reduce((sum, pick) => sum + (pick.pointsEarned ?? 0), 0)
      return {
        weekNumber: week.weekNumber,
        correct,
        incorrect,
        scoredPicks: scored.length,
        winRate: scored.length > 0 ? correct / scored.length : null,
        totalPoints,
      }
    })
}

function computeConfidenceStats(weeks: HistoricalWeek[]): ConfidenceStat[] {
  const byConfidence = new Map<number, ConfidenceStat>()
  for (const week of weeks) {
    for (const pick of week.picks) {
      if (pick.outcome !== 'correct') continue
      const entry = byConfidence.get(pick.confidence) ?? {
        confidence: pick.confidence,
        correct: 0,
      }
      entry.correct += 1
      byConfidence.set(pick.confidence, entry)
    }
  }
  return [...byConfidence.values()].sort((left, right) => right.confidence - left.confidence)
}

function formatWinRate(winRate: number | null): string {
  return winRate === null ? '—' : `${Math.round(winRate * 100)}%`
}

function SeasonStats({ weeks }: { weeks: HistoricalWeek[] }) {
  const weekStats = useMemo(() => computeWeekStats(weeks), [weeks])
  const confidenceStats = useMemo(() => computeConfidenceStats(weeks), [weeks])
  const weeksWithScoring = weekStats.filter((week) => week.scoredPicks > 0)

  if (weeksWithScoring.length === 0) return null

  const totalCorrect = weeksWithScoring.reduce((sum, week) => sum + week.correct, 0)
  const totalScored = weeksWithScoring.reduce((sum, week) => sum + week.scoredPicks, 0)
  const seasonWinRate = totalScored > 0 ? totalCorrect / totalScored : null
  const averageWeeklyPoints =
    weeksWithScoring.reduce((sum, week) => sum + week.totalPoints, 0) / weeksWithScoring.length
  const confidenceHistogramData = [...confidenceStats].sort(
    (left, right) => left.confidence - right.confidence,
  )

  return (
    <section
      className="space-y-5 rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dev-dark:border-border dark:bg-slate-900 dev-dark:bg-surface-elevated"
      aria-labelledby="season-stats-heading"
    >
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Season stats</p>
        <h2
          id="season-stats-heading"
          className="mt-1 text-xl font-black text-primary dark:text-white dev-dark:text-ink"
        >
          Your season so far
        </h2>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800 dev-dark:border-border">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
            Season win rate
          </p>
          <p className="mt-1 text-2xl font-black text-primary dark:text-white dev-dark:text-ink">
            {formatWinRate(seasonWinRate)}
          </p>
          <p className="text-xs text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
            {totalCorrect} of {totalScored} scored picks
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800 dev-dark:border-border">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
            Average weekly points
          </p>
          <p className="mt-1 text-2xl font-black text-primary dark:text-white dev-dark:text-ink">
            {averageWeeklyPoints.toFixed(1)}
          </p>
          <p className="text-xs text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
            Across {weeksWithScoring.length} scored week{weeksWithScoring.length === 1 ? '' : 's'}
          </p>
        </div>
      </div>

      <div>
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
          Win rate per week
        </p>
        <ul className="mt-2 space-y-1.5">
          {weeksWithScoring.map((week) => (
            <li key={week.weekNumber} className="flex items-center gap-3 text-sm">
              <span className="w-16 shrink-0 font-bold">Week {week.weekNumber}</span>
              <div
                className="h-3 flex-1 overflow-hidden rounded-full bg-surface-muted dark:bg-slate-800 dev-dark:bg-surface-hover"
                role="img"
                aria-label={`Week ${week.weekNumber}: ${formatWinRate(week.winRate)} win rate`}
              >
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${(week.winRate ?? 0) * 100}%` }}
                />
              </div>
              <span className="w-12 shrink-0 text-right text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
                {formatWinRate(week.winRate)}
              </span>
              <span className="w-16 shrink-0 text-right font-bold text-accent">
                {week.totalPoints} pts
              </span>
            </li>
          ))}
        </ul>
      </div>

      {confidenceHistogramData.length > 0 && (
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
            Confidence point histogram
          </p>
          <div
            className="mt-2 h-64"
            role="img"
            aria-label={`Confidence point histogram: ${confidenceHistogramData
              .map((stat) => `confidence ${stat.confidence}, ${stat.correct} correct`)
              .join('; ')}`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={confidenceHistogramData}
                margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} className="opacity-20" />
                <XAxis
                  dataKey="confidence"
                  label={{ value: 'Confidence value', position: 'insideBottom', offset: -4 }}
                  tickLine={false}
                  fontSize={12}
                />
                <YAxis
                  allowDecimals={false}
                  label={{ value: 'Times used', angle: -90, position: 'insideLeft' }}
                  tickLine={false}
                  fontSize={12}
                  width={36}
                />
                <Tooltip
                  formatter={(value) => [value, 'Correct']}
                  labelFormatter={(confidence) => `Confidence ${confidence}`}
                />
                <Bar
                  dataKey="correct"
                  fill="var(--color-success)"
                  name="Correct"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </section>
  )
}

export function ProfilePage() {
  const historyQuery = useQuery({
    queryKey: ['picks', 'history'],
    queryFn: fetchPickHistory,
    staleTime: 10 * 60_000,
  })
  const [requestedWeek, setRequestedWeek] = useState<number | null>(null)
  const availableWeeks = historyQuery.data
    ? [...historyQuery.data.weeks].sort((left, right) => left.weekNumber - right.weekNumber)
    : []
  const latestWeekNumber = availableWeeks.at(-1)?.weekNumber ?? null
  const selectedWeekNumber = availableWeeks.some((week) => week.weekNumber === requestedWeek)
    ? requestedWeek
    : latestWeekNumber
  const selectedWeek = availableWeeks.find((week) => week.weekNumber === selectedWeekNumber)

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Your record</p>
        <h1 className="mt-2 flex items-center gap-2 text-3xl font-black tracking-tight text-primary dark:text-white dev-dark:text-ink">
          <UserRound className="text-sky" size={25} aria-hidden="true" /> Profile
        </h1>
      </div>
      {historyQuery.isPending && (
        <p
          aria-live="polite"
          className="text-slate-600 dark:text-slate-300 dev-dark:text-text-secondary"
        >
          Loading your pick history...
        </p>
      )}
      {historyQuery.error && (
        <p role="alert" className="text-danger">
          {historyQuery.error instanceof ApiError && historyQuery.error.status === 404
            ? 'No pick history is available.'
            : 'Could not load your pick history.'}
        </p>
      )}
      {historyQuery.data && historyQuery.data.weeks.length === 0 && (
        <div className="rounded-2xl border border-slate-200 bg-surface p-8 text-center shadow-sm dark:border-slate-800 dev-dark:border-border dark:bg-slate-900 dev-dark:bg-surface-elevated">
          <UserRound className="mx-auto text-sky" size={40} aria-hidden="true" />
          <h2 className="mt-4 text-xl font-bold">No picks submitted yet.</h2>
          <p className="mt-2 text-slate-600 dark:text-slate-300 dev-dark:text-text-secondary">
            Your current and completed-week picks will appear here.
          </p>
        </div>
      )}
      {historyQuery.data && historyQuery.data.weeks.length > 0 && (
        <SeasonStats weeks={historyQuery.data.weeks} />
      )}
      {selectedWeek && (
        <section className="space-y-3" aria-labelledby={`history-week-${selectedWeek.weekNumber}`}>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <label
                htmlFor="profile-week"
                className="block text-xs font-bold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400 dev-dark:text-text-muted"
              >
                Review week
              </label>
              <select
                id="profile-week"
                value={selectedWeekNumber ?? ''}
                onChange={(event) => setRequestedWeek(Number(event.target.value))}
                className="mt-2 min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold text-ink dark:border-slate-700 dev-dark:border-border-hover dark:bg-slate-950 dev-dark:bg-background dark:text-slate-100 dev-dark:text-ink"
              >
                {availableWeeks.map((week) => (
                  <option key={week.weekNumber} value={week.weekNumber}>
                    Week {week.weekNumber}
                  </option>
                ))}
              </select>
            </div>
            <h2
              id={`history-week-${selectedWeek.weekNumber}`}
              className="text-xl font-black text-primary dark:text-white dev-dark:text-ink"
            >
              Week {selectedWeek.weekNumber}
            </h2>
          </div>
          <HistoryTable picks={selectedWeek.picks} />
        </section>
      )}
    </div>
  )
}
