import { useEffect, useState } from 'react'
import { ArrowRight, CheckCircle2 } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { joinLeague } from '@/api/league'
import { NflMark } from '@/components/nfl/NflMark'
import { Button } from '@/components/ui/Button'

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
          error instanceof ApiError
            ? error.message
            : 'Could not join the league. Please try again.',
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
        <NflMark />
        <CheckCircle2 className="mt-8 text-accent" size={48} aria-hidden="true" />
        <h1 className="text-3xl font-black text-primary dark:text-white">You're in!</h1>
        <p className="text-slate-600 dark:text-slate-300">You've successfully joined the league.</p>
        <Button onClick={() => void navigate('/', { replace: true })}>
          Go to dashboard <ArrowRight size={16} aria-hidden="true" />
        </Button>
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
