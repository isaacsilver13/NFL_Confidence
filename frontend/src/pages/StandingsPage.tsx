import { useQuery } from '@tanstack/react-query'
import { BarChart3 } from 'lucide-react'
import { ApiError } from '@/api/client'
import { fetchSeasonStandings } from '@/api/leaderboard'
import { SortableTh } from '@/components/ui/SortableTable'
import { useTableSort } from '@/components/ui/useTableSort'
import type { LeaderboardMember } from '@/types/leaderboard'

function StandingsTable({ standings }: { standings: LeaderboardMember[] }) {
  const sort = useTableSort(standings, {
    rank: { value: (m) => m.rank, numeric: false },
    member: { value: (m) => m.memberName },
    points: { value: (m) => m.totalPoints, numeric: true },
    wins: { value: (m) => m.weeklyWins, numeric: true },
    podiums: {
      value: (m) => m.firstPlaceFinishes + m.secondPlaceFinishes + m.thirdPlaceFinishes,
      numeric: true,
    },
  })
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-surface shadow-sm dark:border-slate-800 dev-dark:border-border dark:bg-slate-900 dev-dark:bg-surface-elevated">
      <table className="w-full min-w-[760px] text-left text-sm">
        <caption className="sr-only">Season standings</caption>
        <thead className="bg-surface-muted text-xs uppercase tracking-[0.14em] text-ink-muted dark:bg-slate-950 dev-dark:bg-background dark:text-slate-400 dev-dark:text-text-muted">
          <tr>
            <SortableTh label="Rank" columnKey="rank" sort={sort} />
            <SortableTh label="Member" columnKey="member" sort={sort} />
            <SortableTh label="Points" columnKey="points" sort={sort} align="right" />
            <SortableTh label="Weekly wins" columnKey="wins" sort={sort} align="right" />
            <SortableTh label="Podiums" columnKey="podiums" sort={sort} align="right" />
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
    staleTime: 10 * 60_000,
  })
  const isLoading = seasonQuery.isPending
  const error = seasonQuery.error

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Long game</p>
        <h1 className="mt-2 flex items-center gap-2 text-3xl font-black tracking-tight text-primary dark:text-white dev-dark:text-ink">
          <BarChart3 className="text-sky" size={25} aria-hidden="true" /> Season standings
        </h1>
      </div>

      {isLoading && (
        <p
          aria-live="polite"
          className="text-slate-600 dark:text-slate-300 dev-dark:text-text-secondary"
        >
          Loading season standings...
        </p>
      )}
      {error && (
        <p role="alert" className="text-danger">
          {error instanceof ApiError && error.status === 404
            ? 'No completed standings are available.'
            : 'Could not load standings.'}
        </p>
      )}
      {seasonQuery.data && seasonQuery.data.standings.length === 0 && (
        <p className="text-slate-600 dark:text-slate-300 dev-dark:text-text-secondary">
          No completed season results are available.
        </p>
      )}
      {seasonQuery.data && seasonQuery.data.standings.length > 0 && (
        <StandingsTable standings={seasonQuery.data.standings} />
      )}
    </div>
  )
}
