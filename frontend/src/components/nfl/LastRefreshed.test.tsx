import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchLastRefreshed } from '@/api/nfl'
import { formatLastRefreshed } from '@/features/nfl/formatLastRefreshed'
import { LastRefreshed } from './LastRefreshed'

vi.mock('@/api/nfl', () => ({ fetchLastRefreshed: vi.fn() }))

const mockedFetchLastRefreshed = vi.mocked(fetchLastRefreshed)

function renderComponent() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <LastRefreshed />
    </QueryClientProvider>,
  )
}

describe('LastRefreshed', () => {
  beforeEach(() => vi.clearAllMocks())

  it('formats the timestamp in Chicago time', () => {
    expect(formatLastRefreshed('2026-09-27T21:12:00Z')).toBe('Sun, Sep 27, 4:12 PM CDT')
    expect(formatLastRefreshed('2026-12-06T21:12:00Z')).toBe('Sun, Dec 6, 3:12 PM CST')
  })

  it('shows when scores were last refreshed', async () => {
    mockedFetchLastRefreshed.mockResolvedValue({ lastRefreshedAt: '2026-09-27T21:12:00Z' })
    renderComponent()

    expect(await screen.findByText('Last refreshed Sun, Sep 27, 4:12 PM CDT')).toBeInTheDocument()
  })

  it('renders nothing before any sync has run', async () => {
    mockedFetchLastRefreshed.mockResolvedValue({ lastRefreshedAt: null })
    const { container } = renderComponent()

    await vi.waitFor(() => expect(mockedFetchLastRefreshed).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
