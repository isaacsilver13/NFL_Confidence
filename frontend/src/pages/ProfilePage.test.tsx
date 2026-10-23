import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchCompletedWeeks, fetchPickHistory } from '@/api/nfl'
import type { PickHistory } from '@/types/nfl'
import { ProfilePage } from './ProfilePage'

vi.mock('@/api/nfl', () => ({
  fetchPickHistory: vi.fn(),
  fetchCompletedWeeks: vi.fn(),
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
    vi.mocked(fetchCompletedWeeks).mockResolvedValue([
      { weekNumber: 1, seasonNumber: 2026 },
      { weekNumber: 2, seasonNumber: 2026 },
    ])
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

    expect(await screen.findByText('No picks submitted yet.')).toBeInTheDocument()
  })

  it("renders the user's current-week picks alongside completed history", async () => {
    mockedFetchPickHistory.mockResolvedValueOnce({
      ...history,
      weeks: [
        ...history.weeks,
        {
          weekNumber: 2,
          picks: [
            {
              ...history.weeks[0].picks[0],
              id: 'pick-current',
              gameId: 'game-current',
              awayTeam: 'DAL',
              homeTeam: 'NYG',
              status: 'scheduled',
              winningTeam: null,
              pointsEarned: null,
              outcome: 'unscored',
            },
          ],
        },
      ],
    })
    renderPage()

    expect(await screen.findByText('DAL at NYG')).toBeInTheDocument()
    expect(screen.getByText('Not scored')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Week 2' })).toBeInTheDocument()
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

  it('summarizes season win rate, weekly points, and a confidence histogram', async () => {
    mockedFetchPickHistory.mockResolvedValueOnce({
      season: 2026,
      weeks: [
        {
          weekNumber: 1,
          picks: [
            {
              ...history.weeks[0].picks[0],
              id: 'p1',
              confidence: 4,
              pointsEarned: 4,
              outcome: 'correct',
            },
            {
              ...history.weeks[0].picks[0],
              id: 'p2',
              gameId: 'game-2',
              confidence: 2,
              pointsEarned: 0,
              outcome: 'incorrect',
            },
          ],
        },
        {
          weekNumber: 2,
          picks: [
            {
              ...history.weeks[0].picks[0],
              id: 'p3',
              gameId: 'game-3',
              confidence: 4,
              pointsEarned: 4,
              outcome: 'correct',
            },
          ],
        },
      ],
    })
    renderPage()

    await screen.findByText('Your season so far')
    expect(screen.getByText('67%')).toBeInTheDocument()
    expect(screen.getByText('2 of 3 scored picks')).toBeInTheDocument()
    expect(screen.getByText('4.0')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Week 1: 50% win rate' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Week 2: 100% win rate' })).toBeInTheDocument()
    expect(
      screen.getByRole('img', {
        name: 'Confidence point histogram: confidence 2, 0% (0/1 correct); confidence 4, 100% (2/2 correct)',
      }),
    ).toBeInTheDocument()
  })

  it('hides season stats when there is no scored history', async () => {
    mockedFetchPickHistory.mockResolvedValueOnce({
      season: 2026,
      weeks: [
        {
          weekNumber: 2,
          picks: [
            {
              ...history.weeks[0].picks[0],
              id: 'pick-current',
              awayTeam: 'DAL',
              homeTeam: 'NYG',
              status: 'scheduled',
              winningTeam: null,
              pointsEarned: null,
              outcome: 'unscored',
            },
          ],
        },
      ],
    })
    renderPage()

    await screen.findByText('DAL at NYG')
    expect(screen.queryByText('Your season so far')).not.toBeInTheDocument()
  })

  it('averages only completed weeks and counts settled confidence uses, including losses', async () => {
    vi.mocked(fetchCompletedWeeks).mockResolvedValue([{ weekNumber: 1, seasonNumber: 2026 }])
    const pick = history.weeks[0].picks[0]
    mockedFetchPickHistory.mockResolvedValue({
      season: 2026,
      weeks: [
        { weekNumber: 1, picks: [{ ...pick, pointsEarned: 10 }] },
        {
          weekNumber: 2,
          picks: [
            { ...pick, id: 'loss', pointsEarned: 0, outcome: 'incorrect' },
            { ...pick, id: 'pending', pointsEarned: null, outcome: 'unscored', status: 'live' },
            { ...pick, id: 'voided', pointsEarned: 4, outcome: 'voided' },
          ],
        },
      ],
    })
    renderPage()
    expect(await screen.findByText('10.0')).toBeInTheDocument()
    expect(screen.getByText('Across 1 completed week')).toBeInTheDocument()
    expect(screen.getByText('0/1 correct · 0%')).toBeInTheDocument()
    expect(
      screen.getByRole('img', {
        name: 'Confidence point histogram: confidence 4, 50% (1/2 correct)',
      }),
    ).toBeInTheDocument()
  })

  it('defaults to kickoff time with alphabetical matchups as the tiebreaker', async () => {
    const pick = history.weeks[0].picks[0]
    mockedFetchPickHistory.mockResolvedValue({
      season: 2026,
      weeks: [
        {
          weekNumber: 1,
          picks: [
            { ...pick, id: 'later', awayTeam: 'ARI', kickoff: '2026-09-11T20:00:00Z' },
            { ...pick, id: 'gb', awayTeam: 'GB' },
            { ...pick, id: 'buf' },
          ],
        },
      ],
    })
    renderPage()
    const table = await screen.findByRole('table', { name: 'Your picks' })
    const rows = within(table).getAllByRole('row')
    expect(rows[1]).toHaveTextContent('BUF at KC')
    expect(rows[2]).toHaveTextContent('GB at KC')
    expect(rows[3]).toHaveTextContent('ARI at KC')
    expect(screen.getByRole('columnheader', { name: 'Kickoff' })).toHaveAttribute(
      'aria-sort',
      'ascending',
    )
    await userEvent.setup().click(screen.getByRole('button', { name: 'Sort by Kickoff' }))
    expect(within(table).getAllByRole('row')[1]).toHaveTextContent('ARI at KC')
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
    expect(screen.getAllByRole('columnheader')[3]).toHaveAttribute('aria-sort', 'ascending')
  })
})
