import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { createLeague, fetchLeague } from '@/api/league'

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
      <button
        type="submit"
        disabled={isSubmitting}
        className="min-h-11 w-full rounded-md bg-primary px-4 py-2 font-medium text-white transition-colors duration-150 hover:bg-primary-hover disabled:opacity-50"
      >
        {isSubmitting ? 'Creating…' : 'Create league'}
      </button>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}

export function DashboardPage() {
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
      <div className="animate-fade-in space-y-4">
        <h1 className="text-2xl font-bold">Welcome!</h1>
        <p className="text-slate-600 dark:text-slate-300">
          No league has been created yet. Create one to get started.
        </p>
        <CreateLeagueForm />
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      {league && (
        <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-slate-900">
          <p className="text-lg font-semibold">{league.name}</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Season {league.season} · {league.memberCount} member
            {league.memberCount === 1 ? '' : 's'} · Commissioner {league.commissionerName}
          </p>
        </div>
      )}
      <p className="text-slate-600 dark:text-slate-300">
        Current week countdown, weekly/season rank, and upcoming games will appear here.
      </p>
    </div>
  )
}
