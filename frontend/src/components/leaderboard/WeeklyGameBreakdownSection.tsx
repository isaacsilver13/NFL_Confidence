import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPickBreakdown } from '@/api/leaderboard'
import { fetchStartedWeeks } from '@/api/nfl'
import { WeeklyPickBreakdown } from '@/components/leaderboard/WeeklyPickBreakdown'

const mutedText = 'text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted'

export function WeeklyGameBreakdownSection() {
  const [week, setWeek] = useState<number>()
  const weeksQuery = useQuery({
    queryKey: ['leaderboard', 'weeks', 'started'],
    queryFn: fetchStartedWeeks,
    staleTime: 10 * 60_000,
  })
  const breakdownQuery = useQuery({
    queryKey: ['leaderboard', 'pick-breakdown'],
    queryFn: fetchPickBreakdown,
    staleTime: 10 * 60_000,
  })
  // The breakdown exists once a week's picks are locked (first kickoff), so offer exactly those.
  const weekNumbers = (weeksQuery.data ?? []).map((started) => started.weekNumber)
  const selectedWeek = week ?? weekNumbers.at(-1)
  const weekBreakdown = breakdownQuery.data?.weeks.find(
    (entry) => entry.weekNumber === selectedWeek,
  )
  const isPending = weeksQuery.isPending || breakdownQuery.isPending

  return (
    <div className="animate-fade-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">League picks</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white dev-dark:text-ink">
            Weekly Game Breakdown
          </h1>
        </div>
        {weekNumbers.length > 0 && (
          <label className="flex items-center gap-3 text-sm font-bold text-ink-muted dark:text-slate-300 dev-dark:text-text-secondary">
            Week
            <select
              value={selectedWeek ?? ''}
              onChange={(event) => setWeek(Number(event.target.value))}
              className="min-h-11 rounded-xl border border-slate-300 bg-surface px-3 text-ink shadow-sm dark:border-slate-700 dev-dark:border-border-hover dark:bg-slate-900 dev-dark:bg-surface-elevated dark:text-slate-100 dev-dark:text-ink"
            >
              {weekNumbers.map((weekNumber) => (
                <option key={weekNumber} value={weekNumber}>
                  Week {weekNumber}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {isPending && (
        <p className={mutedText} aria-live="polite">
          Loading pick breakdown...
        </p>
      )}
      {(weeksQuery.error || breakdownQuery.error) && (
        <p className="text-sm text-danger" role="alert">
          Could not load the pick breakdown.
        </p>
      )}
      {!isPending && !weeksQuery.error && !breakdownQuery.error && selectedWeek === undefined && (
        <p className={mutedText}>The breakdown appears once a week is locked.</p>
      )}
      {!isPending && !breakdownQuery.error && selectedWeek !== undefined && !weekBreakdown && (
        <p className={mutedText}>
          Pick breakdown isn&apos;t available until Week {selectedWeek} is locked.
        </p>
      )}
      {weekBreakdown && <WeeklyPickBreakdown games={weekBreakdown.games} />}
    </div>
  )
}
