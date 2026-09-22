import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthContextValue } from '@/features/auth/AuthContext'
import { fetchSessionBootstrap } from '@/api/session'
import { ThemeProvider } from '@/features/theme/ThemeProvider'
import type { User } from '@/types/auth'
import App from './App'

// App lazy-loads these pages; mock them so the routing table can be verified without
// pulling in each page's own data-fetching dependencies.
vi.mock('./pages/DashboardPage', () => ({
  DashboardPage: () => <div>Dashboard mock</div>,
}))

vi.mock('./pages/JoinLeaguePage', () => ({
  JoinLeaguePage: () => <div>Join league mock</div>,
}))

vi.mock('./pages/LeagueSettingsPage', () => ({
  LeagueSettingsPage: () => <div>League settings mock</div>,
}))

vi.mock('./pages/PicksPage', () => ({
  PicksPage: () => <div>Picks mock</div>,
}))

// AppLayout (rendered for every protected, non-/join route) fetches the session
// bootstrap to decide which nav links to show.
vi.mock('@/api/session', () => ({
  fetchSessionBootstrap: vi.fn(),
}))

const mockedFetchSessionBootstrap = vi.mocked(fetchSessionBootstrap)

const user: User = {
  id: 'user-1',
  displayName: 'Test User',
  email: 'test@example.com',
  avatarUrl: null,
}

const authenticatedContext: AuthContextValue = {
  user,
  isLoading: false,
  isAuthenticated: true,
  setUser: vi.fn(),
  signOut: vi.fn().mockResolvedValue(undefined),
}

const unauthenticatedContext: AuthContextValue = {
  user: null,
  isLoading: false,
  isAuthenticated: false,
  setUser: vi.fn(),
  signOut: vi.fn().mockResolvedValue(undefined),
}

/** Renders the location's pathname + hash so redirects can be asserted on. */
function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{`${location.pathname}${location.hash}`}</div>
}

function renderApp(initialEntry: string, authContext: AuthContextValue) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <AuthContext.Provider value={authContext}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <MemoryRouter initialEntries={[initialEntry]}>
            <LocationProbe />
            <App />
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  )
}

describe('App routing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedFetchSessionBootstrap.mockResolvedValue({
      user,
      league: null,
      currentWeek: null,
      membership: { status: 'member', role: 'member' },
    })
  })

  it('renders LoginPage at /login without requiring authentication', async () => {
    renderApp('/login', unauthenticatedContext)

    expect(await screen.findByRole('button', { name: /continue with google/i })).toBeInTheDocument()
  })

  it('redirects an unauthenticated visitor away from a protected route to /login', async () => {
    renderApp('/', unauthenticatedContext)

    expect(await screen.findByTestId('location')).toHaveTextContent('/login')
  })

  it('renders the Picks page directly at /picks', async () => {
    renderApp('/picks', authenticatedContext)

    expect(await screen.findByText('Picks mock')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/picks')
  })

  it('redirects /leaderboard to the Leaderboard pane on the dashboard', async () => {
    renderApp('/leaderboard', authenticatedContext)

    expect(await screen.findByText('Dashboard mock')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/#leaderboard')
  })

  it('redirects /standings to the Standings pane on the dashboard', async () => {
    renderApp('/standings', authenticatedContext)

    expect(await screen.findByText('Dashboard mock')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/#standings')
  })

  it('redirects /profile to the Profile pane on the dashboard', async () => {
    renderApp('/profile', authenticatedContext)

    expect(await screen.findByText('Dashboard mock')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/#profile')
  })

  it('renders the join-league page for an authenticated user at /join', async () => {
    renderApp('/join', authenticatedContext)

    expect(await screen.findByText('Join league mock')).toBeInTheDocument()
  })

  it('renders league settings for an authenticated user at /league-settings', async () => {
    renderApp('/league-settings', authenticatedContext)

    expect(await screen.findByText('League settings mock')).toBeInTheDocument()
  })
})
