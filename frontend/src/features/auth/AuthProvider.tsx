import { useEffect, useState, type ReactNode } from 'react'
import { fetchCurrentUser, logout as apiLogout } from '@/api/auth'
import { setAccessToken } from '@/api/client'
import type { User } from '@/types/auth'
import { AuthContext } from './AuthContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function bootstrapSession() {
      try {
        // No access token exists yet on a fresh page load; apiFetch's built-in 401
        // handling transparently calls /auth/refresh using the httpOnly cookie.
        const currentUser = await fetchCurrentUser()
        if (!cancelled) setUser(currentUser)
      } catch {
        if (!cancelled) setUser(null)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void bootstrapSession()
    return () => {
      cancelled = true
    }
  }, [])

  async function signOut() {
    try {
      await apiLogout()
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: user !== null, setUser, signOut }}
    >
      {children}
    </AuthContext.Provider>
  )
}
