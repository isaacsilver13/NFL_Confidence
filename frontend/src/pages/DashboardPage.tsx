import { useState } from 'react'
import { ArrowUpRight, CalendarDays, KeyRound, Users } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { createLeague, joinLeagueWithCode } from '@/api/league'
import { fetchSessionBootstrap } from '@/api/session'
import { fetchWeeklyLeaderboard, fetchSeasonStandings } from '@/api/leaderboard'
import { Button } from '@/components/ui/Button'

const CURRENT_SEASON = new Date().getFullYear()

function CreateLeagueForm() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [season, setSeason] = useState(CURRENT_SEASON)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await createLeague({ name: name.trim(), season })
      await queryClient.invalidateQueries({ queryKey: ['session', 'bootstrap'] })
    } catch {
      setError('Could not create the league. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="max-w-sm space-y-4">
      <div>
        <label htmlFor="league-name" className="mb-1 block text-sm font-medium">
          League name
        </label>
        <input
          id="league-name"
          type="text"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <div>
        <label htmlFor="league-season" className="mb-1 block text-sm font-medium">
          Season
        </label>
        <input
          id="league-season"
          type="number"
          required
          value={season}
          onChange={(event) => setSeason(Number(event.target.value))}
          className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <Button type="submit" disabled={isSubmitting} fullWidth>
        {isSubmitting ? 'Creating…' : 'Create league'}
      </Button>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}

function JoinLeagueForm() {
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await joinLeagueWithCode(code.trim())
      await queryClient.invalidateQueries({ queryKey: ['session', 'bootstrap'] })
    } catch {
      setError('That league passcode is invalid. Please check it and try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="max-w-sm space-y-4">
      <div>
        <label htmlFor="league-passcode" className="mb-1 block text-sm font-medium">
          League passcode
        </label>
        <input
          id="league-passcode"
          type="text"
          required
          value={code}
          onChange={(event) => setCode(event.target.value)}
          className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <Button type="submit" disabled={isSubmitting} fullWidth>
        <KeyRound size={16} aria-hidden="true" />
        {isSubmitting ? 'Joining…' : 'Join league'}
      </Button>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const {
    data: bootstrapData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['session', 'bootstrap'],
    queryFn: fetchSessionBootstrap,
    retry: false,
  })

  const league = bootstrapData?.league ?? null
  const currentWeek = bootstrapData?.currentWeek ?? null
  const user = bootstrapData?.user

  // Fetch leaderboard data for current week if we have a league and week
  const { data: weeklyLeaderboard, isLoading: isWeeklyLoading } = useQuery({
    queryKey: ['leaderboard', 'week', currentWeek?.weekNumber],
    queryFn: () => fetchWeeklyLeaderboard(currentWeek?.weekNumber),
    enabled: Boolean(league && currentWeek),
    retry: false,
  })

  // Fetch season standings if we have a league
  const { data: seasonStandings, isLoading: isSeasonLoading } = useQuery({
    queryKey: ['leaderboard', 'season'],
    queryFn: () => fetchSeasonStandings(),
    enabled: Boolean(league),
    retry: false,
  })

  // Find user's rank in weekly leaderboard
  const weeklyRank =
    weeklyLeaderboard && user
      ? (weeklyLeaderboard.standings.findIndex(
          (entry: { memberId: string }) => entry.memberId === user.id,
        ) ?? -1) + 1
      : null
  const displayWeeklyRank = weeklyRank && weeklyRank > 0 ? `#${weeklyRank}` : 'Not scored'

  // Find user's rank in season standings
  const seasonRank =
    seasonStandings && user
      ? (seasonStandings.standings.findIndex(
          (entry: { memberId: string }) => entry.memberId === user.id,
        ) ?? -1) + 1
      : null
  const displaySeasonRank = seasonRank && seasonRank > 0 ? `#${seasonRank}` : 'Not scored'

  if (isLoading) {
    return null
  }

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="animate-fade-in space-y-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">
            Your season starts here
          </p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            Welcome to the pool.
          </h1>
        </div>
        <p className="text-slate-600 dark:text-slate-300">
          No league has been created yet. Create one to get started.
        </p>
        <div className="max-w-md rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <CreateLeagueForm />
        </div>
      </div>
    )
  }

  if (!league) {
    return (
      <div className="animate-fade-in space-y-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">League access</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            Join your pool.
          </h1>
        </div>
        <p className="text-slate-600 dark:text-slate-300">
          Ask the commissioner for the league passcode to join.
        </p>
        <div className="max-w-md rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <JoinLeagueForm />
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">League hub</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            Dashboard
          </h1>
        </div>
        <Button variant="secondary" onClick={() => void navigate('/picks')}>
          Make picks <ArrowUpRight size={16} aria-hidden="true" />
        </Button>
      </div>
      {league && (
        <div className="overflow-hidden rounded-2xl border border-primary/10 bg-primary p-5 text-white shadow-lg shadow-primary/15">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky">
            {league.season} season
          </p>
          <p className="mt-2 text-2xl font-black">{league.name}</p>
          <div className="mt-5 flex flex-wrap gap-3 text-sm text-slate-200">
            <span className="inline-flex items-center gap-2">
              <Users size={16} aria-hidden="true" /> {league.memberCount} member
              {league.memberCount === 1 ? '' : 's'}
            </span>
            <span className="inline-flex items-center gap-2">
              <CalendarDays size={16} aria-hidden="true" /> Commissioner {league.commissionerName}
            </span>
          </div>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ['Current week', currentWeek ? `Week ${currentWeek.weekNumber}` : 'Unavailable'],
          ['My weekly rank', isWeeklyLoading ? 'Loading…' : displayWeeklyRank],
          ['Season rank', isSeasonLoading ? 'Loading…' : displaySeasonRank],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
              {label}
            </p>
            <p className="mt-4 text-2xl font-black text-primary dark:text-white">{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
