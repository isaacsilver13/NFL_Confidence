import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchPickBreakdown, fetchSeasonStandings, fetchWeeklyLeaderboard } from './leaderboard'

function responseFor<T>(data: T): Response {
  return new Response(JSON.stringify({ data, message: null }), { status: 200 })
}

describe('leaderboard API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('requests a selected weekly leaderboard', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(responseFor({ standings: [] }))

    await fetchWeeklyLeaderboard(8)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/leaderboard/week?week=8',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests season standings without adding an undefined query value', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(responseFor({ standings: [] }))

    await fetchSeasonStandings()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/leaderboard/season',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests the weekly pick breakdown', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({ weeks: [] }))

    await fetchPickBreakdown()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/leaderboard/pick-breakdown',
      expect.objectContaining({ credentials: 'include' }),
    )
  })
})
