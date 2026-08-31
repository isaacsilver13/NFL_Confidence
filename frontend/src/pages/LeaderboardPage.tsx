import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Trophy } from 'lucide-react'
import { ApiError } from '@/api/client'
import { fetchWeeklyLeaderboard } from '@/api/leaderboard'
import type { LeaderboardMember } from '@/types/leaderboard'

const DEMO_WEEKS = Array.from({ length: 10 }, (_, index) => index + 2)

function LeaderboardTable({ standings }: { standings: LeaderboardMember[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-surface shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <table className="w-full min-w-[680px] text-left text-sm">
        <caption className="sr-only">Weekly leaderboard rankings</caption>
        <thead className="bg-surface-muted text-xs uppercase tracking-[0.14em] text-ink-muted dark:bg-slate-950 dark:text-slate-400">
          <tr>
            <th className="px-5 py-4">Rank</th>
            <th className="px-5 py-4">Member</th>
            <th className="px-5 py-4 text-right">Points</th>
            <th className="px-5 py-4 text-right">Correct</th>
            <th className="px-5 py-4 text-right">Missed</th>
            <th className="px-5 py-4 text-right">Wins</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {standings.map((member) => (
            <tr
              key={member.memberId}
              className="transition-colors hover:bg-surface-muted/60 dark:hover:bg-slate-950/60"
            >
              <th scope="row" className="px-5 py-4 font-black text-primary dark:text-white">
                {member.rank}
              </th>
              <td className="px-5 py-4 font-bold">{member.memberName}</td>
              <td className="px-5 py-4 text-right font-black text-accent">{member.totalPoints}</td>
              <td className="px-5 py-4 text-right">{member.correctPicks}</td>
              <td className="px-5 py-4 text-right">{member.incorrectPicks}</td>
              <td className="px-5 py-4 text-right">{member.weeklyWins}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function LeaderboardPage() {
  const [week, setWeek] = useState(2)
  const query = useQuery({
    queryKey: ['leaderboard', 'week', week],
    queryFn: () => fetchWeeklyLeaderboard(week),
  })

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Weekly race</p>
          <h1 className="mt-2 flex items-center gap-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            <Trophy className="text-gold" size={25} aria-hidden="true" /> Leaderboard
          </h1>
        </div>
        <label className="flex items-center gap-3 text-sm font-bold text-ink-muted dark:text-slate-300">
          Week
          <select
            value={week}
            onChange={(event) => setWeek(Number(event.target.value))}
            className="min-h-11 rounded-xl border border-slate-300 bg-surface px-3 text-ink shadow-sm dark:border-slate-700 dark:bg-slate-900"
          >
            {DEMO_WEEKS.map((weekNumber) => (
              <option key={weekNumber} value={weekNumber}>
                Week {weekNumber}
              </option>
            ))}
          </select>
        </label>
      </div>

      {query.isPending && (
        <p className="text-slate-600 dark:text-slate-300" aria-live="polite">
          Loading weekly results...
        </p>
      )}
      {query.error && (
        <p className="text-danger" role="alert">
          {query.error instanceof ApiError && query.error.status === 404
            ? `Week ${week} has no completed results.`
            : 'Could not load the weekly leaderboard.'}
        </p>
      )}
      {query.data && query.data.standings.length === 0 && (
        <p className="text-slate-600 dark:text-slate-300">No completed results for this week.</p>
      )}
      {query.data && query.data.standings.length > 0 && (
        <LeaderboardTable standings={query.data.standings} />
      )}
    </div>
  )
}
