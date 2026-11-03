import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { fetchGamePicks } from '@/api/leaderboard'
import type { GamePicks } from '@/types/leaderboard'
import { WeeklyPickBreakdown } from './WeeklyPickBreakdown'

vi.mock('@/api/leaderboard', () => ({
  fetchGamePicks: vi.fn(),
}))

const mockedFetchGamePicks = vi.mocked(fetchGamePicks)

function renderWithClient(children: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>)
}

describe('WeeklyPickBreakdown', () => {
  it('renders per-game counts, percentages, median, and team colors', () => {
    renderWithClient(
      <WeeklyPickBreakdown
        games={[
          {
            gameId: 'game-1',
            awayTeam: 'CHI',
            homeTeam: 'GB',
            awayRecord: '2-1',
            homeRecord: '1-2',
            medianConfidence: 4.5,
            teamCounts: [
              { team: 'CHI', userCount: 6 },
              { team: 'GB', userCount: 2 },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText('Median confidence:')).toBeInTheDocument()
    expect(screen.getByText('4.5')).toBeInTheDocument()
    expect(screen.getByText('(2-1)')).toBeInTheDocument()
    expect(screen.getByText('(1-2)')).toBeInTheDocument()
    expect(screen.getByText('CHI: 6 picks')).toBeInTheDocument()
    expect(screen.getByText('GB: 2 picks')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'CHI 75 percent, GB 25 percent' })).toBeInTheDocument()
  })

  it('shows an empty state for a game without picks', () => {
    renderWithClient(
      <WeeklyPickBreakdown
        games={[
          {
            gameId: 'game-1',
            awayTeam: 'BUF',
            homeTeam: 'KC',
            awayRecord: null,
            homeRecord: null,
            medianConfidence: null,
            teamCounts: [
              { team: 'BUF', userCount: 0 },
              { team: 'KC', userCount: 0 },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText('No confidence data')).toBeInTheDocument()
    expect(screen.getByText('No picks were submitted for this game.')).toBeInTheDocument()
  })

  it('shows a message when no games are available', () => {
    renderWithClient(<WeeklyPickBreakdown games={[]} />)

    expect(screen.getByText('No games are available for this week.')).toBeInTheDocument()
  })

  it("opens a modal showing everyone's pick for a game, and closes it", async () => {
    const user = userEvent.setup()
    mockedFetchGamePicks.mockResolvedValue({
      gameId: 'game-1',
      awayTeam: 'CHI',
      homeTeam: 'GB',
      picks: [
        { memberName: 'Alex', team: 'CHI', confidence: 5, isCorrect: true },
        { memberName: 'Sam', team: 'GB', confidence: 3, isCorrect: false },
      ],
    })
    renderWithClient(
      <WeeklyPickBreakdown
        games={[
          {
            gameId: 'game-1',
            awayTeam: 'CHI',
            homeTeam: 'GB',
            awayRecord: null,
            homeRecord: null,
            medianConfidence: 4,
            teamCounts: [
              { team: 'CHI', userCount: 1 },
              { team: 'GB', userCount: 1 },
            ],
          },
        ]}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'View Picks' }))

    expect(mockedFetchGamePicks).toHaveBeenCalledWith('game-1')
    expect(await screen.findByText('Alex')).toBeInTheDocument()
    expect(screen.getByText('Sam')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByText('Alex')).not.toBeInTheDocument()
  })

  describe('game picks T-chart', () => {
    const game = {
      gameId: 'game-1',
      awayTeam: 'CHI',
      homeTeam: 'GB',
      awayRecord: null,
      homeRecord: null,
      medianConfidence: 4,
      teamCounts: [
        { team: 'CHI', userCount: 2 },
        { team: 'GB', userCount: 2 },
      ],
    }

    async function openGame(picks: GamePicks['picks']) {
      mockedFetchGamePicks.mockResolvedValue({
        gameId: 'game-1',
        awayTeam: 'CHI',
        homeTeam: 'GB',
        picks,
      })
      const user = userEvent.setup()
      renderWithClient(<WeeklyPickBreakdown games={[game]} />)
      await user.click(screen.getByRole('button', { name: 'View Picks' }))
      await screen.findByRole('list', { name: 'CHI picks' })
    }

    function rowsOf(name: string) {
      return within(screen.getByRole('list', { name }))
        .getAllByRole('listitem')
        .map((item) => item.textContent?.replace(/\s+/g, ' ').trim())
    }

    it('splits picks into a column per team, highest points first', async () => {
      await openGame([
        { memberName: 'Alex', team: 'CHI', confidence: 5, isCorrect: null },
        { memberName: 'Sam', team: 'GB', confidence: 3, isCorrect: null },
        { memberName: 'Jo', team: 'CHI', confidence: 9, isCorrect: null },
        { memberName: 'Kim', team: 'GB', confidence: 7, isCorrect: null },
      ])

      expect(rowsOf('CHI picks')).toEqual(['Jo 9', 'Alex 5'])
      expect(rowsOf('GB picks')).toEqual(['Kim 7', 'Sam 3'])
    })

    it('breaks equal points by member name', async () => {
      await openGame([
        { memberName: 'Zed', team: 'CHI', confidence: 4, isCorrect: null },
        { memberName: 'Amy', team: 'CHI', confidence: 4, isCorrect: null },
      ])

      expect(rowsOf('CHI picks')).toEqual(['Amy 4', 'Zed 4'])
    })

    it('shows "No picks" for a team nobody picked', async () => {
      await openGame([{ memberName: 'Alex', team: 'CHI', confidence: 5, isCorrect: null }])

      expect(rowsOf('GB picks')).toEqual(['No picks'])
    })

    it('marks correct and wrong picks for screen readers, and leaves unscored picks plain', async () => {
      await openGame([
        { memberName: 'Alex', team: 'CHI', confidence: 5, isCorrect: true },
        { memberName: 'Sam', team: 'GB', confidence: 3, isCorrect: false },
        { memberName: 'Jo', team: 'CHI', confidence: 2, isCorrect: null },
      ])

      expect(rowsOf('CHI picks')).toEqual(['Alex 5 ✓ Correct', 'Jo 2'])
      expect(rowsOf('GB picks')).toEqual(['Sam 3 ✗ Wrong'])
    })
  })
})
