import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider } from './AuthProvider'
import { useAuth } from './AuthContext'
import { setAccessToken } from '@/api/client'
import type { User } from '@/types/auth'

function successResponse<T>(data: T): Response {
  return new Response(JSON.stringify({ data, message: null }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function unauthorizedResponse(): Response {
  return new Response(
    JSON.stringify({
      error: { code: 'UNAUTHORIZED', message: 'Missing refresh token', details: [] },
    }),
    { status: 401, headers: { 'Content-Type': 'application/json' } },
  )
}

function AuthProbe() {
  const { isLoading, user } = useAuth()
  return <output>{isLoading ? 'loading' : (user?.email ?? 'signed-out')}</output>
}

const user: User = {
  id: 'user-1',
  displayName: 'Test User',
  email: 'test@example.com',
  avatarUrl: null,
}

describe('AuthProvider', () => {
  beforeEach(() => {
    setAccessToken(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    setAccessToken(null)
  })

  it('refreshes before fetching the current user', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(successResponse({ accessToken: 'access-token' }))
      .mockResolvedValueOnce(successResponse(user))
    vi.stubGlobal('fetch', fetchMock)

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => expect(screen.getByText(user.email)).toBeInTheDocument())

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/refresh')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/auth/me')
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      headers: { Authorization: 'Bearer access-token' },
    })
  })

  it('stays signed out after a refresh failure without requesting the user', async () => {
    const fetchMock = vi.fn().mockResolvedValue(unauthorizedResponse())
    vi.stubGlobal('fetch', fetchMock)

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => expect(screen.getByText('signed-out')).toBeInTheDocument())

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/refresh')
  })
})
