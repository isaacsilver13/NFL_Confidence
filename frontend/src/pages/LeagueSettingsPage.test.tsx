import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fetchLeague,
  fetchLeagueMembers,
  fetchMemberPaymentStatuses,
  fetchMemberSubmissionStatuses,
  removeLeagueMember,
  updateLeagueMember,
  updateMemberPayment,
  voidUnpaidPicks,
} from '@/api/league'
import { fetchCurrentWeek, fetchWeeks } from '@/api/nfl'
import { fetchSessionBootstrap } from '@/api/session'
import type { SessionBootstrap } from '@/api/session'
import type { League, LeagueMember } from '@/types/league'
import type { MemberPaymentStatuses, MemberSubmissionStatuses } from '@/types/league'
import { LeagueSettingsPage } from './LeagueSettingsPage'

vi.mock('@/api/league', () => ({
  createInvite: vi.fn(),
  fetchLeague: vi.fn(),
  fetchLeagueMembers: vi.fn(),
  fetchMemberPaymentStatuses: vi.fn(),
  fetchMemberSubmissionStatuses: vi.fn(),
  removeLeagueMember: vi.fn(),
  updateLeagueMember: vi.fn(),
  updateMemberPayment: vi.fn(),
  voidUnpaidPicks: vi.fn(),
}))

vi.mock('@/api/nfl', () => ({
  fetchCurrentWeek: vi.fn(),
  fetchWeeks: vi.fn(),
}))

vi.mock('@/api/session', () => ({
  fetchSessionBootstrap: vi.fn(),
}))

const mockedFetchLeague = vi.mocked(fetchLeague)
const mockedFetchLeagueMembers = vi.mocked(fetchLeagueMembers)
const mockedFetchMemberPaymentStatuses = vi.mocked(fetchMemberPaymentStatuses)
const mockedFetchMemberSubmissionStatuses = vi.mocked(fetchMemberSubmissionStatuses)
const mockedRemoveLeagueMember = vi.mocked(removeLeagueMember)
const mockedUpdateLeagueMember = vi.mocked(updateLeagueMember)
const mockedUpdateMemberPayment = vi.mocked(updateMemberPayment)
const mockedVoidUnpaidPicks = vi.mocked(voidUnpaidPicks)
const mockedFetchWeeks = vi.mocked(fetchWeeks)
const mockedFetchCurrentWeek = vi.mocked(fetchCurrentWeek)
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

const submissionStatuses: MemberSubmissionStatuses = {
  week: 1,
  members: members.map((member) => ({
    userId: member.userId,
    displayName: member.displayName,
    email: member.email,
    role: member.role,
    submittedAt: member.role === 'owner' ? '2026-09-05T12:00:00Z' : null,
    pickCount: member.role === 'owner' ? 5 : 0,
    isComplete: false,
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
  it('groups tools in accordions that are all closed by default', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: /^Member roster/ })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    const invites = screen.getByRole('button', { name: /^Invitations & passcode/ })
    expect(invites).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('League passcode')).not.toBeInTheDocument()
    await userEvent.setup().click(invites)
    expect(screen.getByText('League passcode')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Weekly status/ })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.queryByRole('button', { name: /^Pick submissions/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Weekly payments/ })).not.toBeInTheDocument()
  })
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
    mockedFetchCurrentWeek.mockResolvedValue({
      id: 'week-1',
      season: 2026,
      weekNumber: 1,
      startDate: '2026-09-01T00:00:00Z',
      endDate: '2026-09-08T00:00:00Z',
      status: 'regular',
    })
    mockedFetchMemberPaymentStatuses.mockResolvedValue(paymentStatuses)
    mockedFetchMemberSubmissionStatuses.mockResolvedValue(submissionStatuses)
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

    await user.click(await screen.findByRole('button', { name: /^Member roster/ }))
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
    renderPage()

    await user.click(await screen.findByRole('button', { name: /^Member roster/ }))
    expect((await screen.findAllByText('member@example.com')).length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: 'Remove Member' }))
    await user.click(screen.getByRole('button', { name: 'Remove' }))

    await waitFor(() => expect(mockedRemoveLeagueMember).toHaveBeenCalledWith('member-1'))
    expect(screen.queryByText('Could not remove Member. Please try again.')).not.toBeInTheDocument()
  })

  it('shows an error when member removal fails', async () => {
    const user = userEvent.setup()
    mockedRemoveLeagueMember.mockRejectedValueOnce(new Error('request failed'))
    renderPage()

    await user.click(await screen.findByRole('button', { name: /^Member roster/ }))
    expect((await screen.findAllByText('member@example.com')).length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: 'Remove Member' }))
    await user.click(screen.getByRole('button', { name: 'Remove' }))

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
    renderPage()

    await user.click(await screen.findByRole('button', { name: /^Weekly status/ }))
    const paymentCheckboxes = await screen.findAllByRole('checkbox', { name: 'Paid' })
    await user.click(paymentCheckboxes[1])

    await waitFor(() => expect(mockedUpdateMemberPayment).toHaveBeenCalledWith('member-1', 1, true))
    await user.click(screen.getByRole('button', { name: 'Void unpaid picks' }))
    await user.click(screen.getByRole('button', { name: 'Void picks' }))

    await waitFor(() => expect(mockedVoidUnpaidPicks).toHaveBeenCalledWith(1))
  })

  it('shows paid and submitted state for every member in one table', async () => {
    renderPage()

    await userEvent.setup().click(await screen.findByRole('button', { name: /^Weekly status/ }))
    const table = await screen.findByRole('table', { name: /weekly status/i })
    expect(screen.getAllByRole('table')).toHaveLength(1)
    const ownerRow = within(table).getByRole('row', { name: /Commissioner/ })
    expect(within(ownerRow).getByText(/Submitted Sep 5/)).toBeInTheDocument()
    expect(within(ownerRow).getByRole('checkbox', { name: 'Paid' })).toBeChecked()
    const memberRow = within(table).getByRole('row', { name: /member@example.com/ })
    expect(within(memberRow).getByText('Not submitted')).toBeInTheDocument()
    expect(within(memberRow).getByRole('checkbox', { name: 'Paid' })).not.toBeChecked()
  })

  it('marks a complete autosaved card that was never formally submitted', async () => {
    mockedFetchMemberSubmissionStatuses.mockResolvedValue({
      ...submissionStatuses,
      members: submissionStatuses.members.map((member) =>
        member.submittedAt ? member : { ...member, pickCount: 16, isComplete: true },
      ),
    })
    renderPage()

    await userEvent.setup().click(await screen.findByRole('button', { name: /^Weekly status/ }))
    const table = await screen.findByRole('table', { name: /weekly status/i })
    expect(within(table).getAllByText('Complete (autosaved)').length).toBeGreaterThan(0)
    expect(within(table).queryByText('Not submitted')).not.toBeInTheDocument()
  })

  it('puts Weekly status first among the Members sections', async () => {
    renderPage()

    const roster = await screen.findByRole('button', { name: /^Member roster/ })
    const invites = screen.getByRole('button', { name: /^Invitations & passcode/ })
    const status = screen.getByRole('button', { name: /^Weekly status/ })
    expect(status.compareDocumentPosition(invites) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(status.compareDocumentPosition(roster) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('filters the weekly status table by paid and by pick status', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(await screen.findByRole('button', { name: /^Weekly status/ }))
    const table = await screen.findByRole('table', { name: /weekly status/i })
    const names = () =>
      within(table)
        .getAllByRole('row')
        .slice(1)
        .map((row) => within(row).getAllByRole('rowheader')[0].textContent)

    expect(names()).toHaveLength(2)
    await user.selectOptions(screen.getByLabelText('Filter by paid'), 'unpaid')
    expect(names()).toEqual([expect.stringContaining('Member')])
    expect(names()[0]).not.toContain('Commissioner')

    await user.selectOptions(screen.getByLabelText('Filter by paid'), 'all')
    await user.selectOptions(screen.getByLabelText('Filter by picks'), 'submitted')
    expect(names()).toEqual([expect.stringContaining('Commissioner')])
  })

  it('sorts the weekly status table by paid when its header is clicked', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(await screen.findByRole('button', { name: /^Weekly status/ }))
    const table = await screen.findByRole('table', { name: /weekly status/i })
    const first = () => within(table).getAllByRole('row')[1].textContent

    await user.click(screen.getByRole('button', { name: 'Sort by Paid' }))
    expect(first()).toContain('Commissioner')
    await user.click(screen.getByRole('button', { name: 'Sort by Paid' }))
    expect(first()).toContain('member@example.com')
  })

  it('defaults the weekly status table to the current week, not Week 1', async () => {
    const week = (weekNumber: number) => ({
      id: `week-${weekNumber}`,
      season: 2026,
      weekNumber,
      startDate: '2026-09-01T00:00:00Z',
      endDate: '2026-09-08T00:00:00Z',
      status: 'regular',
    })
    mockedFetchWeeks.mockResolvedValue([week(1), week(2), week(3)])
    mockedFetchCurrentWeek.mockResolvedValue(week(3))
    renderPage()

    await userEvent.setup().click(await screen.findByRole('button', { name: /^Weekly status/ }))
    await waitFor(() => expect(mockedFetchMemberPaymentStatuses).toHaveBeenCalledWith(3))
    await waitFor(() => expect(mockedFetchMemberSubmissionStatuses).toHaveBeenCalledWith(3))
    expect(screen.getByLabelText('Status week')).toHaveValue('3')
    expect(mockedFetchMemberPaymentStatuses).not.toHaveBeenCalledWith(1)
    expect(mockedFetchMemberSubmissionStatuses).not.toHaveBeenCalledWith(1)
  })
})
