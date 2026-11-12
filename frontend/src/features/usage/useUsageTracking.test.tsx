import { useEffect } from 'react'
import { act, render } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthContextValue } from '@/features/auth/AuthContext'
import { sendEvent } from '@/api/events'
import { shouldHeartbeat, useUsageTracking } from './useUsageTracking'

vi.mock('@/api/events', () => ({ sendEvent: vi.fn() }))

const sendEventMock = vi.mocked(sendEvent)

let navigateTo: (path: string) => void = () => undefined

function Probe() {
  useUsageTracking()
  const navigate = useNavigate()
  useEffect(() => {
    navigateTo = (path) => void navigate(path)
  }, [navigate])
  return null
}

function renderTracked(user: AuthContextValue['user'] = { id: 'u1' } as AuthContextValue['user']) {
  const value: AuthContextValue = {
    user,
    isLoading: false,
    isAuthenticated: Boolean(user),
    setUser: vi.fn(),
    signOut: vi.fn(),
  }
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/picks?x=1#frag']}>
        <Probe />
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

function heartbeats() {
  return sendEventMock.mock.calls.filter(([action]) => action === 'heartbeat')
}

function setHidden(hidden: boolean) {
  Object.defineProperty(document, 'hidden', { configurable: true, value: hidden })
}

describe('shouldHeartbeat', () => {
  it('is true up to exactly 2 minutes after the last interaction', () => {
    expect(shouldHeartbeat(120_000, 0, false)).toBe(true)
    expect(shouldHeartbeat(120_001, 0, false)).toBe(false)
  })

  it('is false while the document is hidden', () => {
    expect(shouldHeartbeat(1_000, 0, true)).toBe(false)
  })
})

describe('useUsageTracking', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    sendEventMock.mockClear()
    setHidden(false)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('sends session_start once with a device value', () => {
    renderTracked()

    const starts = sendEventMock.mock.calls.filter(([action]) => action === 'session_start')
    expect(starts).toHaveLength(1)
    expect(['phone', 'desktop']).toContain((starts[0][1] as { device: string }).device)
  })

  it('sends page_view with pathname only, on mount and on route change', () => {
    renderTracked()
    expect(sendEventMock).toHaveBeenCalledWith('page_view', { path: '/picks' })

    act(() => navigateTo('/leaderboard?code=SECRET#top'))

    expect(sendEventMock).toHaveBeenCalledWith('page_view', { path: '/leaderboard' })
    expect(JSON.stringify(sendEventMock.mock.calls)).not.toContain('SECRET')
  })

  it('sends heartbeat every 30s while the user is interacting', () => {
    renderTracked()
    act(() => vi.advanceTimersByTime(30_000))
    expect(heartbeats()).toHaveLength(1)
    expect(heartbeats()[0][1]).toEqual({ path: '/picks' })

    act(() => {
      document.dispatchEvent(new Event('pointerdown'))
      vi.advanceTimersByTime(30_000)
    })
    expect(heartbeats()).toHaveLength(2)
  })

  it('stops heartbeats 2 minutes after the last interaction, then resumes on interaction', () => {
    renderTracked()
    act(() => vi.advanceTimersByTime(120_000))
    const sentWhileActive = heartbeats().length
    expect(sentWhileActive).toBe(4)

    act(() => vi.advanceTimersByTime(10 * 60_000))
    expect(heartbeats()).toHaveLength(sentWhileActive)

    act(() => {
      document.dispatchEvent(new Event('keydown'))
      vi.advanceTimersByTime(30_000)
    })
    expect(heartbeats()).toHaveLength(sentWhileActive + 1)
  })

  it('sends no heartbeat while the document is hidden', () => {
    renderTracked()
    setHidden(true)
    act(() => vi.advanceTimersByTime(60_000))
    expect(heartbeats()).toHaveLength(0)
  })

  it('sends nothing for a logged-out user', () => {
    renderTracked(null)
    act(() => vi.advanceTimersByTime(60_000))
    expect(sendEventMock).not.toHaveBeenCalled()
  })

  it('sends nothing after unmount', () => {
    const { unmount } = renderTracked()
    unmount()
    sendEventMock.mockClear()

    act(() => {
      document.dispatchEvent(new Event('pointerdown'))
      vi.advanceTimersByTime(5 * 60_000)
    })

    expect(sendEventMock).not.toHaveBeenCalled()
  })
})
