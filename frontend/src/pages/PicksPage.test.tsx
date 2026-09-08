import { describe, expect, it, beforeEach, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiError } from '@/api/client'
import { savePicks } from '@/api/nfl'
import { fetchCurrentPicksCard } from '@/api/session'
import {
  getPicksCardRefetchInterval,
  LIVE_GAME_POLL_INTERVAL_MS,
} from '@/features/nfl/picksPolling'
import type { NflGame, NflPick, NflWeek } from '@/types/nfl'
import { PicksPage } from './PicksPage'

vi.mock('@/api/nfl', () => ({
  savePicks: vi.fn(),
}))

vi.mock('@/api/session', () => ({
  fetchCurrentPicksCard: vi.fn(),
}))

const mockedFetchCurrentPicksCard = vi.mocked(fetchCurrentPicksCard)
const mockedSavePicks = vi.mocked(savePicks)

const week: NflWeek = {
  id: 'week-1',
  season: 2026,
  weekNumber: 1,
  startDate: '2026-08-23T00:00:00Z',
  endDate: '2026-08-31T00:00:00Z',
  status: 'regular',
}

const games: NflGame[] = [
  {
    id: 'game-1',
    awayTeam: 'BUF',
    homeTeam: 'KC',
    kickoff: '2026-08-25T20:00:00Z',
    status: 'scheduled',
    venueName: 'Highmark Stadium',
    venueLocation: 'Orchard Park, NY',
    spreadTeam: 'KC',
    spread: -3.5,
    awayScore: null,
    homeScore: null,
    winningTeam: null,
    isTie: false,
  },
  {
    id: 'game-2',
    awayTeam: 'GB',
    homeTeam: 'CHI',
    kickoff: '2026-08-26T20:00:00Z',
    status: 'scheduled',
    venueName: null,
    venueLocation: null,
    spreadTeam: null,
    spread: null,
    awayScore: null,
    homeScore: null,
    winningTeam: null,
    isTie: false,
  },
]

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <PicksPage />
    </QueryClientProvider>,
  )
}

describe('PicksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const picksCard = {
      week,
      games,
      picks: [],
    }
    mockedFetchCurrentPicksCard.mockResolvedValue(picksCard)
    mockedSavePicks.mockResolvedValue([] as NflPick[])
  })

  it('renders current games and submits one unique confidence value per game', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('button', { name: 'BUF' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'GB' })).toBeInTheDocument()
    expect(screen.getByText('Highmark Stadium')).toBeInTheDocument()
    expect(screen.getByText(/Line: KC -3.5/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'KC' }))
    await user.click(screen.getByRole('button', { name: 'GB' }))
    await user.click(screen.getAllByRole('button', { name: '2' })[0])
    await user.click(screen.getAllByRole('button', { name: '1' })[1])

    await waitFor(() => expect(mockedSavePicks).toHaveBeenCalledTimes(1))
    expect(mockedSavePicks.mock.calls[0][0]).toEqual({
      week: 1,
      voidedGameIds: [],
      picks: [
        { gameId: 'game-1', team: 'KC', confidence: 2 },
        { gameId: 'game-2', team: 'GB', confidence: 1 },
      ],
    })
    expect(screen.queryByRole('button', { name: 'Save picks' })).not.toBeInTheDocument()
    expect(await screen.findByText('Picks saved.')).toBeInTheDocument()
  })

  it('voids incomplete and conflicting drafts while keeping the save flow live', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByRole('heading', { name: /Week 1 picks/i })
    await user.click(screen.getByRole('button', { name: 'BUF' }))
    await user.click(screen.getAllByRole('button', { name: '1' })[0])

    await waitFor(() => expect(mockedSavePicks).toHaveBeenCalledTimes(1))
    expect(mockedSavePicks.mock.calls[0][0]).toEqual({
      week: 1,
      picks: [{ gameId: 'game-1', team: 'BUF', confidence: 1 }],
      voidedGameIds: ['game-2'],
    })
    expect(
      await screen.findByText(/incomplete or conflicting picks were voided/i),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'GB' }))
    await user.click(screen.getAllByRole('button', { name: '1' })[1])

    await waitFor(() => expect(mockedSavePicks).toHaveBeenCalledTimes(2))
    expect(mockedSavePicks.mock.calls[1][0]).toEqual({
      week: 1,
      picks: [{ gameId: 'game-1', team: 'BUF', confidence: 1 }],
      voidedGameIds: ['game-2'],
    })
  })

  it('renders confidence values in a 4x4 grid and toggles picks off', async () => {
    const user = userEvent.setup()
    mockedFetchCurrentPicksCard.mockResolvedValueOnce({
      week,
      games,
      picks: [
        {
          id: 'pick-1',
          gameId: 'game-1',
          team: 'BUF',
          confidence: 2,
          submittedAt: '2026-08-24T12:00:00Z',
        },
        {
          id: 'pick-2',
          gameId: 'game-2',
          team: 'GB',
          confidence: 1,
          submittedAt: '2026-08-24T12:00:00Z',
        },
      ],
    })
    renderPage()

    const confidenceGroup = await screen.findByRole('group', {
      name: 'Confidence for BUF at KC',
    })
    expect(confidenceGroup).toHaveClass('grid', 'grid-cols-4')

    const winner = screen.getByRole('button', { name: 'BUF' })
    const confidence = screen.getAllByRole('button', { name: '2' })[0]
    expect(winner).toHaveAttribute('aria-pressed', 'true')
    expect(confidence).toHaveAttribute('aria-pressed', 'true')

    await user.click(winner)
    await user.click(confidence)

    expect(winner).toHaveAttribute('aria-pressed', 'false')
    expect(confidence).toHaveAttribute('aria-pressed', 'false')
    await waitFor(() => expect(mockedSavePicks).toHaveBeenCalledTimes(1))
    expect(mockedSavePicks.mock.calls[0][0]).toEqual({
      week: 1,
      picks: [{ gameId: 'game-2', team: 'GB', confidence: 1 }],
      voidedGameIds: ['game-1'],
    })
  })

  it('shows rejected saves inline', async () => {
    const user = userEvent.setup()
    mockedSavePicks.mockRejectedValueOnce(
      new ApiError(422, 'VALIDATION_ERROR', 'Picks are no longer editable.'),
    )
    renderPage()

    await screen.findByRole('heading', { name: /Week 1 picks/i })
    await user.click(screen.getByRole('button', { name: 'KC' }))
    await user.click(screen.getByRole('button', { name: 'GB' }))
    await user.click(screen.getAllByRole('button', { name: '2' })[0])
    await user.click(screen.getAllByRole('button', { name: '1' })[1])

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Picks are no longer editable.'),
    )
    expect(screen.queryByText('Picks saved.')).not.toBeInTheDocument()
  })

  it('hydrates an existing pick', async () => {
    const picksCard = {
      week,
      games,
      picks: [
        {
          id: 'pick-1',
          gameId: 'game-1',
          team: 'BUF',
          confidence: 2,
          submittedAt: '2026-08-24T12:00:00Z',
        },
      ],
    }
    mockedFetchCurrentPicksCard.mockResolvedValueOnce(picksCard)
    renderPage()

    expect(await screen.findByRole('button', { name: 'BUF' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getAllByRole('button', { name: '2' })[0]).toHaveAttribute('aria-pressed', 'true')
  })

  it('displays team logos for both teams in each game', async () => {
    renderPage()

    // Wait for the page to load
    await screen.findByRole('heading', { name: /Week 1 picks/i })

    // Verify that logo images are rendered for all teams
    // We look for img elements by their src attribute (images with logos)
    const allImages = document.querySelectorAll('img')

    // Filter for team logo images (they have .png filenames in /logos/)
    const teamLogoImages = Array.from(allImages).filter(
      (img) => img.src && img.src.includes('/logos/') && img.src.includes('.png'),
    )

    // We expect at least 4 logo images: 2 teams per game, and we have 2 games = 4 minimum
    // (displayed in the matchup header for each game)
    expect(teamLogoImages.length).toBeGreaterThanOrEqual(4)

    // Verify specific team logos are present
    const bufImages = teamLogoImages.filter((img) => img.src.includes('/BUF.png'))
    const kcImages = teamLogoImages.filter((img) => img.src.includes('/KC.png'))

    expect(bufImages.length).toBeGreaterThan(0)
    expect(kcImages.length).toBeGreaterThan(0)
  })

  it('polls the picks card only when a game is live', () => {
    expect(getPicksCardRefetchInterval({ week, games, picks: [] })).toBe(false)
    expect(
      getPicksCardRefetchInterval({
        week,
        games: [{ ...games[0], status: 'live' }, games[1]],
        picks: [],
      }),
    ).toBe(LIVE_GAME_POLL_INTERVAL_MS)
    expect(
      getPicksCardRefetchInterval({
        week,
        games: [{ ...games[0], status: 'final' }, games[1]],
        picks: [],
      }),
    ).toBe(false)
  })
})
