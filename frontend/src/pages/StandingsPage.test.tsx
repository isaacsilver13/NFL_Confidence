import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
      nightGamePicks: [],
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

  it('sorts the standings when a column header is clicked', async () => {
    const user = userEvent.setup()
    mockedFetchSeasonStandings.mockResolvedValue({
      ...standings,
      standings: [
        { ...standings.standings[0], memberId: 'a', memberName: 'Alpha', rank: 1, totalPoints: 10 },
        { ...standings.standings[0], memberId: 'b', memberName: 'Bravo', rank: 2, totalPoints: 30 },
        {
          ...standings.standings[0],
          memberId: 'c',
          memberName: 'Charlie',
          rank: 3,
          totalPoints: 20,
        },
      ],
    })

    renderPage()

    const names = () =>
      within(screen.getByRole('table'))
        .getAllByRole('row')
        .slice(1)
        .map((row) => within(row).getAllByRole('cell')[0].textContent)
    await screen.findByText('Alpha')
    expect(names()).toEqual(['Alpha', 'Bravo', 'Charlie'])

    await user.click(screen.getByRole('button', { name: 'Sort by Points' }))
    expect(names()).toEqual(['Bravo', 'Charlie', 'Alpha'])

    await user.click(screen.getByRole('button', { name: 'Sort by Points' }))
    expect(names()).toEqual(['Alpha', 'Charlie', 'Bravo'])
    expect(screen.getByRole('button', { name: 'Sort by Points' }).closest('th')).toHaveAttribute(
      'aria-sort',
      'ascending',
    )

    await user.click(screen.getByRole('button', { name: 'Sort by Member' }))
    expect(names()).toEqual(['Alpha', 'Bravo', 'Charlie'])
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
