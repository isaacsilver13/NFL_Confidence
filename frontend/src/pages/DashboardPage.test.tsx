import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { joinLeagueWithCode } from '@/api/league'
import { fetchSessionBootstrap, type SessionBootstrap } from '@/api/session'
import { DashboardPage } from './DashboardPage'

vi.mock('@/api/league', () => ({
  createLeague: vi.fn(),
  joinLeagueWithCode: vi.fn(),
}))

vi.mock('@/api/session', () => ({
  fetchSessionBootstrap: vi.fn(),
}))

vi.mock('@/api/leaderboard', () => ({
  fetchSeasonStandings: vi.fn(),
  fetchWeeklyLeaderboard: vi.fn(),
}))

const mockedJoinLeagueWithCode = vi.mocked(joinLeagueWithCode)
const mockedFetchSessionBootstrap = vi.mocked(fetchSessionBootstrap)

const nonMemberSession: SessionBootstrap = {
  user: {
    id: 'user-1',
    displayName: 'New User',
    email: 'new@example.com',
    avatarUrl: null,
  },
  league: null,
  currentWeek: null,
  membership: { status: 'not_member', role: null },
}

const noLeagueSession: SessionBootstrap = {
  ...nonMemberSession,
  membership: { status: 'no_league', role: null },
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DashboardPage league access', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchSessionBootstrap.mockResolvedValue(nonMemberSession)
  })

  it('prompts a signed-in non-member for the shared league passcode', async () => {
    renderPage()

    expect(await screen.findByLabelText('League passcode')).toBeInTheDocument()
    expect(screen.getByText(/not a member yet/i)).toBeInTheDocument()
  })

  it('shows the create-league form when no league exists', async () => {
    mockedFetchSessionBootstrap.mockResolvedValueOnce(noLeagueSession)
    renderPage()

    expect(await screen.findByLabelText('League name')).toBeInTheDocument()
    expect(screen.queryByLabelText('League passcode')).not.toBeInTheDocument()
  })

  it('shows a specific message for an invalid passcode', async () => {
    const user = userEvent.setup()
    mockedJoinLeagueWithCode.mockRejectedValueOnce(
      new ApiError(422, 'VALIDATION_ERROR', 'That league passcode is invalid.'),
    )
    renderPage()

    await user.type(await screen.findByLabelText('League passcode'), 'wrong-code')
    await user.click(screen.getByRole('button', { name: /join league/i }))

    expect(
      await screen.findByText('That league passcode is invalid. Please check it and try again.'),
    ).toBeInTheDocument()
  })

  it('shows a specific message when the user is already a member', async () => {
    const user = userEvent.setup()
    mockedJoinLeagueWithCode.mockRejectedValueOnce(
      new ApiError(409, 'CONFLICT', 'You are already a member of this league.'),
    )
    renderPage()

    await user.type(await screen.findByLabelText('League passcode'), 'league-code')
    await user.click(screen.getByRole('button', { name: /join league/i }))

    expect(await screen.findByText('You are already a member of this league.')).toBeInTheDocument()
  })
})
