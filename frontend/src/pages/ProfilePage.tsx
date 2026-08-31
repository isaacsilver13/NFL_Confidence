import { useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, UserRound } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { fetchPickHistory } from '@/api/nfl'
import type { HistoricalPick, PickOutcome } from '@/types/nfl'

const OUTCOME_LABELS: Record<PickOutcome, string> = {
  correct: 'Correct',
  incorrect: 'Incorrect',
  unscored: 'Not scored',
}

type SortKey = 'game' | 'team' | 'confidence' | 'outcome' | 'points'
type SortDirection = 'ascending' | 'descending'

const OUTCOME_ORDER: Record<PickOutcome, number> = { unscored: 0, incorrect: 1, correct: 2 }

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
        : 'text-ink-muted dark:text-slate-400'
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
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
      <table className="w-full min-w-[760px] text-left text-sm">
        <caption className="sr-only">Your picks</caption>
        <thead className="bg-surface-muted text-xs uppercase tracking-[0.14em] text-ink-muted dark:bg-slate-950 dark:text-slate-400">
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
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {sortedPicks.map((pick) => (
            <tr key={pick.id}>
              <th scope="row" className="px-4 py-3 font-semibold">
                {pick.awayTeam} at {pick.homeTeam}
                <span className="block text-xs font-normal text-ink-muted dark:text-slate-400">
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
        className="inline-flex items-center gap-1 font-bold hover:text-primary dark:hover:text-white"
      >
        <span>{label}</span>
        <Icon size={14} aria-hidden="true" />
      </button>
    </th>
  )
}

export function ProfilePage() {
  const historyQuery = useQuery({ queryKey: ['picks', 'history'], queryFn: fetchPickHistory })
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
        <h1 className="mt-2 flex items-center gap-2 text-3xl font-black tracking-tight text-primary dark:text-white">
          <UserRound className="text-sky" size={25} aria-hidden="true" /> Profile
        </h1>
      </div>
      {historyQuery.isPending && (
        <p aria-live="polite" className="text-slate-600 dark:text-slate-300">
          Loading your pick history...
        </p>
      )}
      {historyQuery.error && (
        <p role="alert" className="text-danger">
          {historyQuery.error instanceof ApiError && historyQuery.error.status === 404
            ? 'No completed pick history is available.'
            : 'Could not load your pick history.'}
        </p>
      )}
      {historyQuery.data && historyQuery.data.weeks.length === 0 && (
        <div className="rounded-2xl border border-slate-200 bg-surface p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <UserRound className="mx-auto text-sky" size={40} aria-hidden="true" />
          <h2 className="mt-4 text-xl font-bold">No completed picks yet.</h2>
          <p className="mt-2 text-slate-600 dark:text-slate-300">
            Your completed-week picks will appear here.
          </p>
        </div>
      )}
      {selectedWeek && (
        <section className="space-y-3" aria-labelledby={`history-week-${selectedWeek.weekNumber}`}>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <label
                htmlFor="profile-week"
                className="block text-xs font-bold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400"
              >
                Review week
              </label>
              <select
                id="profile-week"
                value={selectedWeekNumber ?? ''}
                onChange={(event) => setRequestedWeek(Number(event.target.value))}
                className="mt-2 min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold text-ink dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
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
              className="text-xl font-black text-primary dark:text-white"
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
