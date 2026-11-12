/**
 * Fire-and-forget usage tracking. Events are best-effort: failures are swallowed and must
 * never affect the page. `skipAuthRetry` keeps a tracking call from triggering a token
 * refresh when the access token has expired.
 */

import { apiFetch } from './client'

export type EventAction = 'session_start' | 'page_view' | 'section_open' | 'heartbeat'

export function sendEvent(action: EventAction, metadata: Record<string, string>): void {
  apiFetch<void>('/events', {
    method: 'POST',
    body: JSON.stringify({ events: [{ action, metadata }] }),
    skipAuthRetry: true,
  }).catch(() => undefined)
}

export function trackSectionOpen(section: string): void {
  sendEvent('section_open', { section })
}
