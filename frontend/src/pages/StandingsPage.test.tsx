import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { fetchSeasonStandings } from '@/api/leaderboard'
import type { SeasonStandings } from '@/types/leaderboard'
import { StandingsPage } from './StandingsPage'

vi.mock('@/api/leaderboard', () => ({
  fetchSeasonStandings: vi.fn(),
}))

const mockedFetchSeasonStandings = vi.mocked(fetchSeasonStandings)

const standings: SeasonStandings = {
  season: 2026,
  standings: [
    {
      rank: 1,
      memberId: 'user-1',
      memberName: 'Owner',
      totalPoints: 42,
      correctPicks: 10,
      incorrectPicks: 2,
      weeklyWins: 2,
      firstPlaceFinishes: 2,
      secondPlaceFinishes: 1,
      thirdPlaceFinishes: 0,
      payoutCents: 0,
      pointsRemaining: 0,
      lastTwoGamePicks: [],
    },
  ],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <StandingsPage />
    </QueryClientProvider>,
  )
}

describe('StandingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a loading message while standings are pending', () => {
    mockedFetchSeasonStandings.mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('Loading season standings...')).toBeInTheDocument()
  })

  it('shows an empty-state message when there are no completed standings', async () => {
    mockedFetchSeasonStandings.mockResolvedValue({ season: 2026, standings: [] })

    renderPage()

    expect(
      await screen.findByText('No completed season results are available.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('renders the standings table when data is populated', async () => {
    mockedFetchSeasonStandings.mockResolvedValue(standings)

    renderPage()

    expect(await screen.findByText('Owner')).toBeInTheDocument()
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('shows a specific message for a 404 error', async () => {
    mockedFetchSeasonStandings.mockRejectedValue(new ApiError(404, 'NOT_FOUND', 'not found'))

    renderPage()

    expect(await screen.findByText('No completed standings are available.')).toBeInTheDocument()
  })

  it('shows a generic error message for a non-404 failure', async () => {
    mockedFetchSeasonStandings.mockRejectedValue(new Error('boom'))

    renderPage()

    expect(await screen.findByText('Could not load standings.')).toBeInTheDocument()
  })
})
