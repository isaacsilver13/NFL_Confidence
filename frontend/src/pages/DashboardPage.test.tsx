import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { joinLeagueWithCode } from '@/api/league'
import { fetchCurrentPicksCard, fetchSessionBootstrap, type SessionBootstrap } from '@/api/session'
import { fetchCompletedWeeks } from '@/api/nfl'
import { fetchSeasonStandings, fetchWeeklyLeaderboard } from '@/api/leaderboard'
import { DashboardPage } from './DashboardPage'

vi.mock('./PicksPage', () => ({
  PicksPage: () => <div>Picks section body</div>,
}))

vi.mock('./LeaderboardPage', () => ({
  LeaderboardPage: () => <div>Leaderboard section body</div>,
}))

vi.mock('./StandingsPage', () => ({
  StandingsPage: () => <div>Standings section body</div>,
}))

vi.mock('./ProfilePage', () => ({
  ProfilePage: () => <div>Profile section body</div>,
}))

vi.mock('@/api/league', () => ({
  createLeague: vi.fn(),
  joinLeagueWithCode: vi.fn(),
}))

vi.mock('@/api/session', () => ({
  fetchSessionBootstrap: vi.fn(),
  fetchCurrentPicksCard: vi.fn(),
}))

vi.mock('@/api/nfl', () => ({
  fetchCompletedWeeks: vi.fn(),
  fetchPickHistory: vi.fn(),
}))

vi.mock('@/api/leaderboard', () => ({
  fetchSeasonStandings: vi.fn(),
  fetchWeeklyLeaderboard: vi.fn(),
}))

const mockedJoinLeagueWithCode = vi.mocked(joinLeagueWithCode)
const mockedFetchSessionBootstrap = vi.mocked(fetchSessionBootstrap)
const mockedFetchCurrentPicksCard = vi.mocked(fetchCurrentPicksCard)
const mockedFetchCompletedWeeks = vi.mocked(fetchCompletedWeeks)
const mockedFetchSeasonStandings = vi.mocked(fetchSeasonStandings)
const mockedFetchWeeklyLeaderboard = vi.mocked(fetchWeeklyLeaderboard)

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

const memberSession: SessionBootstrap = {
  ...nonMemberSession,
  league: {
    id: 'league-1',
    name: 'Test League',
    season: 2026,
    memberCount: 2,
    commissionerName: 'Commissioner',
    inviteCode: 'invite-code',
    isActive: true,
  },
  currentWeek: {
    id: 'week-1',
    season: 2026,
    weekNumber: 1,
    startDate: '2026-09-01T00:00:00Z',
    endDate: '2026-09-08T00:00:00Z',
    status: 'regular',
  },
  membership: { status: 'member', role: 'member' },
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
    window.localStorage.clear()
    window.history.replaceState(null, '', '/')
    mockedFetchSessionBootstrap.mockResolvedValue(nonMemberSession)
    mockedFetchCurrentPicksCard.mockResolvedValue({
      week: memberSession.currentWeek!,
      games: [],
      picks: [],
    })
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchSeasonStandings.mockResolvedValue({ season: 2026, standings: [] })
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

  it('opens only Picks by default and fetches leaderboard data after expansion', async () => {
    const user = userEvent.setup()
    mockedFetchSessionBootstrap.mockResolvedValueOnce(memberSession)
    renderPage()

    const picksSection = await screen.findByRole('button', { name: /^Picks/ })
    const leaderboardSection = screen.getByRole('button', { name: /^Leaderboard/ })
    expect(picksSection).toHaveAttribute('aria-expanded', 'true')
    expect(leaderboardSection).toHaveAttribute('aria-expanded', 'false')
    expect(await screen.findByText('Picks section body')).toBeInTheDocument()
    expect(mockedFetchCompletedWeeks).not.toHaveBeenCalled()

    await user.click(leaderboardSection)

    expect(leaderboardSection).toHaveAttribute('aria-expanded', 'true')
    await screen.findByText('Leaderboard section body')
    expect(mockedFetchCompletedWeeks).toHaveBeenCalledTimes(1)
  })

  it('shows the live current week rank in the summary before any week completes', async () => {
    const user = userEvent.setup()
    mockedFetchSessionBootstrap.mockResolvedValueOnce(memberSession)
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 1, seasonNumber: 2026 },
      standings: [
        {
          rank: 2,
          memberId: 'user-1',
          memberName: 'New User',
          totalPoints: 5,
          correctPicks: 1,
          incorrectPicks: 0,
          weeklyWins: 0,
          firstPlaceFinishes: 0,
          secondPlaceFinishes: 0,
          thirdPlaceFinishes: 0,
          payoutCents: 0,
          pointsRemaining: 10,
        },
      ],
    })
    renderPage()

    const leaderboardSection = await screen.findByRole('button', { name: /^Leaderboard/ })
    await user.click(leaderboardSection)

    expect(await screen.findByText('Your current rank is #2')).toBeInTheDocument()
  })

  it('opens a section named by the URL hash and keeps Picks open for multiple panes', async () => {
    mockedFetchSessionBootstrap.mockResolvedValueOnce(memberSession)
    window.history.replaceState(null, '', '/#standings')
    renderPage()

    expect(await screen.findByRole('button', { name: /^Standings/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(screen.getByRole('button', { name: /^Picks/ })).toHaveAttribute('aria-expanded', 'true')
  })
})
