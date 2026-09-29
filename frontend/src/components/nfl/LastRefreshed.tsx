import { useQuery } from '@tanstack/react-query'
import { fetchLastRefreshed } from '@/api/nfl'
import { formatLastRefreshed } from '@/features/nfl/formatLastRefreshed'

export function LastRefreshed({ className = '' }: { className?: string }) {
  const { data } = useQuery({
    queryKey: ['weeks', 'last-refreshed'],
    queryFn: fetchLastRefreshed,
    refetchInterval: 60_000,
  })

  if (!data?.lastRefreshedAt) return null
  return (
    <p
      className={`text-xs font-semibold text-ink-muted dark:text-slate-400 dev-dark:text-text-muted ${className}`}
    >
      Last refreshed {formatLastRefreshed(data.lastRefreshedAt)}
    </p>
  )
}
