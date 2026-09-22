import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchPickBreakdown, fetchWeeklyLeaderboard } from '@/api/leaderboard'
import { fetchCompletedWeeks, fetchCurrentWeek } from '@/api/nfl'
import type { NflWeek } from '@/types/nfl'
import { LeaderboardPage } from './LeaderboardPage'

vi.mock('@/api/leaderboard', () => ({
  fetchWeeklyLeaderboard: vi.fn(),
  fetchPickBreakdown: vi.fn(),
}))

vi.mock('@/api/nfl', () => ({
  fetchCompletedWeeks: vi.fn(),
  fetchCurrentWeek: vi.fn(),
}))

const mockedFetchWeeklyLeaderboard = vi.mocked(fetchWeeklyLeaderboard)
const mockedFetchPickBreakdown = vi.mocked(fetchPickBreakdown)
const mockedFetchCompletedWeeks = vi.mocked(fetchCompletedWeeks)
const mockedFetchCurrentWeek = vi.mocked(fetchCurrentWeek)

const currentWeek: NflWeek = {
  id: 'week-3',
  season: 2026,
  weekNumber: 3,
  startDate: '2026-09-20T00:00:00Z',
  endDate: '2026-09-27T00:00:00Z',
  status: 'regular',
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <LeaderboardPage />
    </QueryClientProvider>,
  )
}

describe('LeaderboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchPickBreakdown.mockResolvedValue({ season: 2026, weeks: [] })
  })

  it('defaults to the live current week when no week has completed yet', async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [
        {
          rank: 1,
          memberId: 'user-1',
          memberName: 'Owner',
          totalPoints: 10,
          correctPicks: 1,
          incorrectPicks: 0,
          weeklyWins: 0,
          firstPlaceFinishes: 0,
          secondPlaceFinishes: 0,
          thirdPlaceFinishes: 0,
          payoutCents: 0,
          pointsRemaining: 5,
          lastTwoGamePicks: [],
        },
      ],
      lastTwoGames: [],
    })

    renderPage()

    expect(await screen.findByText('Owner')).toBeInTheDocument()
    expect(mockedFetchWeeklyLeaderboard).toHaveBeenCalledWith(3)
    expect(screen.getByRole('option', { name: 'Week 3 — Live' })).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('lists completed weeks alongside the live current week, sorted ascending', async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([
      { weekNumber: 1, seasonNumber: 2026 },
      { weekNumber: 2, seasonNumber: 2026 },
    ])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [],
      lastTwoGames: [],
    })

    renderPage()

    await screen.findByRole('option', { name: 'Week 3 — Live' })
    const options = screen.getAllByRole('option').map((option) => option.textContent)
    expect(options).toEqual(['Week 1', 'Week 2', 'Week 3 — Live'])
  })

  it('shows a message instead of an endless spinner when no week exists yet', async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockRejectedValue(new Error('not found'))

    renderPage()

    expect(await screen.findByText('No weeks available yet.')).toBeInTheDocument()
    expect(mockedFetchWeeklyLeaderboard).not.toHaveBeenCalled()
  })

  it('shows only Rank, Member, Correct, Points, and Points Left columns in that order', async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [
        {
          rank: 1,
          memberId: 'user-1',
          memberName: 'Owner',
          totalPoints: 10,
          correctPicks: 1,
          incorrectPicks: 0,
          weeklyWins: 0,
          firstPlaceFinishes: 0,
          secondPlaceFinishes: 0,
          thirdPlaceFinishes: 0,
          payoutCents: 0,
          pointsRemaining: 5,
          lastTwoGamePicks: [],
        },
      ],
      lastTwoGames: [],
    })

    renderPage()

    await screen.findByText('Owner')
    const headers = screen.getAllByRole('columnheader').map((header) => header.textContent)
    expect(headers).toEqual(['Rank', 'Member', 'Correct', 'Points', 'Points Left'])
  })

  it("adds a column per last-two-games showing each member's pick", async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [
        {
          rank: 1,
          memberId: 'user-1',
          memberName: 'Owner',
          totalPoints: 10,
          correctPicks: 1,
          incorrectPicks: 0,
          weeklyWins: 0,
          firstPlaceFinishes: 0,
          secondPlaceFinishes: 0,
          thirdPlaceFinishes: 0,
          payoutCents: 0,
          pointsRemaining: 5,
          lastTwoGamePicks: [
            { gameId: 'game-1', team: 'DEN', confidence: 6 },
            { gameId: 'game-2', team: null, confidence: null },
          ],
        },
      ],
      lastTwoGames: [
        { gameId: 'game-1', awayTeam: 'DEN', homeTeam: 'KC' },
        { gameId: 'game-2', awayTeam: 'DAL', homeTeam: 'NYG' },
      ],
    })

    renderPage()

    await screen.findByText('Owner')
    const headers = screen.getAllByRole('columnheader').map((header) => header.textContent)
    expect(headers).toEqual([
      'Rank',
      'Member',
      'Correct',
      'Points',
      'Points Left',
      'Picks (DEN @ KC)',
      'Picks (DAL @ NYG)',
    ])
    expect(screen.getByText('DEN (6)')).toBeInTheDocument()
  })

  it('gives the week select readable text color in dark mode', async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [],
      lastTwoGames: [],
    })

    renderPage()

    const select = await screen.findByRole('combobox', { name: 'Week' })
    expect(select).toHaveClass('dark:text-slate-100')
  })

  it('shows the pick breakdown for the selected week', async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([{ weekNumber: 1, seasonNumber: 2026 }])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [],
      lastTwoGames: [],
    })
    mockedFetchPickBreakdown.mockResolvedValue({
      season: 2026,
      weeks: [
        {
          weekNumber: 3,
          games: [
            {
              gameId: 'game-1',
              awayTeam: 'CHI',
              homeTeam: 'GB',
              medianConfidence: 4,
              teamCounts: [
                { team: 'CHI', userCount: 3 },
                { team: 'GB', userCount: 1 },
              ],
            },
          ],
        },
      ],
    })

    renderPage()

    expect(await screen.findByText('Game Breakdown')).toBeInTheDocument()
    expect(await screen.findByText('CHI: 3 picks')).toBeInTheDocument()
  })

  it("shows a message when the selected week's breakdown isn't available yet", async () => {
    mockedFetchCompletedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [],
      lastTwoGames: [],
    })
    mockedFetchPickBreakdown.mockResolvedValue({ season: 2026, weeks: [] })

    renderPage()

    expect(
      await screen.findByText("Pick breakdown isn't available until Week 3 is complete."),
    ).toBeInTheDocument()
  })

  it('switches the pick breakdown when a different week is selected', async () => {
    const user = userEvent.setup()
    mockedFetchCompletedWeeks.mockResolvedValue([{ weekNumber: 1, seasonNumber: 2026 }])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 1, seasonNumber: 2026 },
      standings: [],
      lastTwoGames: [],
    })
    mockedFetchPickBreakdown.mockResolvedValue({
      season: 2026,
      weeks: [
        {
          weekNumber: 1,
          games: [
            {
              gameId: 'game-1',
              awayTeam: 'CHI',
              homeTeam: 'GB',
              medianConfidence: 4,
              teamCounts: [{ team: 'CHI', userCount: 2 }],
            },
          ],
        },
      ],
    })

    renderPage()

    // Defaults to the live current week (3), which has no completed breakdown yet.
    await screen.findByText("Pick breakdown isn't available until Week 3 is complete.")

    await user.selectOptions(screen.getByRole('combobox', { name: 'Week' }), 'Week 1')

    expect(await screen.findByText('CHI: 2 picks')).toBeInTheDocument()
    expect(
      screen.queryByText("Pick breakdown isn't available until Week 3 is complete."),
    ).not.toBeInTheDocument()
  })
})
