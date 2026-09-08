import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fetchLeague,
  fetchLeagueMembers,
  fetchMemberPaymentStatuses,
  removeLeagueMember,
  updateLeagueMember,
  updateMemberPayment,
  voidUnpaidPicks,
} from '@/api/league'
import { fetchWeeks } from '@/api/nfl'
import { fetchSessionBootstrap } from '@/api/session'
import type { SessionBootstrap } from '@/api/session'
import type { League, LeagueMember } from '@/types/league'
import type { MemberPaymentStatuses } from '@/types/league'
import { LeagueSettingsPage } from './LeagueSettingsPage'

vi.mock('@/api/league', () => ({
  createInvite: vi.fn(),
  fetchLeague: vi.fn(),
  fetchLeagueMembers: vi.fn(),
  fetchMemberPaymentStatuses: vi.fn(),
  removeLeagueMember: vi.fn(),
  updateLeagueMember: vi.fn(),
  updateMemberPayment: vi.fn(),
  voidUnpaidPicks: vi.fn(),
}))

vi.mock('@/api/nfl', () => ({
  fetchWeeks: vi.fn(),
}))

vi.mock('@/api/session', () => ({
  fetchSessionBootstrap: vi.fn(),
}))

const mockedFetchLeague = vi.mocked(fetchLeague)
const mockedFetchLeagueMembers = vi.mocked(fetchLeagueMembers)
const mockedFetchMemberPaymentStatuses = vi.mocked(fetchMemberPaymentStatuses)
const mockedRemoveLeagueMember = vi.mocked(removeLeagueMember)
const mockedUpdateLeagueMember = vi.mocked(updateLeagueMember)
const mockedUpdateMemberPayment = vi.mocked(updateMemberPayment)
const mockedVoidUnpaidPicks = vi.mocked(voidUnpaidPicks)
const mockedFetchWeeks = vi.mocked(fetchWeeks)
const mockedFetchSessionBootstrap = vi.mocked(fetchSessionBootstrap)

const league: League = {
  id: 'league-1',
  name: 'Test League',
  season: 2026,
  memberCount: 2,
  commissionerName: 'Commissioner',
  inviteCode: 'league-code',
  isActive: true,
}

const members: LeagueMember[] = [
  {
    id: 'membership-1',
    userId: 'owner-1',
    displayName: 'Commissioner',
    email: 'owner@example.com',
    avatarUrl: null,
    role: 'owner',
    joinedAt: '2026-09-01T00:00:00Z',
  },
  {
    id: 'membership-2',
    userId: 'member-1',
    displayName: 'Member',
    email: 'member@example.com',
    avatarUrl: null,
    role: 'member',
    joinedAt: '2026-09-02T00:00:00Z',
  },
]

const ownerSession: SessionBootstrap = {
  user: {
    id: 'owner-1',
    displayName: 'Commissioner',
    email: 'owner@example.com',
    avatarUrl: null,
  },
  league,
  currentWeek: null,
  membership: { status: 'member', role: 'owner' },
}

const paymentStatuses: MemberPaymentStatuses = {
  week: 1,
  members: members.map((member) => ({
    userId: member.userId,
    displayName: member.displayName,
    email: member.email,
    role: member.role,
    isPaid: member.role === 'owner',
    markedAt: null,
    voidedPickCount: 0,
  })),
}

function renderPage(session: SessionBootstrap = ownerSession) {
  mockedFetchSessionBootstrap.mockResolvedValue(session)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/members']}>
        <Routes>
          <Route path="/members" element={<LeagueSettingsPage />} />
          <Route path="/" element={<p>Dashboard</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LeagueSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchLeague.mockResolvedValue(league)
    mockedFetchLeagueMembers.mockResolvedValue(members)
    mockedFetchWeeks.mockResolvedValue([
      {
        id: 'week-1',
        season: 2026,
        weekNumber: 1,
        startDate: '2026-09-01T00:00:00Z',
        endDate: '2026-09-08T00:00:00Z',
        status: 'regular',
      },
    ])
    mockedFetchMemberPaymentStatuses.mockResolvedValue(paymentStatuses)
    mockedRemoveLeagueMember.mockResolvedValue(undefined)
    mockedUpdateLeagueMember.mockResolvedValue(members[1])
    mockedUpdateMemberPayment.mockResolvedValue(undefined)
    mockedVoidUnpaidPicks.mockResolvedValue({
      week: 1,
      voidedPickCount: 1,
      affectedMemberCount: 1,
    })
  })

  it('lets an owner edit a member while keeping email read-only', async () => {
    const user = userEvent.setup()
    renderPage()

    expect((await screen.findAllByText('member@example.com')).length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: 'Edit Member' }))
    expect(screen.getByLabelText('Display name')).toHaveValue('Member')
    expect(screen.getByText(/email: member@example.com \(read-only\)/i)).toBeInTheDocument()

    await user.clear(screen.getByLabelText('Display name'))
    await user.type(screen.getByLabelText('Display name'), 'Updated Member')
    await user.selectOptions(screen.getByLabelText('Role'), 'owner')
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() =>
      expect(mockedUpdateLeagueMember).toHaveBeenCalledWith('member-1', {
        displayName: 'Updated Member',
        role: 'owner',
      }),
    )
  })

  it('removes a member without showing an error after a successful response', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()

    expect((await screen.findAllByText('member@example.com')).length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: 'Remove Member' }))

    await waitFor(() => expect(mockedRemoveLeagueMember).toHaveBeenCalledWith('member-1'))
    expect(screen.queryByText('Could not remove Member. Please try again.')).not.toBeInTheDocument()
  })

  it('shows an error when member removal fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockedRemoveLeagueMember.mockRejectedValueOnce(new Error('request failed'))
    renderPage()

    expect((await screen.findAllByText('member@example.com')).length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: 'Remove Member' }))

    expect(
      await screen.findByText('Could not remove Member. Please try again.'),
    ).toBeInTheDocument()
  })

  it('redirects a regular member away from commissioner tools', async () => {
    renderPage({ ...ownerSession, membership: { status: 'member', role: 'member' } })

    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
    expect(mockedFetchLeague).not.toHaveBeenCalled()
  })

  it('lets a commissioner mark payment and void unpaid picks', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()

    expect(await screen.findByText('Weekly payments')).toBeInTheDocument()
    const paymentCheckboxes = await screen.findAllByRole('checkbox', { name: 'Paid' })
    await user.click(paymentCheckboxes[1])

    await waitFor(() => expect(mockedUpdateMemberPayment).toHaveBeenCalledWith('member-1', 1, true))
    await user.click(screen.getByRole('button', { name: 'Void unpaid picks' }))

    await waitFor(() => expect(mockedVoidUnpaidPicks).toHaveBeenCalledWith(1))
  })
})
