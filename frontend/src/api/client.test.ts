import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, refreshAccessToken, setAccessToken } from './client'

function successResponse<T>(data: T): Response {
  return new Response(JSON.stringify({ data, message: null }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function unauthorizedResponse(): Response {
  return new Response(
    JSON.stringify({ error: { code: 'UNAUTHORIZED', message: 'Expired token', details: [] } }),
    { status: 401, headers: { 'Content-Type': 'application/json' } },
  )
}

describe('api client authentication', () => {
  beforeEach(() => {
    setAccessToken(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    setAccessToken(null)
  })

  it('shares one refresh request across concurrent callers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successResponse({ accessToken: 'access-token' }))
    vi.stubGlobal('fetch', fetchMock)

    const results = await Promise.all([refreshAccessToken(), refreshAccessToken()])

    expect(results).toEqual([true, true])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('refreshes and retries an authenticated request after a 401', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorizedResponse())
      .mockResolvedValueOnce(successResponse({ accessToken: 'access-token' }))
      .mockResolvedValueOnce(successResponse({ id: 'user-1' }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiFetch<{ id: string }>('/auth/me')

    expect(result).toEqual({ id: 'user-1' })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[2][1]).toMatchObject({
      headers: { Authorization: 'Bearer access-token' },
    })
  })
})
