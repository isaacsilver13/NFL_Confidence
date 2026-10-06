import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Trophy } from 'lucide-react'
import { ApiError } from '@/api/client'
import { fetchWeeklyLeaderboard } from '@/api/leaderboard'
import { fetchCurrentWeek, fetchStartedWeeks } from '@/api/nfl'
import { LastRefreshed } from '@/components/nfl/LastRefreshed'
import { AllPicksModal } from '@/components/leaderboard/AllPicksModal'
import { OutcomeScenariosModal } from '@/components/leaderboard/OutcomeScenariosModal'
import { Button } from '@/components/ui/Button'
import { SortableTh } from '@/components/ui/SortableTable'
import { useTableSort } from '@/components/ui/useTableSort'
import type { GameLabel, LeaderboardMember, MemberGamePick } from '@/types/leaderboard'

interface WeekOption {
  weekNumber: number
  isCurrent: boolean
}

function buildWeekOptions(
  completedWeeks: { weekNumber: number }[],
  currentWeekNumber: number | undefined,
): WeekOption[] {
  const options = completedWeeks.map((week) => ({ weekNumber: week.weekNumber, isCurrent: false }))
  if (currentWeekNumber !== undefined && !options.some((o) => o.weekNumber === currentWeekNumber)) {
    options.push({ weekNumber: currentWeekNumber, isCurrent: true })
  }
  return options.sort((a, b) => a.weekNumber - b.weekNumber)
}

function formatPicksRemaining(picks: MemberGamePick[]): string {
  const formatted = picks
    .filter((pick) => pick.team && pick.confidence !== null)
    .map((pick) => `${pick.team} (${pick.confidence})`)
  return formatted.length > 0 ? formatted.join(', ') : '—'
}

function LeaderboardTable({
  standings,
  nightGames,
}: {
  standings: LeaderboardMember[]
  nightGames: GameLabel[]
}) {
  // The backend sends night games only once Sunday night has kicked off.
  const showPicksRemaining = nightGames.length > 0
  const sort = useTableSort(standings, {
    rank: { value: (m) => m.rank },
    member: { value: (m) => m.memberName },
    correct: { value: (m) => m.correctPicks, numeric: true },
    points: { value: (m) => m.totalPoints, numeric: true },
    // Confidence points still riding on the night games.
    nightGames: {
      value: (m) =>
        m.nightGamePicks.length === 0
          ? null
          : m.nightGamePicks.reduce((sum, pick) => sum + (pick.confidence ?? 0), 0),
      numeric: true,
    },
  })
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-surface shadow-sm dark:border-slate-800 dev-dark:border-border dark:bg-slate-900 dev-dark:bg-surface-elevated">
      <table className="w-full min-w-[680px] text-left text-sm">
        <caption className="sr-only">Weekly leaderboard rankings</caption>
        <thead className="bg-surface-muted text-xs uppercase tracking-[0.14em] text-ink-muted dark:bg-slate-950 dev-dark:bg-background dark:text-slate-400 dev-dark:text-text-muted">
          <tr>
            <SortableTh label="Rank" columnKey="rank" sort={sort} />
            <SortableTh label="Member" columnKey="member" sort={sort} />
            <SortableTh label="Correct" columnKey="correct" sort={sort} align="right" />
            <SortableTh label="Points" columnKey="points" sort={sort} align="right" />
            {showPicksRemaining && (
              <SortableTh
                label="SNF/MNF"
                columnKey="nightGames"
                sort={sort}
                align="right"
                className="px-5 py-4 whitespace-nowrap"
              />
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800 dev-dark:divide-border">
          {sort.sortedRows.map((member) => (
            <tr
              key={member.memberId}
              className="transition-colors hover:bg-surface-muted/60 dark:hover:bg-slate-950/60 dev-dark:hover:bg-surface-hover"
            >
              <th
                scope="row"
                className="px-5 py-4 font-black text-primary dark:text-white dev-dark:text-ink"
              >
                {member.rank}
              </th>
              <td className="px-5 py-4 font-bold">{member.memberName}</td>
              <td className="px-5 py-4 text-right">{member.correctPicks}</td>
              <td className="px-5 py-4 text-right font-black text-accent">{member.totalPoints}</td>
              {showPicksRemaining && (
                <td className="px-5 py-4 text-right whitespace-nowrap">
                  {formatPicksRemaining(member.nightGamePicks)}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function LeaderboardPage() {
  const [week, setWeek] = useState<number>()
  const [showAllPicks, setShowAllPicks] = useState(false)
  const [showOutcomeScenarios, setShowOutcomeScenarios] = useState(false)
  const weeksQuery = useQuery({
    queryKey: ['leaderboard', 'weeks', 'started'],
    queryFn: fetchStartedWeeks,
    staleTime: 10 * 60_000,
  })
  const currentWeekQuery = useQuery({
    queryKey: ['weeks', 'current'],
    queryFn: fetchCurrentWeek,
    staleTime: 60_000,
  })
  const completedWeeks = weeksQuery.data ?? []
  const weekOptions = buildWeekOptions(completedWeeks, currentWeekQuery.data?.weekNumber)
  const selectedWeek = week ?? currentWeekQuery.data?.weekNumber ?? weekOptions.at(-1)?.weekNumber
  const query = useQuery({
    queryKey: ['leaderboard', 'week', selectedWeek],
    queryFn: () => fetchWeeklyLeaderboard(selectedWeek as number),
    enabled: selectedWeek !== undefined,
    staleTime: 10 * 60_000,
  })
  const canShowOutcomeScenarios =
    selectedWeek === currentWeekQuery.data?.weekNumber &&
    query.data?.outcomeScenariosAvailable === true

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Weekly race</p>
          <h1 className="mt-2 flex items-center gap-2 text-3xl font-black tracking-tight text-primary dark:text-white dev-dark:text-ink">
            <Trophy className="text-gold" size={25} aria-hidden="true" /> Weekly Leaderboard
          </h1>
          <LastRefreshed className="mt-1" />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {query.data && query.data.standings.length > 0 && query.data.picksRevealed && (
            <Button type="button" variant="secondary" onClick={() => setShowAllPicks(true)}>
              See everyone&apos;s picks
            </Button>
          )}
          {canShowOutcomeScenarios && (
            <Button type="button" variant="secondary" onClick={() => setShowOutcomeScenarios(true)}>
              See possible finishes
            </Button>
          )}
          <label className="flex items-center gap-3 text-sm font-bold text-ink-muted dark:text-slate-300 dev-dark:text-text-secondary">
            Week
            <select
              value={selectedWeek ?? ''}
              onChange={(event) => setWeek(Number(event.target.value))}
              className="min-h-11 rounded-xl border border-slate-300 bg-surface px-3 text-ink shadow-sm dark:border-slate-700 dev-dark:border-border-hover dark:bg-slate-900 dev-dark:bg-surface-elevated dark:text-slate-100 dev-dark:text-ink"
            >
              {weekOptions.map(({ weekNumber, isCurrent }) => (
                <option key={weekNumber} value={weekNumber}>
                  Week {weekNumber}
                  {isCurrent ? ' — Live' : ''}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      {showAllPicks && selectedWeek !== undefined && (
        <AllPicksModal week={selectedWeek} onClose={() => setShowAllPicks(false)} />
      )}
      {showOutcomeScenarios && selectedWeek !== undefined && (
        <OutcomeScenariosModal week={selectedWeek} onClose={() => setShowOutcomeScenarios(false)} />
      )}

      {selectedWeek === undefined && !weeksQuery.isPending && !currentWeekQuery.isPending && (
        <p className="text-slate-600 dark:text-slate-300 dev-dark:text-text-secondary">
          No weeks available yet.
        </p>
      )}
      {selectedWeek !== undefined && query.isPending && (
        <p
          className="text-slate-600 dark:text-slate-300 dev-dark:text-text-secondary"
          aria-live="polite"
        >
          Loading weekly results...
        </p>
      )}
      {query.error && (
        <p className="text-danger" role="alert">
          {query.error instanceof ApiError && query.error.status === 404
            ? `Week ${selectedWeek ?? ''} has no completed results.`
            : 'Could not load the weekly leaderboard.'}
        </p>
      )}
      {query.data && query.data.standings.length === 0 && (
        <p className="text-slate-600 dark:text-slate-300 dev-dark:text-text-secondary">
          No completed results for this week.
        </p>
      )}
      {query.data && query.data.standings.length > 0 && (
        <LeaderboardTable standings={query.data.standings} nightGames={query.data.nightGames} />
      )}
    </div>
  )
}
