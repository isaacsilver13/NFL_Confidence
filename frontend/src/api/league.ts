import type { CreateLeagueInput, Invite, League, LeagueMember } from '@/types/league'
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
