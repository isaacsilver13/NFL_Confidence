import { beforeEach, describe, expect, it, vi } from 'vitest'
import { sendEvent, trackSectionOpen } from './events'

describe('events API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('posts a single event to /events without retrying auth', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 204 }))

    sendEvent('page_view', { path: '/picks' })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/events')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(init?.body as string)).toEqual({
      events: [{ action: 'page_view', metadata: { path: '/picks' } }],
    })
  })

  it('does not trigger a token refresh when the event gets a 401', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify({ error: {} }), { status: 401 }))

    sendEvent('heartbeat', { path: '/' })
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    await Promise.resolve()

    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/auth/refresh'))).toBe(false)
  })

  // An unhandled rejection would fail the vitest run, so reaching the end proves it is swallowed.
  it('swallows network failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))

    expect(() => sendEvent('heartbeat', { path: '/' })).not.toThrow()
    await new Promise((resolve) => setTimeout(resolve, 0))
  })

  it('trackSectionOpen sends a section_open event', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 204 }))

    trackSectionOpen('standings')

    const init = fetchMock.mock.calls[0][1]
    expect(JSON.parse(init?.body as string).events[0]).toEqual({
      action: 'section_open',
      metadata: { section: 'standings' },
    })
  })
})
