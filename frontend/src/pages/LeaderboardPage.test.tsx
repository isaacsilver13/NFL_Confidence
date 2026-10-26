import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchWeeklyLeaderboard, fetchWeeklyOutcomeScenarios } from '@/api/leaderboard'
import {
  fetchAllPicksForWeek,
  fetchStartedWeeks,
  fetchCurrentWeek,
  fetchLastRefreshed,
} from '@/api/nfl'
import type { NflWeek } from '@/types/nfl'
import { LeaderboardPage } from './LeaderboardPage'

vi.mock('@/api/leaderboard', () => ({
  fetchWeeklyLeaderboard: vi.fn(),
  fetchWeeklyOutcomeScenarios: vi.fn(),
}))

vi.mock('@/api/nfl', () => ({
  fetchLastRefreshed: vi.fn(),
  fetchAllPicksForWeek: vi.fn(),
  fetchStartedWeeks: vi.fn(),
  fetchCurrentWeek: vi.fn(),
}))

const mockedFetchWeeklyLeaderboard = vi.mocked(fetchWeeklyLeaderboard)
const mockedFetchWeeklyOutcomeScenarios = vi.mocked(fetchWeeklyOutcomeScenarios)
const mockedFetchAllPicksForWeek = vi.mocked(fetchAllPicksForWeek)
const mockedFetchStartedWeeks = vi.mocked(fetchStartedWeeks)
const mockedFetchLastRefreshed = vi.mocked(fetchLastRefreshed)
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
    mockedFetchLastRefreshed.mockResolvedValue({ lastRefreshedAt: '2026-09-27T21:12:00Z' })
  })

  it('defaults to the live current week when no week has completed yet', async () => {
    mockedFetchStartedWeeks.mockResolvedValue([])
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
          maxPointsPossible: 0,
          isEliminated: false,
          nightGamePicks: [],
        },
      ],
      nightGames: [],
      picksRevealed: true,
    })

    renderPage()

    expect(await screen.findByText('Owner')).toBeInTheDocument()
    expect(await screen.findByText(/Last refreshed Sun, Sep 27, 4:12 PM CDT/)).toBeInTheDocument()
    expect(mockedFetchWeeklyLeaderboard).toHaveBeenCalledWith(3)
    expect(screen.getByRole('option', { name: 'Week 3 — Live' })).toBeInTheDocument()
  })

  it('lists completed weeks alongside the live current week, sorted ascending', async () => {
    mockedFetchStartedWeeks.mockResolvedValue([
      { weekNumber: 1, seasonNumber: 2026 },
      { weekNumber: 2, seasonNumber: 2026 },
    ])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [],
      nightGames: [],
      picksRevealed: true,
    })

    renderPage()

    await screen.findByRole('option', { name: 'Week 3 — Live' })
    const options = screen.getAllByRole('option').map((option) => option.textContent)
    expect(options).toEqual(['Week 1', 'Week 2', 'Week 3 — Live'])
  })

  it('shows a message instead of an endless spinner when no week exists yet', async () => {
    mockedFetchStartedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockRejectedValue(new Error('not found'))

    renderPage()

    expect(await screen.findByText('No weeks available yet.')).toBeInTheDocument()
    expect(mockedFetchWeeklyLeaderboard).not.toHaveBeenCalled()
  })

  it('shows Rank, Member, Correct, Points, Points Left, and Max Points columns in that order', async () => {
    mockedFetchStartedWeeks.mockResolvedValue([])
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
          maxPointsPossible: 0,
          isEliminated: false,
          nightGamePicks: [],
        },
      ],
      nightGames: [],
      picksRevealed: true,
    })

    renderPage()

    await screen.findByText('Owner')
    const headers = screen.getAllByRole('columnheader').map((header) => header.textContent)
    expect(headers).toEqual(['Rank', 'Member', 'Correct', 'Points', 'Points Left', 'Max Points'])
  })

  it('adds one SNF/MNF column listing the night-game picks per member', async () => {
    mockedFetchStartedWeeks.mockResolvedValue([])
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
          maxPointsPossible: 0,
          isEliminated: false,
          nightGamePicks: [
            { gameId: 'game-1', team: 'KC', confidence: 10 },
            { gameId: 'game-2', team: 'CHI', confidence: 5 },
            { gameId: 'game-3', team: 'LAR', confidence: 2 },
          ],
        },
        {
          rank: 2,
          memberId: 'user-2',
          memberName: 'Challenger',
          totalPoints: 8,
          correctPicks: 1,
          incorrectPicks: 0,
          weeklyWins: 0,
          firstPlaceFinishes: 0,
          secondPlaceFinishes: 0,
          thirdPlaceFinishes: 0,
          payoutCents: 0,
          pointsRemaining: 0,
          maxPointsPossible: 0,
          isEliminated: false,
          nightGamePicks: [],
        },
      ],
      picksRevealed: true,
      nightGames: [
        { gameId: 'game-1', awayTeam: 'DEN', homeTeam: 'KC' },
        { gameId: 'game-2', awayTeam: 'DAL', homeTeam: 'CHI' },
        { gameId: 'game-3', awayTeam: 'DAL', homeTeam: 'LAR' },
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
      'Max Points',
      'SNF/MNF',
    ])
    expect(screen.getByText('KC (10), CHI (5), LAR (2)')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('gives the week select readable text color in dark mode', async () => {
    mockedFetchStartedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [],
      nightGames: [],
      picksRevealed: true,
    })

    renderPage()

    const select = await screen.findByRole('combobox', { name: 'Week' })
    expect(select).toHaveClass('dark:text-slate-100')
  })

  it("opens everyone's picks for the selected week in a popup, hidden without standings", async () => {
    const user = userEvent.setup()
    mockedFetchStartedWeeks.mockResolvedValue([{ weekNumber: 2, seasonNumber: 2026 }])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockImplementation(async (weekNumber = 3) => ({
      week: { weekNumber, seasonNumber: 2026 },
      standings:
        weekNumber === 3
          ? []
          : [
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
                pointsRemaining: 0,
                maxPointsPossible: 0,
                isEliminated: false,
                nightGamePicks: [],
              },
            ],
      nightGames: [],
      picksRevealed: true,
    }))
    mockedFetchAllPicksForWeek.mockResolvedValue({
      week: { ...currentWeek, id: 'week-2', weekNumber: 2 },
      games: [
        {
          id: 'game-1',
          awayTeam: 'BUF',
          homeTeam: 'KC',
          kickoff: '2026-09-13T17:00:00Z',
          status: 'final',
        },
      ],
      members: [
        {
          userId: 'user-1',
          displayName: 'Alex',
          picks: [{ id: 'p1', gameId: 'game-1', team: 'KC', confidence: 3, submittedAt: '' }],
        },
      ],
    } as never)

    renderPage()

    await screen.findByRole('option', { name: 'Week 3 — Live' })
    await screen.findByText('No completed results for this week.')
    expect(screen.queryByRole('button', { name: /see everyone's picks/i })).not.toBeInTheDocument()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Week' }), 'Week 2')
    await user.click(await screen.findByRole('button', { name: /see everyone's picks/i }))

    expect(mockedFetchAllPicksForWeek).toHaveBeenCalledWith(2)
    expect(await screen.findByText('Alex')).toBeInTheDocument()
    expect(screen.getByText('KC (3)')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByText('KC (3)')).not.toBeInTheDocument()
  })

  it("hides the everyone's picks button until the week's first kickoff", async () => {
    mockedFetchStartedWeeks.mockResolvedValue([])
    mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
    mockedFetchWeeklyLeaderboard.mockResolvedValue({
      week: { weekNumber: 3, seasonNumber: 2026 },
      standings: [
        {
          rank: 1,
          memberId: 'user-1',
          memberName: 'Owner',
          totalPoints: 0,
          correctPicks: 0,
          incorrectPicks: 0,
          weeklyWins: 0,
          firstPlaceFinishes: 0,
          secondPlaceFinishes: 0,
          thirdPlaceFinishes: 0,
          payoutCents: 0,
          pointsRemaining: 0,
          maxPointsPossible: 0,
          isEliminated: false,
          nightGamePicks: [],
        },
      ],
      nightGames: [],
      picksRevealed: false,
    })

    renderPage()

    expect(await screen.findByText('Owner')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /see everyone's picks/i })).not.toBeInTheDocument()
  })

  it('opens possible finishes only for the live week when the scenario window is available', async () => {
    const user = userEvent.setup()
    mockedFetchStartedWeeks.mockResolvedValue([{ weekNumber: 2, seasonNumber: 2026 }])
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
          pointsRemaining: 12,
          maxPointsPossible: 0,
          isEliminated: false,
          nightGamePicks: [],
        },
      ],
      nightGames: [],
      picksRevealed: true,
      outcomeScenariosAvailable: true,
    })
    mockedFetchWeeklyOutcomeScenarios.mockResolvedValue({
      sundayGame: { gameId: 'snf', awayTeam: 'BUF', homeTeam: 'KC' },
      mondayGame: { gameId: 'mnf', awayTeam: 'DAL', homeTeam: 'LAR' },
      scenarios: [
        {
          sundayWinner: 'BUF',
          mondayWinner: 'DAL',
          firstPlace: ['Alex'],
          secondPlace: ['Sam'],
          thirdPlace: ['Taylor'],
        },
        {
          sundayWinner: 'BUF',
          mondayWinner: 'LAR',
          firstPlace: ['Sam'],
          secondPlace: ['Alex'],
          thirdPlace: ['Taylor'],
        },
        {
          sundayWinner: 'KC',
          mondayWinner: 'DAL',
          firstPlace: ['Taylor'],
          secondPlace: ['Alex'],
          thirdPlace: ['Sam'],
        },
        {
          sundayWinner: 'KC',
          mondayWinner: 'LAR',
          firstPlace: ['Alex'],
          secondPlace: ['Taylor'],
          thirdPlace: ['Sam'],
        },
      ],
    })

    renderPage()

    await user.click(await screen.findByRole('button', { name: /see possible finishes/i }))
    expect(mockedFetchWeeklyOutcomeScenarios).toHaveBeenCalledWith(3)
    expect(await screen.findByRole('dialog', { name: /possible finishes/i })).toBeInTheDocument()
    expect(screen.getAllByText('BUF wins')).toHaveLength(2)
    expect(screen.getAllByText('KC wins')).toHaveLength(2)
    expect(screen.getAllByText('DAL wins')).toHaveLength(2)
    expect(screen.getAllByText('LAR wins')).toHaveLength(2)
    expect(screen.getAllByText('Alex')).toHaveLength(4)

    await user.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByRole('dialog', { name: /possible finishes/i })).not.toBeInTheDocument()
  })

  describe('max points, elimination, and member picks', () => {
    function row(
      memberId: string,
      memberName: string,
      rank: number,
      totalPoints: number,
      pointsRemaining: number,
      isEliminated = false,
    ) {
      return {
        rank,
        memberId,
        memberName,
        totalPoints,
        correctPicks: 1,
        incorrectPicks: 0,
        weeklyWins: 0,
        firstPlaceFinishes: 0,
        secondPlaceFinishes: 0,
        thirdPlaceFinishes: 0,
        payoutCents: 0,
        pointsRemaining,
        maxPointsPossible: totalPoints + pointsRemaining,
        isEliminated,
        nightGamePicks: [],
      }
    }

    function mockLeaderboard(standings: ReturnType<typeof row>[], picksRevealed = true) {
      mockedFetchStartedWeeks.mockResolvedValue([])
      mockedFetchCurrentWeek.mockResolvedValue(currentWeek)
      mockedFetchWeeklyLeaderboard.mockResolvedValue({
        week: { weekNumber: 3, seasonNumber: 2026 },
        standings,
        nightGames: [],
        picksRevealed,
      })
    }

    it('shows each member max points and tags eliminated members while points are in play', async () => {
      mockLeaderboard([row('u1', 'Alex', 1, 30, 5), row('u2', 'Sam', 2, 10, 5, true)])

      renderPage()

      await screen.findByText('Alex')
      const samRow = screen.getByText('Sam').closest('tr') as HTMLElement
      expect(within(samRow).getByText('15')).toBeInTheDocument()
      expect(within(samRow).getByText('Eliminated')).toBeInTheDocument()
      const alexRow = screen.getByText('Alex').closest('tr') as HTMLElement
      expect(within(alexRow).getByText('35')).toBeInTheDocument()
      expect(within(alexRow).queryByText('Eliminated')).not.toBeInTheDocument()
    })

    it('drops the eliminated tag once nothing is left to play', async () => {
      mockLeaderboard([row('u1', 'Alex', 1, 30, 0), row('u2', 'Sam', 2, 10, 0, true)])

      renderPage()

      await screen.findByText('Alex')
      expect(screen.queryByText('Eliminated')).not.toBeInTheDocument()
    })

    it("opens just the clicked member's picks, colored by result", async () => {
      const user = userEvent.setup()
      mockLeaderboard([row('u1', 'Alex', 1, 30, 5), row('u2', 'Sam', 2, 10, 5)])
      const game = (
        id: string,
        away: string,
        home: string,
        status: string,
        winningTeam: string | null,
        isTie = false,
      ) => ({
        id,
        awayTeam: away,
        homeTeam: home,
        kickoff: '2026-09-20T17:00:00Z',
        status,
        winningTeam,
        isTie,
      })
      const pick = (gameId: string, team: string, confidence: number) => ({
        id: `${gameId}-${team}`,
        gameId,
        team,
        confidence,
        submittedAt: '',
      })
      mockedFetchAllPicksForWeek.mockResolvedValue({
        week: currentWeek,
        games: [
          game('g1', 'BUF', 'KC', 'final', 'KC'),
          game('g2', 'GB', 'CHI', 'final', 'GB'),
          game('g3', 'DAL', 'NYG', 'final', null, true),
          game('g4', 'MIA', 'NE', 'live', null),
        ],
        members: [
          {
            userId: 'u1',
            displayName: 'Alex',
            picks: [
              pick('g1', 'KC', 4),
              pick('g2', 'CHI', 3),
              pick('g3', 'DAL', 2),
              pick('g4', 'MIA', 1),
            ],
          },
          { userId: 'u2', displayName: 'Sam', picks: [pick('g1', 'BUF', 4)] },
        ],
      } as never)

      renderPage()

      await user.click(await screen.findByRole('button', { name: 'Alex' }))

      const dialog = await screen.findByRole('dialog', { name: /Alex's picks — Week 3/ })
      expect(within(dialog).queryByText('Sam')).not.toBeInTheDocument()
      const correct = within(dialog).getByText('KC (4)').closest('td') as HTMLElement
      const wrong = within(dialog).getByText('CHI (3)').closest('td') as HTMLElement
      expect(correct).toHaveClass('text-success')
      expect(within(correct).getByText(/Correct/)).toBeInTheDocument()
      expect(wrong).toHaveClass('text-danger')
      expect(within(wrong).getByText(/Wrong/)).toBeInTheDocument()
      // A tied game and a live game stay neutral.
      for (const label of ['DAL (2)', 'MIA (1)']) {
        const cell = within(dialog).getByText(label).closest('td') as HTMLElement
        expect(cell).not.toHaveClass('text-success')
        expect(cell).not.toHaveClass('text-danger')
      }
      expect(mockedFetchAllPicksForWeek).toHaveBeenCalledWith(3)
    })

    it('leaves member names as plain text until picks are revealed', async () => {
      mockLeaderboard([row('u1', 'Alex', 1, 0, 0)], false)

      renderPage()

      await screen.findByText('Alex')
      expect(screen.queryByRole('button', { name: 'Alex' })).not.toBeInTheDocument()
    })
  })
})
