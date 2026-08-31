import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '@/features/auth/AuthProvider'
import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  beforeEach(() => {
    // AuthProvider calls GET /auth/me on mount to silently restore a session; stub
    // fetch so that resolves deterministically instead of hitting the real network.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network disabled in tests')))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the Google sign-in button', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>,
      )
    })

    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument()
  })
})
