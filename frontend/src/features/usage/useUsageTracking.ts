import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { sendEvent } from '@/api/events'
import { useAuth } from '@/features/auth/AuthContext'

const HEARTBEAT_INTERVAL_MS = 30_000
const IDLE_CUTOFF_MS = 120_000
const INTERACTION_EVENTS = ['pointerdown', 'keydown', 'touchstart'] as const

/**
 * Heartbeats only count (and only fire) while the tab is visible and the user interacted
 * recently. A visible-but-abandoned tab therefore goes quiet after 2 minutes instead of
 * keeping the Fly machine and database awake.
 */
export function shouldHeartbeat(now: number, lastInteractionAt: number, hidden: boolean): boolean {
  return !hidden && now - lastInteractionAt <= IDLE_CUTOFF_MS
}

function deviceKind(): 'phone' | 'desktop' {
  return window.matchMedia?.('(max-width: 639px)').matches ? 'phone' : 'desktop'
}

export function useUsageTracking(): void {
  const { user } = useAuth()
  const userId = user?.id
  const { pathname } = useLocation()
  const pathRef = useRef(pathname)
  const lastInteractionRef = useRef(0)

  useEffect(() => {
    pathRef.current = pathname
    if (userId) sendEvent('page_view', { path: pathname })
  }, [pathname, userId])

  useEffect(() => {
    if (!userId) return

    lastInteractionRef.current = Date.now()
    sendEvent('session_start', { device: deviceKind() })

    const markInteraction = () => {
      lastInteractionRef.current = Date.now()
    }
    for (const name of INTERACTION_EVENTS) {
      document.addEventListener(name, markInteraction, { passive: true })
    }
    window.addEventListener('scroll', markInteraction, { passive: true, capture: true })

    const timer = window.setInterval(() => {
      if (shouldHeartbeat(Date.now(), lastInteractionRef.current, document.hidden)) {
        sendEvent('heartbeat', { path: pathRef.current })
      }
    }, HEARTBEAT_INTERVAL_MS)

    return () => {
      window.clearInterval(timer)
      for (const name of INTERACTION_EVENTS) {
        document.removeEventListener(name, markInteraction)
      }
      window.removeEventListener('scroll', markInteraction, { capture: true })
    }
  }, [userId])
}
