import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { joinLeague } from '@/api/league'

type JoinStatus = 'joining' | 'success' | 'error'

export function JoinLeaguePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<JoinStatus>(token ? 'joining' : 'error')
  const [errorMessage, setErrorMessage] = useState<string | null>(
    token ? null : 'This invite link is missing a token.',
  )

  useEffect(() => {
    if (!token) {
      return
    }

    let cancelled = false
    joinLeague(token)
      .then(() => {
        if (!cancelled) {
          setStatus('success')
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setStatus('error')
        setErrorMessage(
          error instanceof ApiError ? error.message : 'Could not join the league. Please try again.',
        )
      })
    return () => {
      cancelled = true
    }
  }, [token])

  if (status === 'joining') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-slate-600 dark:text-slate-300">Joining league…</p>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
        <h1 className="text-2xl font-bold">You're in!</h1>
        <p className="text-slate-600 dark:text-slate-300">
          You've successfully joined the league.
        </p>
        <button
          type="button"
          onClick={() => void navigate('/', { replace: true })}
          className="min-h-11 rounded-md bg-primary px-4 py-2 font-medium text-white transition-colors duration-150 hover:bg-primary-hover"
        >
          Go to dashboard
        </button>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-bold">Couldn't join league</h1>
      <p className="text-slate-600 dark:text-slate-300">{errorMessage}</p>
    </div>
  )
}
