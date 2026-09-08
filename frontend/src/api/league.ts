import type {
  CreateLeagueInput,
  Invite,
  League,
  LeagueMember,
  LeagueMemberUpdateInput,
  MemberPaymentStatuses,
  VoidUnpaidPicksResult,
} from '@/types/league'
import { apiFetch } from './client'

export async function fetchLeague(): Promise<League> {
  return apiFetch<League>('/league')
}

export async function fetchLeagueMembers(): Promise<LeagueMember[]> {
  return apiFetch<LeagueMember[]>('/league/members')
}

export async function createLeague(input: CreateLeagueInput): Promise<League> {
  return apiFetch<League>('/league', { method: 'POST', body: JSON.stringify(input) })
}

export async function createInvite(email: string): Promise<Invite> {
  return apiFetch<Invite>('/league/invite', { method: 'POST', body: JSON.stringify({ email }) })
}

export async function joinLeague(token: string): Promise<void> {
  await apiFetch<null>('/league/join', { method: 'POST', body: JSON.stringify({ token }) })
}

export async function joinLeagueWithCode(code: string): Promise<void> {
  await apiFetch<null>('/league/join-with-code', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export async function removeLeagueMember(userId: string): Promise<void> {
  await apiFetch<null>(`/league/members/${userId}`, { method: 'DELETE' })
}

export async function updateLeagueMember(
  userId: string,
  input: LeagueMemberUpdateInput,
): Promise<LeagueMember> {
  return apiFetch<LeagueMember>(`/league/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export async function fetchMemberPaymentStatuses(week: number): Promise<MemberPaymentStatuses> {
  return apiFetch<MemberPaymentStatuses>(`/league/payments?week=${week}`)
}

export async function updateMemberPayment(
  userId: string,
  week: number,
  isPaid: boolean,
): Promise<void> {
  await apiFetch<null>(`/league/payments/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ week, isPaid }),
  })
}

export async function voidUnpaidPicks(week: number): Promise<VoidUnpaidPicksResult> {
  return apiFetch<VoidUnpaidPicksResult>('/league/payments/void-unpaid', {
    method: 'POST',
    body: JSON.stringify({ week }),
  })
}
