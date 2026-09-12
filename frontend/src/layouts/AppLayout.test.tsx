import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchSessionBootstrap } from '@/api/session'
import { AuthContext } from '@/features/auth/AuthContext'
import type { User } from '@/types/auth'
import type { SessionBootstrap } from '@/api/session'
import { AppLayout } from './AppLayout'

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

function renderLayout(membership: SessionBootstrap['membership']) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  mockedFetchSessionBootstrap.mockResolvedValue({
    user,
    league: null,
    currentWeek: null,
    membership,
  })
  return render(
    <AuthContext.Provider
      value={{
        user,
        isLoading: false,
        isAuthenticated: true,
        setUser: vi.fn(),
        signOut: vi.fn().mockResolvedValue(undefined),
      }}
    >
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<p>Dashboard content</p>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </AuthContext.Provider>,
  )
}

describe('AppLayout commissioner navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the Members tab to owners', async () => {
    renderLayout({ status: 'member', role: 'owner' })

    expect(await screen.findByRole('link', { name: 'Members' })).toHaveAttribute(
      'href',
      '/league-settings',
    )
  })

  it('hides the Members tab from regular members', async () => {
    renderLayout({ status: 'member', role: 'member' })

    await screen.findByText('Dashboard content')
    expect(screen.queryByRole('link', { name: 'Members' })).not.toBeInTheDocument()
  })
})
