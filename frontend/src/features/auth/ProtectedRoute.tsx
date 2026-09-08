import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchSessionBootstrap } from '@/api/session'
import { useAuth } from './AuthContext'

/** Route guard: redirects unauthenticated visitors to /login, preserving their target. */
export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}

/** Route guard: sends authenticated non-members to the dashboard join prompt. */
export function LeagueMemberRoute() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['session', 'bootstrap'],
    queryFn: fetchSessionBootstrap,
    retry: false,
    staleTime: 5 * 60_000,
  })

  if (isLoading) {
    return null
  }

  if (error || data?.membership.status !== 'member') {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
