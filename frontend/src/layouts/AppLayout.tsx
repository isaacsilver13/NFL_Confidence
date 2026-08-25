import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthContext'

const NAV_LINKS = [
  { to: '/', label: 'Dashboard' },
  { to: '/picks', label: 'Picks' },
  { to: '/leaderboard', label: 'Leaderboard' },
  { to: '/standings', label: 'Standings' },
  { to: '/profile', label: 'Profile' },
]

function navLinkClassName({ isActive }: { isActive: boolean }): string {
  return [
    'rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150',
    isActive
      ? 'bg-primary text-white'
      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
  ].join(' ')
}

export function AppLayout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await signOut()
    void navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <nav className="mx-auto flex max-w-4xl items-center gap-1 overflow-x-auto px-4 py-3">
          <span className="mr-4 shrink-0 font-bold text-primary">NFL Confidence Pool</span>
          {NAV_LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === '/'} className={navLinkClassName}>
              {link.label}
            </NavLink>
          ))}
          <span className="ml-auto flex shrink-0 items-center gap-3">
            {user && (
              <span className="hidden text-sm text-slate-600 sm:inline dark:text-slate-300">
                {user.displayName}
              </span>
            )}
            <button
              type="button"
              onClick={() => void handleSignOut()}
              className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 transition-colors duration-150 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Sign out
            </button>
          </span>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

