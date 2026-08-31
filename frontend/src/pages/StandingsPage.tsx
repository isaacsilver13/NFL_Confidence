import { useQuery } from '@tanstack/react-query'
import { BarChart3 } from 'lucide-react'
import { ApiError } from '@/api/client'
import { fetchPickBreakdown, fetchSeasonStandings } from '@/api/leaderboard'
import { WeeklyPickBreakdown } from '@/components/leaderboard/WeeklyPickBreakdown'
import type { LeaderboardMember } from '@/types/leaderboard'

function StandingsTable({ standings }: { standings: LeaderboardMember[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-surface shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <table className="w-full min-w-[760px] text-left text-sm">
        <caption className="sr-only">Season standings</caption>
        <thead className="bg-surface-muted text-xs uppercase tracking-[0.14em] text-ink-muted dark:bg-slate-950 dark:text-slate-400">
          <tr>
            <th className="px-5 py-4">Rank</th>
            <th className="px-5 py-4">Member</th>
            <th className="px-5 py-4 text-right">Points</th>
            <th className="px-5 py-4 text-right">Weekly wins</th>
            <th className="px-5 py-4 text-right">Podiums</th>
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
              <td className="px-5 py-4 text-right">{member.weeklyWins}</td>
              <td className="px-5 py-4 text-right">
                {member.firstPlaceFinishes + member.secondPlaceFinishes + member.thirdPlaceFinishes}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function StandingsPage() {
  const seasonQuery = useQuery({
    queryKey: ['leaderboard', 'season'],
    queryFn: () => fetchSeasonStandings(),
  })
  const breakdownQuery = useQuery({
    queryKey: ['leaderboard', 'pick-breakdown'],
    queryFn: fetchPickBreakdown,
  })
  const isLoading = seasonQuery.isPending || breakdownQuery.isPending
  const error = seasonQuery.error ?? breakdownQuery.error

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Long game</p>
        <h1 className="mt-2 flex items-center gap-2 text-3xl font-black tracking-tight text-primary dark:text-white">
          <BarChart3 className="text-sky" size={25} aria-hidden="true" /> Season standings
        </h1>
      </div>

      {isLoading && (
        <p aria-live="polite" className="text-slate-600 dark:text-slate-300">
          Loading season standings...
        </p>
      )}
      {error && (
        <p role="alert" className="text-danger">
          {error instanceof ApiError && error.status === 404
            ? 'No completed standings or pick data are available.'
            : 'Could not load standings and pick data.'}
        </p>
      )}
      {seasonQuery.data && seasonQuery.data.standings.length === 0 && (
        <p className="text-slate-600 dark:text-slate-300">
          No completed season results are available.
        </p>
      )}
      {seasonQuery.data && seasonQuery.data.standings.length > 0 && (
        <StandingsTable standings={seasonQuery.data.standings} />
      )}

      <section
        className="space-y-5 rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        aria-labelledby="breakdown-heading"
      >
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">League picks</p>
          <h2
            id="breakdown-heading"
            className="mt-1 text-xl font-black text-primary dark:text-white"
          >
            Weekly breakdown
          </h2>
        </div>
        {breakdownQuery.data && <WeeklyPickBreakdown weeks={breakdownQuery.data.weeks} />}
      </section>
    </div>
  )
}
