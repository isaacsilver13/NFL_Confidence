import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AuthContext, useAuth } from './AuthContext'

function AuthProbe() {
  const auth = useAuth()
  return <output>{auth.isAuthenticated ? 'authenticated' : 'unauthenticated'}</output>
}

function ThrowingProbe() {
  useAuth()
  return null
}

describe('AuthContext', () => {
  it('exposes a context object and a useAuth hook', () => {
    expect(AuthContext).toBeDefined()
    expect(useAuth).toBeInstanceOf(Function)
  })

  it('throws when useAuth is called outside an AuthProvider', () => {
    // Swallow the expected React error boundary console output for this render.
    expect(() => render(<ThrowingProbe />)).toThrow('useAuth must be used within an AuthProvider')
  })

  it('returns the provided value when rendered within an AuthContext.Provider', () => {
    render(
      <AuthContext.Provider
        value={{
          user: null,
          isLoading: false,
          isAuthenticated: true,
          setUser: () => {},
          signOut: async () => {},
        }}
      >
        <AuthProbe />
      </AuthContext.Provider>,
    )

    expect(screen.getByText('authenticated')).toBeInTheDocument()
  })
})
