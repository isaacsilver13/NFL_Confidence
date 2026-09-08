import { useState } from 'react'
import { KeyRound, Mail, Pencil, Save, ShieldCheck, UserMinus, Users, X } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import {
  createInvite,
  fetchMemberPaymentStatuses,
  fetchLeague,
  fetchLeagueMembers,
  removeLeagueMember,
  updateLeagueMember,
  updateMemberPayment,
  voidUnpaidPicks,
} from '@/api/league'
import { fetchWeeks } from '@/api/nfl'
import { fetchSessionBootstrap } from '@/api/session'
import { Button } from '@/components/ui/Button'
import type { LeagueMember } from '@/types/league'

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

function PaymentAdmin() {
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const [actionUserId, setActionUserId] = useState<string | null>(null)
  const [isVoiding, setIsVoiding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { data: weeks } = useQuery({
    queryKey: ['weeks'],
    queryFn: fetchWeeks,
    staleTime: 5 * 60_000,
  })
  const weekNumber = selectedWeek ?? weeks?.[0]?.weekNumber ?? 0
  const { data: paymentStatuses, isLoading } = useQuery({
    queryKey: ['league', 'payments', weekNumber],
    queryFn: () => fetchMemberPaymentStatuses(weekNumber),
    enabled: weekNumber > 0,
  })

  async function handlePaymentChange(userId: string, isPaid: boolean) {
    if (weekNumber === 0) return
    setError(null)
    setActionUserId(userId)
    try {
      await updateMemberPayment(userId, weekNumber, isPaid)
      await queryClient.invalidateQueries({ queryKey: ['league', 'payments', weekNumber] })
    } catch {
      setError('Could not update payment status. Please try again.')
    } finally {
      setActionUserId(null)
    }
  }

  async function handleVoidUnpaid() {
    if (weekNumber === 0 || !window.confirm(`Void all unpaid picks for Week ${weekNumber}?`)) return
    setError(null)
    setIsVoiding(true)
    try {
      await voidUnpaidPicks(weekNumber)
      await queryClient.invalidateQueries({ queryKey: ['league', 'payments', weekNumber] })
      await queryClient.invalidateQueries({ queryKey: ['picks'] })
      await queryClient.invalidateQueries({ queryKey: ['leaderboard'] })
    } catch {
      setError('Could not void unpaid picks. Please try again.')
    } finally {
      setIsVoiding(false)
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Weekly payments</h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Mark who has paid before voiding unpaid picks.
          </p>
        </div>
        <label className="text-sm font-medium">
          Week
          <select
            aria-label="Payment week"
            value={weekNumber || ''}
            onChange={(event) => setSelectedWeek(Number(event.target.value))}
            className="ml-2 min-h-10 rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
          >
            {weeks?.map((week) => (
              <option key={week.id} value={week.weekNumber}>
                Week {week.weekNumber}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Loading payment status...</p>
      ) : (
        <>
          <ul className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-surface shadow-sm dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
            {paymentStatuses?.members.map((payment) => (
              <li
                key={payment.userId}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              >
                <div>
                  <p className="font-medium">{payment.displayName}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{payment.email}</p>
                  {payment.voidedPickCount > 0 && (
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      {payment.voidedPickCount} pick(s) already voided
                    </p>
                  )}
                </div>
                <label className="flex min-h-10 items-center gap-2 text-sm font-semibold">
                  <input
                    type="checkbox"
                    checked={payment.isPaid}
                    disabled={actionUserId === payment.userId || isVoiding}
                    onChange={(event) =>
                      void handlePaymentChange(payment.userId, event.target.checked)
                    }
                    className="h-4 w-4 accent-accent"
                  />
                  Paid
                </label>
              </li>
            ))}
          </ul>
          <Button
            type="button"
            variant="danger"
            onClick={() => void handleVoidUnpaid()}
            disabled={isVoiding || weekNumber === 0}
          >
            {isVoiding ? 'Voiding unpaid picks...' : 'Void unpaid picks'}
          </Button>
        </>
      )}
    </section>
  )
}

export function LeagueSettingsPage() {
  const { data: bootstrapData, isLoading: isLoadingMembership } = useQuery({
    queryKey: ['session', 'bootstrap'],
    queryFn: fetchSessionBootstrap,
    retry: false,
    staleTime: 5 * 60_000,
  })
  const isCommissioner =
    bootstrapData?.membership.status === 'member' && bootstrapData.membership.role === 'owner'
  const [removingUserId, setRemovingUserId] = useState<string | null>(null)
  const [removeError, setRemoveError] = useState<string | null>(null)
  const [editingUserId, setEditingUserId] = useState<string | null>(null)
  const [draftDisplayName, setDraftDisplayName] = useState('')
  const [draftRole, setDraftRole] = useState<LeagueMember['role']>('member')
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)
  const [updateError, setUpdateError] = useState<string | null>(null)
  const { data: league, isLoading: isLoadingLeague } = useQuery({
    queryKey: ['league'],
    queryFn: fetchLeague,
    enabled: isCommissioner,
    retry: false,
    staleTime: 5 * 60_000,
  })
  const { data: members } = useQuery({
    queryKey: ['league', 'members'],
    queryFn: fetchLeagueMembers,
    enabled: isCommissioner && !!league,
    staleTime: 2 * 60_000,
  })
  const queryClient = useQueryClient()

  if (isLoadingMembership) {
    return null
  }

  if (!isCommissioner) {
    return <Navigate to="/" replace />
  }

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

  function startEditing(member: LeagueMember) {
    setEditingUserId(member.userId)
    setDraftDisplayName(member.displayName)
    setDraftRole(member.role)
    setUpdateError(null)
  }

  function cancelEditing() {
    setEditingUserId(null)
    setUpdateError(null)
  }

  async function handleUpdateMember(event: React.FormEvent, userId: string) {
    event.preventDefault()
    setUpdateError(null)
    setUpdatingUserId(userId)
    try {
      await updateLeagueMember(userId, {
        displayName: draftDisplayName.trim(),
        role: draftRole,
      })
      await queryClient.invalidateQueries({ queryKey: ['league', 'members'] })
      await queryClient.invalidateQueries({ queryKey: ['session', 'bootstrap'] })
      setEditingUserId(null)
    } catch {
      setUpdateError('Could not update this member. Please try again.')
    } finally {
      setUpdatingUserId(null)
    }
  }

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
          Members
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
        {(removeError || updateError) && (
          <p className="text-sm text-red-600 dark:text-red-400">{removeError || updateError}</p>
        )}
        <ul className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-surface shadow-sm dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
          {members?.map((member) => (
            <li key={member.id} className="px-4 py-3">
              {editingUserId === member.userId ? (
                <form
                  onSubmit={(event) => void handleUpdateMember(event, member.userId)}
                  className="space-y-3"
                >
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor={`member-name-${member.userId}`}
                        className="mb-1 block text-sm font-medium"
                      >
                        Display name
                      </label>
                      <input
                        id={`member-name-${member.userId}`}
                        type="text"
                        required
                        value={draftDisplayName}
                        onChange={(event) => setDraftDisplayName(event.target.value)}
                        className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor={`member-role-${member.userId}`}
                        className="mb-1 block text-sm font-medium"
                      >
                        Role
                      </label>
                      <select
                        id={`member-role-${member.userId}`}
                        value={draftRole}
                        onChange={(event) =>
                          setDraftRole(event.target.value as LeagueMember['role'])
                        }
                        className="min-h-11 w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
                      >
                        <option value="member">Member</option>
                        <option value="owner">Commissioner</option>
                      </select>
                    </div>
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Email: {member.email} (read-only)
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button type="submit" disabled={updatingUserId === member.userId}>
                      <Save size={16} aria-hidden="true" />
                      {updatingUserId === member.userId ? 'Saving...' : 'Save changes'}
                    </Button>
                    <Button type="button" variant="quiet" onClick={cancelEditing}>
                      <X size={16} aria-hidden="true" />
                      Cancel
                    </Button>
                  </div>
                </form>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p>{member.displayName}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{member.email}</p>
                    <p className="text-sm capitalize text-slate-500 dark:text-slate-400">
                      {member.role === 'owner' ? 'Commissioner' : 'Member'}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => startEditing(member)}
                      aria-label={`Edit ${member.displayName}`}
                    >
                      <Pencil size={16} aria-hidden="true" />
                      Edit
                    </Button>
                    {member.role !== 'owner' && (
                      <Button
                        variant="danger"
                        onClick={() => void handleRemoveMember(member.userId, member.displayName)}
                        disabled={removingUserId === member.userId}
                        aria-label={`Remove ${member.displayName}`}
                      >
                        <UserMinus size={16} aria-hidden="true" />
                        {removingUserId === member.userId ? 'Removing...' : 'Remove'}
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      <PaymentAdmin />
    </div>
  )
}
