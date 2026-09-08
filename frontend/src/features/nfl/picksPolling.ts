import type { CurrentPicksCard } from '@/api/session'

export const LIVE_GAME_POLL_INTERVAL_MS = 30_000

export function getPicksCardRefetchInterval(data: CurrentPicksCard | undefined): number | false {
  return data?.games.some((game) => game.status === 'live') ? LIVE_GAME_POLL_INTERVAL_MS : false
}
