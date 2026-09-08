import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchSessionBootstrap } from '@/api/session'
import { LeagueMemberRoute } from './ProtectedRoute'

vi.mock('@/api/session', () => ({
  fetchSessionBootstrap: vi.fn(),
}))

const mockedFetchSessionBootstrap = vi.mocked(fetchSessionBootstrap)

function renderRoute() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/picks']}>
        <Routes>
          <Route element={<LeagueMemberRoute />}>
            <Route path="/picks" element={<p>Picks page</p>} />
          </Route>
          <Route path="/" element={<p>Join dashboard</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LeagueMemberRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redirects authenticated non-members to the dashboard', async () => {
    mockedFetchSessionBootstrap.mockResolvedValue({
      user: {
        id: 'user-1',
        displayName: 'New User',
        email: 'new@example.com',
        avatarUrl: null,
      },
      league: null,
      currentWeek: null,
      membership: { status: 'not_member', role: null },
    })

    renderRoute()

    expect(await screen.findByText('Join dashboard')).toBeInTheDocument()
    expect(screen.queryByText('Picks page')).not.toBeInTheDocument()
  })
})
