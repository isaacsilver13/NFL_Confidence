import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fetchCompletedWeeks,
  fetchCurrentGames,
  fetchCurrentPicks,
  fetchCurrentWeek,
  fetchPickHistory,
  fetchWeekGames,
  fetchWeeks,
  savePicks,
} from './nfl'

function responseFor<T>(data: T): Response {
  return new Response(JSON.stringify({ data, message: null }), { status: 200 })
}

describe('nfl API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('requests the current week', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await fetchCurrentWeek()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/weeks/current',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests all weeks', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor([]))

    await fetchWeeks()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/weeks',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests current-week games', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor([]))

    await fetchCurrentGames()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/games/current',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests games for a given week', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor([]))

    await fetchWeekGames(4)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/games?week=4',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests current picks', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor([]))

    await fetchCurrentPicks()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/picks/current',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests pick history', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await fetchPickHistory()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/picks/history',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests completed weeks', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor([]))

    await fetchCompletedWeeks()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/leaderboard/weeks',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('saves picks with the given payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor([]))
    const input = {
      week: 4,
      picks: [{ gameId: 'game-1', team: 'KC', confidence: 1 }],
      voidedGameIds: [],
    }

    await savePicks(input)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/picks',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(input) }),
    )
  })
})
