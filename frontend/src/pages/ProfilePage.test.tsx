import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchPickHistory } from '@/api/nfl'
import type { PickHistory } from '@/types/nfl'
import { ProfilePage } from './ProfilePage'

vi.mock('@/api/nfl', () => ({
  fetchPickHistory: vi.fn(),
}))

const mockedFetchPickHistory = vi.mocked(fetchPickHistory)

const history: PickHistory = {
  season: 2026,
  weeks: [
    {
      weekNumber: 1,
      picks: [
        {
          id: 'pick-1',
          gameId: 'game-1',
          awayTeam: 'BUF',
          homeTeam: 'KC',
          kickoff: '2026-09-10T20:00:00Z',
          status: 'final',
          team: 'KC',
          confidence: 4,
          submittedAt: '2026-09-09T12:00:00Z',
          winningTeam: 'KC',
          isTie: false,
          pointsEarned: 7,
          outcome: 'correct',
        },
      ],
    },
  ],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ProfilePage />
    </QueryClientProvider>,
  )
}

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchPickHistory.mockResolvedValue(history)
  })

  it('renders private completed pick history without a member selector', async () => {
    renderPage()

    expect(await screen.findByText('BUF at KC')).toBeInTheDocument()
    expect(screen.getByText('Correct')).toBeInTheDocument()
    expect(screen.getByText('7', { selector: 'td' })).toBeInTheDocument()
    expect(screen.queryByLabelText(/member/i)).not.toBeInTheDocument()
    expect(mockedFetchPickHistory).toHaveBeenCalledTimes(1)
  })

  it('renders an empty state when no completed picks exist', async () => {
    mockedFetchPickHistory.mockResolvedValueOnce({ season: 2026, weeks: [] })
    renderPage()

    expect(await screen.findByText('No completed picks yet.')).toBeInTheDocument()
  })

  it('defaults to the latest week and switches the reviewed week', async () => {
    const user = userEvent.setup()
    mockedFetchPickHistory.mockResolvedValueOnce({
      season: 2026,
      weeks: [
        ...history.weeks,
        {
          weekNumber: 2,
          picks: [{ ...history.weeks[0].picks[0], id: 'pick-2', awayTeam: 'GB', homeTeam: 'CHI' }],
        },
      ],
    })
    renderPage()

    expect(await screen.findByText('GB at CHI')).toBeInTheDocument()
    expect(screen.queryByText('BUF at KC')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Review week'), '1')
    expect(screen.getByText('BUF at KC')).toBeInTheDocument()
    expect(screen.queryByText('GB at CHI')).not.toBeInTheDocument()
  })

  it('sorts history rows when a column header is activated', async () => {
    const user = userEvent.setup()
    mockedFetchPickHistory.mockResolvedValueOnce({
      season: 2026,
      weeks: [
        {
          weekNumber: 1,
          picks: [
            history.weeks[0].picks[0],
            {
              ...history.weeks[0].picks[0],
              id: 'pick-2',
              awayTeam: 'GB',
              homeTeam: 'CHI',
              confidence: 1,
              pointsEarned: 2,
            },
          ],
        },
      ],
    })
    renderPage()

    await screen.findByText('GB at CHI')
    await user.click(screen.getByRole('button', { name: 'Sort by Confidence' }))
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('GB at CHI')
    expect(rows[2]).toHaveTextContent('BUF at KC')
    expect(screen.getAllByRole('columnheader')[2]).toHaveAttribute('aria-sort', 'ascending')
  })
})
