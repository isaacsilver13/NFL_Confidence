import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createInvite,
  createLeague,
  fetchLeague,
  fetchLeagueMembers,
  fetchMemberPaymentStatuses,
  joinLeague,
  joinLeagueWithCode,
  removeLeagueMember,
  updateLeagueMember,
  updateMemberPayment,
  voidUnpaidPicks,
} from './league'

function responseFor<T>(data: T): Response {
  return new Response(JSON.stringify({ data, message: null }), { status: 200 })
}

describe('league API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('requests the current league', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await fetchLeague()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests league members', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor([]))

    await fetchLeagueMembers()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/members',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates a league with the given name and season', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await createLeague({ name: 'Test League', season: 2026 })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Test League', season: 2026 }),
      }),
    )
  })

  it('creates an invite for an email address', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await createInvite('friend@example.com')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/invite',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'friend@example.com' }),
      }),
    )
  })

  it('joins a league by invite token', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor(null))

    await joinLeague('invite-token')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/join',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ token: 'invite-token' }),
      }),
    )
  })

  it('joins a league by passcode', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor(null))

    await joinLeagueWithCode('league-code')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/join-with-code',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ code: 'league-code' }),
      }),
    )
  })

  it('removes a league member', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor(null))

    await removeLeagueMember('member-1')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/members/member-1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('updates a league member', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await updateLeagueMember('member-1', { displayName: 'Updated', role: 'owner' })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/members/member-1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ displayName: 'Updated', role: 'owner' }),
      }),
    )
  })

  it('requests member payment statuses for a given week', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await fetchMemberPaymentStatuses(3)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/payments?week=3',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('updates a member payment status', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor(null))

    await updateMemberPayment('member-1', 3, true)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/payments/member-1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ week: 3, isPaid: true }),
      }),
    )
  })

  it('voids unpaid picks for a given week', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await voidUnpaidPicks(3)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/league/payments/void-unpaid',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ week: 3 }) }),
    )
  })
})
