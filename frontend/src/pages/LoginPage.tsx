import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { devLogin, googleLoginUrl } from '@/api/auth'
import { useAuth } from '@/features/auth/AuthContext'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setUser } = useAuth()
  const [isDevLoggingIn, setIsDevLoggingIn] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const from = (location.state as { from?: Location })?.from
  const redirectTo = from ? `${from.pathname}${from.search}` : '/'

  function handleGoogleLogin() {
    window.location.href = googleLoginUrl()
  }

  async function handleDevLogin() {
    setError(null)
    setIsDevLoggingIn(true)
    try {
      const { user } = await devLogin()
      setUser(user)
      void navigate(redirectTo, { replace: true })
    } catch {
      setError('Dev login failed. Is the backend running?')
    } finally {
      setIsDevLoggingIn(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 dark:bg-slate-950">
      <div className="w-full max-w-sm animate-slide-up rounded-lg bg-white p-8 text-center shadow-sm dark:bg-slate-900">
        <h1 className="mb-2 text-2xl font-bold text-primary">NFL Confidence Pool</h1>
        <p className="mb-6 text-slate-600 dark:text-slate-300">
          Sign in to view your league and submit picks.
        </p>
        <button
          type="button"
          onClick={handleGoogleLogin}
          className="min-h-11 w-full rounded-md bg-primary px-4 py-2 font-medium text-white transition-colors duration-150 hover:bg-primary-hover"
        >
          Continue with Google
        </button>
        {import.meta.env.DEV && (
          <button
            type="button"
            onClick={() => void handleDevLogin()}
            disabled={isDevLoggingIn}
            className="mt-3 min-h-11 w-full rounded-md border border-slate-300 px-4 py-2 font-medium text-slate-700 transition-colors duration-150 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {isDevLoggingIn ? 'Signing in…' : 'Continue as Dev User'}
          </button>
        )}
        {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>
    </div>
  )
}

