import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LogOut, Moon, Sun } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchSessionBootstrap } from '@/api/session'
import { Button } from '@/components/ui/Button'
import { NflMark } from '@/components/nfl/NflMark'
import { useAuth } from '@/features/auth/AuthContext'
import { useTheme } from '@/features/theme/ThemeContext'

const NAV_LINKS = [
  { to: '/', label: 'Dashboard' },
  { to: '/picks', label: 'Picks' },
]

function navLinkClassName({ isActive }: { isActive: boolean }): string {
  return [
    'rounded-xl px-3 py-2 text-sm font-bold transition-colors duration-150',
    isActive
      ? 'bg-primary text-white shadow-sm dark:bg-sky dev-dark:bg-accent dark:text-primary dev-dark:text-white'
      : 'text-ink-muted hover:bg-surface-muted hover:text-primary dark:text-slate-300 dev-dark:text-text-secondary dark:hover:bg-slate-800 dev-dark:hover:bg-surface-hover dark:hover:text-white dev-dark:hover:text-ink',
  ].join(' ')
}

export function AppLayout() {
  const { user, signOut } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const { data: bootstrapData } = useQuery({
    queryKey: ['session', 'bootstrap'],
    queryFn: fetchSessionBootstrap,
    enabled: Boolean(user),
    retry: false,
    staleTime: 5 * 60_000,
  })
  const isCommissioner =
    bootstrapData?.membership.status === 'member' && bootstrapData.membership.role === 'owner'
  const navLinks = isCommissioner
    ? [...NAV_LINKS, { to: '/league-settings', label: 'Members' }]
    : NAV_LINKS

  async function handleSignOut() {
    await signOut()
    void navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dev-dark:border-border dark:bg-slate-950/95 dev-dark:bg-background/95">
        <nav className="mx-auto flex max-w-5xl items-center gap-1 overflow-x-auto px-4 py-3">
          <NavLink to="/" end className="mr-4 shrink-0" aria-label="NFL Confidence home">
            <NflMark />
          </NavLink>
          {navLinks.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === '/'} className={navLinkClassName}>
              {link.label}
            </NavLink>
          ))}
          <span className="ml-auto flex shrink-0 items-center gap-3">
            {user && (
              <span className="hidden max-w-32 truncate text-sm font-semibold text-ink-muted sm:inline dark:text-slate-300 dev-dark:text-text-secondary">
                {user.displayName}
              </span>
            )}
            <Button
              variant="quiet"
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <Sun size={16} aria-hidden="true" />
              ) : (
                <Moon size={16} aria-hidden="true" />
              )}
            </Button>
            <Button variant="quiet" onClick={() => void handleSignOut()}>
              <LogOut size={16} aria-hidden="true" />
              Sign out
            </Button>
          </span>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
