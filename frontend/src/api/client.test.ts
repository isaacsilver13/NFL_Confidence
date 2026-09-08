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

function noContentResponse(): Response {
  return new Response(null, { status: 204 })
}

describe('api client authentication', () => {
  beforeEach(() => {
    setAccessToken(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
    setAccessToken(null)
  })

  it('shares one refresh request across concurrent callers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successResponse({ accessToken: 'access-token' }))
    vi.stubGlobal('fetch', fetchMock)

    const results = await Promise.all([refreshAccessToken(), refreshAccessToken()])

    expect(results).toEqual([true, true])
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/refresh')
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

  it('fails a refresh request that exceeds the startup timeout', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn((_url: string, options: RequestInit) => {
      return new Promise<Response>((_, reject) => {
        options.signal?.addEventListener('abort', () => {
          reject(new DOMException('The operation was aborted.', 'AbortError'))
        })
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const refresh = refreshAccessToken()
    await vi.advanceTimersByTimeAsync(8_000)

    await expect(refresh).resolves.toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('resolves successfully for a 204 no-content response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(noContentResponse())
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiFetch<void>('/league/members/member-1', { method: 'DELETE' })).resolves.toBeUndefined()
  })
})
