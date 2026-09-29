import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchPickBreakdown } from '@/api/leaderboard'
import { fetchCompletedWeeks } from '@/api/nfl'
import { WeeklyGameBreakdownSection } from './WeeklyGameBreakdownSection'

vi.mock('@/api/leaderboard', () => ({ fetchPickBreakdown: vi.fn(), fetchGamePicks: vi.fn() }))
vi.mock('@/api/nfl', () => ({ fetchCompletedWeeks: vi.fn() }))

const mockedFetchPickBreakdown = vi.mocked(fetchPickBreakdown)
const mockedFetchCompletedWeeks = vi.mocked(fetchCompletedWeeks)

function game(gameId: string, awayCount: number) {
  return {
    gameId,
    awayTeam: 'CHI',
    homeTeam: 'GB',
    awayRecord: null,
    homeRecord: null,
    medianConfidence: 4,
    teamCounts: [{ team: 'CHI', userCount: awayCount }],
  }
}

function renderSection() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <WeeklyGameBreakdownSection />
    </QueryClientProvider>,
  )
}

describe('WeeklyGameBreakdownSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('defaults to the latest completed week and switches weeks', async () => {
    const user = userEvent.setup()
    mockedFetchCompletedWeeks.mockResolvedValue([
      { weekNumber: 1, seasonNumber: 2026 },
      { weekNumber: 2, seasonNumber: 2026 },
    ])
    mockedFetchPickBreakdown.mockResolvedValue({
      season: 2026,
      weeks: [
        { weekNumber: 1, games: [game('g1', 2)] },
        { weekNumber: 2, games: [game('g2', 3)] },
      ],
    })

    renderSection()

    expect(await screen.findByText('CHI: 3 picks')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Week' }), 'Week 1')
    expect(await screen.findByText('CHI: 2 picks')).toBeInTheDocument()
  })

  it('explains that the breakdown needs a completed week', async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchPickBreakdown.mockResolvedValue({ season: 2026, weeks: [] })

    renderSection()

    expect(
      await screen.findByText('The breakdown appears once a week is complete.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })
})
