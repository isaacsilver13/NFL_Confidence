import { useState } from 'react'
import { ArrowUpRight, CalendarDays, Users } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { createLeague, fetchLeague } from '@/api/league'
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
      await queryClient.invalidateQueries({ queryKey: ['league'] })
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

export function DashboardPage() {
  const navigate = useNavigate()
  const {
    data: league,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['league'],
    queryFn: fetchLeague,
    retry: false,
  })

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
        {['Current week', 'My weekly rank', 'Season rank'].map((label) => (
          <div
            key={label}
            className="rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
              {label}
            </p>
            <p className="mt-4 text-2xl font-black text-primary dark:text-white">Coming soon</p>
          </div>
        ))}
      </div>
    </div>
  )
}
