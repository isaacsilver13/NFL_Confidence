import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchCurrentPicksCard, fetchSessionBootstrap } from './session'

function responseFor<T>(data: T): Response {
  return new Response(JSON.stringify({ data, message: null }), { status: 200 })
}

describe('session API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('requests the session bootstrap payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await fetchSessionBootstrap()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/bootstrap',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('requests the current picks card payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor({}))

    await fetchCurrentPicksCard()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/picks/card/current',
      expect.objectContaining({ credentials: 'include' }),
    )
  })
})
