import { useState } from 'react'
import { KeyRound, Mail, ShieldCheck, UserMinus, Users } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createInvite,
  fetchLeague,
  fetchLeagueMembers,
  removeLeagueMember,
} from '@/api/league'
import { Button } from '@/components/ui/Button'
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
      <Button type="submit" disabled={isSubmitting}>
        <Mail size={16} aria-hidden="true" />
        {isSubmitting ? 'Sending…' : 'Send invite'}
      </Button>
      {successMessage && (
        <p className="text-sm text-green-600 dark:text-green-400">{successMessage}</p>
      )}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}

export function LeagueSettingsPage() {
  const { user } = useAuth()
  const [removingUserId, setRemovingUserId] = useState<string | null>(null)
  const [removeError, setRemoveError] = useState<string | null>(null)
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

  async function handleRemoveMember(userId: string, displayName: string) {
    if (!window.confirm(`Remove ${displayName} from the league?`)) return
    setRemoveError(null)
    setRemovingUserId(userId)
    try {
      await removeLeagueMember(userId)
      await queryClient.invalidateQueries({ queryKey: ['league', 'members'] })
      await queryClient.invalidateQueries({ queryKey: ['session', 'bootstrap'] })
    } catch {
      setRemoveError(`Could not remove ${displayName}. Please try again.`)
    } finally {
      setRemovingUserId(null)
    }
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">
          League administration
        </p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
          League settings
        </h1>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-start gap-3">
          <span className="rounded-xl bg-sky/15 p-3 text-sky">
            <ShieldCheck size={22} aria-hidden="true" />
          </span>
          <div>
            <p className="text-lg font-bold">{league.name}</p>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Season {league.season} · Commissioner {league.commissionerName}
            </p>
          </div>
        </div>
      </div>

      {isCommissioner && (
        <div className="space-y-5">
          <div className="space-y-3">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <KeyRound size={18} aria-hidden="true" /> League passcode
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Share this code with people you want to add to the league.
            </p>
            <code className="inline-block rounded-lg bg-slate-100 px-4 py-3 text-lg font-bold tracking-widest text-primary dark:bg-slate-800 dark:text-white">
              {league.inviteCode}
            </code>
          </div>
          <h2 className="flex items-center gap-2 text-lg font-bold">
            <Mail size={18} aria-hidden="true" /> Invite members
          </h2>
          <InviteForm
            onInvited={() =>
              void queryClient.invalidateQueries({ queryKey: ['league', 'members'] })
            }
          />
        </div>
      )}

      <div className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <Users size={18} aria-hidden="true" /> Members
        </h2>
        {removeError && <p className="text-sm text-red-600 dark:text-red-400">{removeError}</p>}
        <ul className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-surface shadow-sm dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
          {members?.map((member) => (
            <li key={member.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p>{member.displayName}</p>
                <p className="text-sm capitalize text-slate-500 dark:text-slate-400">
                  {member.role}
                </p>
              </div>
              {isCommissioner && member.role !== 'owner' && (
                <Button
                  variant="danger"
                  onClick={() => void handleRemoveMember(member.userId, member.displayName)}
                  disabled={removingUserId === member.userId}
                  aria-label={`Remove ${member.displayName}`}
                >
                  <UserMinus size={16} aria-hidden="true" />
                  {removingUserId === member.userId ? 'Removing…' : 'Remove'}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
