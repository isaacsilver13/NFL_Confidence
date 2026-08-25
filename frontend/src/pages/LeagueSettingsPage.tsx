import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createInvite, fetchLeague, fetchLeagueMembers } from '@/api/league'
import { useAuth } from '@/features/auth/AuthContext'

function InviteForm({ onInvited }: { onInvited: () => void }) {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSuccessMessage(null)
    setIsSubmitting(true)
    try {
      const invite = await createInvite(email.trim())
      setSuccessMessage(`Invite sent to ${invite.email}.`)
      setEmail('')
      onInvited()
    } catch {
      setError('Could not send the invite. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="max-w-sm space-y-3">
      <div>
        <label htmlFor="invite-email" className="mb-1 block text-sm font-medium">
          Invite by email
        </label>
        <input
          id="invite-email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <button
        type="submit"
        disabled={isSubmitting}
        className="min-h-11 rounded-md bg-primary px-4 py-2 font-medium text-white transition-colors duration-150 hover:bg-primary-hover disabled:opacity-50"
      >
        {isSubmitting ? 'Sending…' : 'Send invite'}
      </button>
      {successMessage && <p className="text-sm text-green-600 dark:text-green-400">{successMessage}</p>}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}

export function LeagueSettingsPage() {
  const { user } = useAuth()
  const { data: league, isLoading: isLoadingLeague } = useQuery({
    queryKey: ['league'],
    queryFn: fetchLeague,
    retry: false,
  })
  const { data: members } = useQuery({
    queryKey: ['league', 'members'],
    queryFn: fetchLeagueMembers,
    enabled: !!league,
  })
  const queryClient = useQueryClient()

  if (isLoadingLeague) {
    return null
  }

  if (!league) {
    return (
      <div className="animate-fade-in space-y-4">
        <h1 className="text-2xl font-bold">League Settings</h1>
        <p className="text-slate-600 dark:text-slate-300">
          Create a league from the dashboard before configuring settings.
        </p>
      </div>
    )
  }

  const isCommissioner =
    !!user && !!members?.some((member) => member.userId === user.id && member.role === 'owner')

  return (
    <div className="animate-fade-in space-y-6">
      <h1 className="text-2xl font-bold">League Settings</h1>
      <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-slate-900">
        <p className="text-lg font-semibold">{league.name}</p>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Season {league.season} · Commissioner {league.commissionerName}
        </p>
      </div>

      {isCommissioner && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Invite members</h2>
          <InviteForm
            onInvited={() => void queryClient.invalidateQueries({ queryKey: ['league', 'members'] })}
          />
        </div>
      )}

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Members</h2>
        <ul className="divide-y divide-slate-200 rounded-lg bg-white shadow-sm dark:divide-slate-800 dark:bg-slate-900">
          {members?.map((member) => (
            <li key={member.id} className="flex items-center justify-between px-4 py-3">
              <span>{member.displayName}</span>
              <span className="text-sm capitalize text-slate-500 dark:text-slate-400">
                {member.role}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
