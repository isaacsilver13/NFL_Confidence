import { useState } from 'react'
import { ArrowRight, LogIn } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { devLogin, googleLoginUrl } from '@/api/auth'
import { NflMark } from '@/components/nfl/NflMark'
import { Button } from '@/components/ui/Button'
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
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-8 dark:bg-slate-950">
      <div className="w-full max-w-md animate-slide-up rounded-3xl border border-slate-200 bg-surface p-8 shadow-xl shadow-primary/10 dark:border-slate-800 dark:bg-slate-900 sm:p-10">
        <NflMark />
        <div className="mt-10">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-accent">
            Game day starts here
          </p>
          <h1 className="mb-3 text-3xl font-black tracking-tight text-primary dark:text-white">
            Make every pick count.
          </h1>
        </div>
        <p className="mb-8 max-w-sm text-slate-600 dark:text-slate-300">
          Sign in to view your league and submit picks.
        </p>
        <Button fullWidth onClick={handleGoogleLogin}>
          <LogIn size={18} aria-hidden="true" />
          Continue with Google
          <ArrowRight size={16} aria-hidden="true" />
        </Button>
        {import.meta.env.DEV && (
          <Button
            variant="secondary"
            onClick={() => void handleDevLogin()}
            disabled={isDevLoggingIn}
            fullWidth
            className="mt-3"
          >
            {isDevLoggingIn ? 'Signing in…' : 'Continue as Dev User'}
          </Button>
        )}
        {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>
    </div>
  )
}
