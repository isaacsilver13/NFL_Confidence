import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { devLogin, fetchCurrentUser, googleLoginUrl, logout } from './auth'
import { getAccessToken, setAccessToken } from './client'

function responseFor<T>(data: T): Response {
  return new Response(JSON.stringify({ data, message: null }), { status: 200 })
}

describe('auth API', () => {
  beforeEach(() => {
    setAccessToken(null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    setAccessToken(null)
  })

  it('builds the Google login URL without making a request', () => {
    expect(googleLoginUrl()).toBe('/api/v1/auth/google/login')
  })

  it('logs in via the dev-login endpoint and stores the access token', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      responseFor({
        accessToken: 'dev-access-token',
        tokenType: 'bearer',
        expiresIn: 900,
        user: { id: 'user-1', displayName: 'Dev User', email: 'dev@example.com', avatarUrl: null },
      }),
    )

    await devLogin()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/dev-login',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(getAccessToken()).toBe('dev-access-token')
  })

  it('requests the current user', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      responseFor({
        id: 'user-1',
        displayName: 'Dev User',
        email: 'dev@example.com',
        avatarUrl: null,
      }),
    )

    await fetchCurrentUser()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/me',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('logs out and clears the stored access token', async () => {
    setAccessToken('existing-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(responseFor(null))

    await logout()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/logout',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
    expect(getAccessToken()).toBeNull()
  })
})
